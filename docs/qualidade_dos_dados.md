# Qualidade dos dados: quarentena, deduplicação, cruzamento e idempotência

Regras que o pipeline aplica e onde cada uma está no código. As contagens da última execução estão em
[`dicionario_de_dados.md`](dicionario_de_dados.md), seções "Cruzamento" e "Descartes e quarentena".

Divisão de responsabilidades:
- A **bronze** só rejeita **erro estrutural**, isto é, o que impede ler o registro.
- A **silver** aplica as **regras de negócio**.
- A **gold** não limpa nada: se precisasse limpar, a silver teria falhado.
- Nenhum registro some sem rastro: tudo o que não segue para a camada seguinte vai para uma quarentena
  com o motivo, ou é contado no relatório.

## 1. Bronze — quarentena estrutural (`notebooks/ingestao.ipynb`)

Os registros rejeitados vão para `data/quarentena/<tabela>/<id_carga>.parquet`, com `_registro_bruto`
e `_motivo`. O job não quebra por causa de dado sujo, e `testar_quarentena()` prova isso com bytes
sintéticos.

| Motivo | Fonte | Quando |
| --- | --- | --- |
| `encoding <enc>: …` | NOAA (e qualquer texto lido por `ler_delimitado`) | a linha tem byte que não decodifica no encoding declarado; só aquela linha cai |
| `n_campos: esperado N, veio M` | NOAA | a linha tem número errado de campos |
| `campo não numérico` | NOAA | um dos 13 campos (ano + 12 meses) não é número |
| `obrigatória vazia: [...]` | EPE | `Data`, `Classe` ou `Consumo` vazio na planilha |
| `arrays desalinhados ou vazios` | Open-Meteo | a página JSON tem arrays diários de tamanhos diferentes, ou nenhum dia |

A bronze guarda tudo como `string`, com os nomes originais, e acrescenta seis metadados técnicos a cada
registro:
- `_id_carga`: identificador da carga, que também é o instante UTC em que ela começou;
- `_extraido_em`: horário da extração;
- `_origem`: URL de onde o dado veio;
- `_arquivo_raw`: arquivo raw correspondente;
- `_linha`: posição do registro no arquivo;
- `_hash_registro`: sha256 do registro bruto. O mesmo dado gera o mesmo hash em qualquer carga.

## 2. Silver — regras de negócio (`notebooks/silver.ipynb`)

Os registros que violam uma regra vão para `silver_quarentena`, com a tabela, a regra, o valor
original, a carga e o hash. As regras são avaliadas em ordem, e cada registro cai só na primeira que
violar.

**EPE** (`silver_energia_uf`, `silver_energia_subsistema`):

| Regra | Condição |
| --- | --- |
| `data_invalida` | `Data` não é `AAAAMMDD` válido |
| `consumo_nao_numerico` | `Consumo` não converte para número (negativo é aceito: é estorno, marcado com `flag_estorno`) |
| `consumidores_invalido` | `Consumidores` nulo, negativo ou não inteiro |
| `classe_fora_do_dominio` | classe fora de residencial, comercial, industrial, rural, outros |
| `tipo_fora_do_dominio` | tipo fora de cativo, livre |
| `sistema_fora_do_dominio` | `Sistema` fora dos 5 subsistemas conhecidos |
| `regiao_fora_do_dominio` | região fora das 5 |
| `uf_fora_do_dominio` | UF fora das 27 (só na tabela por UF) |

**Open-Meteo** (`silver_clima_uf_mes`), regras aplicadas por dia, antes de agregar no mês:

| Regra | Condição |
| --- | --- |
| `uf_nao_identificada` | não dá para extrair a UF do nome do arquivo raw |
| `data_invalida` | `time` não é data |
| `variavel_nula` | temperatura média, máxima ou chuva nula |
| `coordenada_ausente` | latitude/longitude da célula de grade ausente |
| `temp_media_fora_da_faixa` | temperatura média fora de −30 a 50 °C |
| `temp_max_fora_da_faixa` | máxima fora de −30 a 55 °C |
| `temp_media_maior_que_max` | média > máxima + 0,05 °C |
| `chuva_fora_da_faixa` | precipitação fora de 0 a 1.000 mm/dia |

Além das regras, a silver confere duas coisas: que as unidades nos sidecars são °C e mm, e que cada UF
usa uma única célula de grade.

**NOAA ONI** (`silver_oni_mes`):

| Regra | Condição |
| --- | --- |
| `ano_invalido` | o ano não é número |
| `oni_invalido_ou_fora_da_faixa` | o valor do mês não é número ou está fora de −5 a 5 |

O sentinela de "sem dado" é lido do rodapé gravado no sidecar, sem número fixo no código. Os meses com
o sentinela (meses que ainda não aconteceram) saem da tabela e são contados no relatório.

**Outros descartes rastreados** (contados em `data/silver/_relatorios/silver_relatorio.json`):
- linhas fora da janela de 2004 a 2025;
- versões antigas da mesma chave, de cargas anteriores;
- duplicatas exatas.

## 3. Deduplicação entre cargas

A bronze é *append-only*: cada carga fica ao lado das anteriores, então a mesma linha da origem aparece
uma vez por carga. A silver deduplica **por chave de negócio**:

1. **Vence a versão mais recente:** `DataVersao` da EPE e, em empate, o `_id_carga` mais novo.
2. **Duplicata exata** (mesma chave e mesmos valores) é colapsada em uma linha.
3. **Mesma chave com valores diferentes na mesma versão** é um conflito: as linhas vão para a
   quarentena com a regra `chave_duplicada_valores_conflitantes`, em vez de a silver escolher uma delas
   em silêncio.

## 4. Cruzamento (energia × clima × ONI)

- **Chave:** `cod_ibge_uf` + `data_ref` entre energia e clima, e `data_ref` com o ONI. Nenhuma fonte
  traz o código IBGE; ele vem de `dim_uf`, uma referência fixa no código.
- **Join:** `left` a partir da energia, com `validate="m:1"`. Clima e ONI têm uma linha por chave, então
  o join não multiplica linhas. Uma checagem confere que o número de linhas e o consumo total são os
  mesmos antes e depois.
- **Órfãos:** os pares sem correspondência vão para `silver_orfaos_join`, com o lado
  (`energia_sem_clima` ou `clima_sem_energia`) e o motivo. A linha de energia não é descartada: ela fica
  com `flag_sem_clima` / `flag_sem_oni`.
- **Na última execução:** 7.128 UF-meses de cada lado, **0 órfãos**.
- **Na gold:** se faltar clima para algum UF-mês da energia, a gold **para** com a instrução de reingerir
  o clima, em vez de encolher a janela em silêncio.

## 5. Idempotência

| Camada | Garantia | Prova |
| --- | --- | --- |
| raw / bronze / quarentena | *append-only*: nada é sobrescrito; cada carga tem seu `id_carga` | o hash por registro identifica a mesma linha em cargas diferentes |
| Open-Meteo | checkpoint: páginas (UF × ano) já completas não são pedidas de novo | `testar_checkpoint()`; uma segunda ingestão baixa 0 páginas |
| silver | reconstruída inteira da bronze, com gravação atômica (arquivo temporário + `os.replace`) | seção 10 do notebook: roda duas vezes e compara o hash de cada tabela; a "prova extra" da mesma seção, rodada depois de uma nova ingestão, compara o conteúdo sem as colunas `_*` |
| gold | reconstruída inteira da silver | seção 11 do notebook: a segunda execução gera as mesmas 8 tabelas |

Execução dupla verificada em 2026-10-09: com duas cargas lado a lado na bronze, o conteúdo das 8 tabelas
da silver ficou idêntico ao da carga única.

## 6. Verificações da gold (`notebooks/gold.ipynb`)

Rodam a cada execução. As críticas interrompem a execução; os avisos ficam no relatório.

- **Testes com dados sintéticos de resposta conhecida:**
  - defasagem por data, em que um mês ausente vira nulo (`testar_defasagem_por_data`);
  - indicadores de ENSO causais, em que cortar o futuro não muda o passado (`testar_flags_causais`);
  - dias úteis com feriados nacionais (`testar_dias_uteis`).
- **Conferências sobre os dados reais:**
  - lags conferidos contra uma busca independente, linha a linha (`testar_lags_nas_features`);
  - anti-vazamento: perturba um mês em toda a silver e reconstrói a gold (`testar_sem_vazamento`;
    detalhes em [`anti-vazamentos.md`](anti-vazamentos.md));
  - o consumo total é igual ao da silver; a grade UF × mês × classe está completa; as anomalias têm
    média zero no período-base; os pesos regionais somam 1.
- **Nulos esperados nas features**, todos estruturais e conferidos em código:
  - primeiro mês: lags de 1 mês;
  - primeiros 12 meses: `ar_y_log_lag12` e `y_yoy_*`;
  - 1 grão com consumo ≤ 0 após a soma (AP/rural/2007-03, −44 MWh cativo), em que o log não existe.

## 7. Casos conhecidos

- **Um registro com `Consumidores = -232`** (EPE, tabela por UF) está na quarentena. A linha inteira sai
  da silver, inclusive o consumo, que era válido. Uma alternativa seria anular só o número de
  consumidores; é uma decisão de quem cuida da silver.
- **AP / rural / 2007-03** tem consumo **cativo** negativo (−44 MWh). A silver só espera estornos no
  mercado livre. O valor fica como publicado e marcado (`flag_consumo_nao_positivo` na gold).
- **`dias_calor` (dias com máxima ≥ 35 °C)** é quase sempre 0 em 16 UFs. A métrica serve pouco nesses
  estados.
