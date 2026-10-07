# El ninõ e a sua influência nas contas referentes ao Brasil:

* **Pergunta Central:** Como a presença do fenômeno El Niño influencia o consumo de energia elétrica no Brasil?
* **Título:** *Impacto do Fenômeno El Niño na Demanda de Energia Elétrica no Brasil: Uma Abordagem Preditiva via Aprendizado de Máquina* 

Possíveis base para análise preditívas:

psl.noaa.gov/data/timeseries/month/DS/ONI/ <br>
epe.gov.br/pt/publicacoes-dados-abertos/dados-abertos/dados-do-consumo-mensal-de-energia-eletrica<br> 
servicodados.ibge.gov.br/api/docs/agregados<br> 
ipeadata.gov.br/api <br>
dados.ons.org.br <br>

Sobre as bases

O fenômeno El Niño eleva as temperaturas médias e altera a distribuição de chuvas no Brasil, gerando um pico imediato na demanda por refrigeração (elevando o consumo residencial e comercial) e reduzindo o nível dos reservatórios hidrelétricos, o que aciona usinas térmicas e encarece o custo da energia.

**Fontes de Dados para a Análise**

| Fonte | Base / API | Frequência | Aplicação Principal no Modelo |
| --- | --- | --- | --- |
| **NOAA** | Oceanic Niño Index (ONI) | Mensal | **Sinal Climático:** Mede anomalias na temperatura do Pacífico Equatorial (Região Niño 3.4) para categorizar eventos de El Niño, La Niña e Neutralidade. |
| **Open-Meteo** | Archive API (ERA5), uma capital por UF | Diária | **Sinal Climático local:** temperatura média e máxima (demanda por refrigeração) e precipitação. |
| **EPE** | Consumo Mensal de Energia | Mensal | **Target (Macro):** Consumo agregado de energia por classe (residencial, industrial, comercial, rural) e por subsistema elétrico. |

**Arquitetura do Fluxo de Dados**

* **Clima e Oferta Futura:** O índice ONI (NOAA) antecipa o regime climático → Afeta o volume de chuvas nas bacias hidrográficas → Impacta a vazão e o nível dos reservatórios monitorados pelo ONS.
* **Operação e Preço do Setor:** O ONS registra o equilíbrio entre oferta e demanda em tempo real, ditando o nível de acionamento térmico e o Custo Marginal de Operação (CMO).
* **Demanda de Mercado:** A EPE fornece a curva do consumo agregado por setor.

## Ingestão: camadas e armadilhas

Tudo é gerado por `notebooks/ingestao.ipynb`. Cada execução é uma **carga** com
`ID_CARGA` (`YYYYmmddTHHMMSSZ`, UTC); nada é sobrescrito, a carga nova fica ao lado das
anteriores. Janela de análise: 2015–2025. A silver ainda não existe.

| Camada | Caminho | Conteúdo |
| --- | --- | --- |
| raw | `data/raw/<fonte>/<id_carga>/` | bytes como vieram + sidecar `.meta.json` (`_origem`, `_extraido_em`, `_id_carga`, `_sha256` do arquivo) |
| bronze | `data/bronze/<tabela>/<id_carga>.parquet` | 1 linha por registro da origem; colunas originais, **todas `string`**; mais `_id_carga`, `_extraido_em`, `_origem`, `_arquivo_raw`, `_linha`, `_hash_registro` |
| quarentena | `data/quarentena/<tabela>/<id_carga>.parquet` | registros que falharam no parse estrutural: `_registro_bruto` + `_motivo` |

| Tabela bronze | Raw | Registro = |
| --- | --- | --- |
| `epe_consumo_subsistema` | `epe_consumo/consumo_mensal_historico.xlsx`, aba `CONSUMO E NUMCONS SAM` | linha da aba |
| `epe_consumo_uf` | mesmo arquivo, aba `CONSUMO E NUMCONS SAM UF` | linha da aba |
| `noaa_oni` | `noaa_oni/oni.data` | um ano (`ano`, `m01`..`m12`) |
| `openmeteo_clima` | `openmeteo_clima/clima_<UF>_<ano>.json` (27 × 11 páginas) | um dia de uma capital |

Para ler: `pd.read_parquet("data/bronze/<tabela>/")` junta todas as cargas. Para
deduplicar entre cargas, use `_hash_registro`: o mesmo dado gera o mesmo hash.

A quarentena só pega **erro estrutural**: byte que não decodifica no encoding declarado,
número de campos errado, campo obrigatório vazio e arrays desalinhados. Faixa, sentinela
e calendário são papel da silver.

**EPE**
- Aba por subsistema (região × subsistema × classe × cativo/livre) e aba por UF. Os dados vão de 2004 em diante; a janela 2015–2025 é recortada na silver.
- `Data` vem como `AAAAMMDD` em texto. `DataVersao` muda a cada publicação da EPE, o que muda o hash da linha inteira.
- `Sistema = SISTEMAS ISOLADOS` está fora do SIN.
- Há consumo negativo: são estornos do mercado livre, publicados assim pela EPE.
- O consumo é **faturado**, com defasagem de cerca de um mês em relação ao consumo real.
- A migração de cativo para livre ao longo da janela deixa não estacionária a série separada por tipo de consumidor; some as duas.

**NOAA ONI**
- Texto em utf-8 separado por espaço. A primeira linha declara o primeiro e o último ano, e só esse bloco vira registro.
- O sentinela `-99.9` também marca os meses que ainda não aconteceram e chega à bronze como texto. O valor declarado está no sidecar (`_rodape`). Filtre na silver, lendo de lá, sem hardcode.
- O ONI é a média móvel **centrada** de 3 meses: o valor do mês m usa m+1. No modelo, use lag ≥ 1 para não vazar o futuro.
- O rodapé informa a versão do ERSST. Valores históricos mudam entre versões.

**Open-Meteo**
- A paginação é por janela de tempo: uma página por capital × ano. As variáveis são `temperature_2m_mean`, `temperature_2m_max` e `precipitation_sum`, com unidades no sidecar (`_unidades`).
- `latitude`/`longitude` do registro são da **célula de grade** que a API usou, não do ponto pedido. As duas coordenadas estão no sidecar, e a UF está no nome do arquivo raw (`_arquivo_raw`).
- O mapeamento UF → subsistema e a ponderação (por exemplo, pelo consumo da aba UF da EPE) ficam para a silver.

## Fontes avaliadas e não usadas

Ficaram de fora por decisão do grupo. O mapeamento abaixo foi feito e conferido para o caso de alguma voltar.

| Fonte | Acesso | Formato | Por que considerar |
| --- | --- | --- | --- |
| **ONS** EAR e carga | `https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/ear_subsistema_di/EAR_DIARIO_SUBSISTEMA_{ano}.csv` e `.../carga_energia_di/CARGA_ENERGIA_{ano}.csv` | CSV ascii, separador `;` | Único elo de reservatório da cadeia ONI → chuva → reservatório; carga medida sem a defasagem de faturamento |
| **INMET** | `https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip` (90–117 MB, ~485 estações). A API `apitempo` exige token. | CSV latin-1, `;`, decimal `,`, 8 linhas de metadados; o cabeçalho e o formato de data/hora mudam em 2019; ausente é `-9999` até 2018 e vazio depois | Temperatura medida em estação, para validar o Open-Meteo |
| **ANEEL** bandeiras | CKAN `https://dadosabertos.aneel.gov.br/api/3/action/datastore_search?resource_id=0591b8f6-fe54-437b-b72b-1aa2efd46e42` (paginação `limit`/`offset`, 142 registros) | JSON; valor com vírgula decimal (`"30,00"`) | Elo de preço: seca → térmica → bandeira vermelha → consumo cai |
