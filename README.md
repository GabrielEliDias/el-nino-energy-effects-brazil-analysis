# El Niño e o consumo de energia elétrica no Brasil

Projeto integrador (CESUPA): pipeline de dados público → Bronze → Silver → Gold → dashboard,
para responder **como a presença do El Niño influencia o consumo de energia elétrica no Brasil**.
Especificação e armadilhas de cada base: [`docs/dataset.md`](docs/dataset.md).
Documentação em `docs/`:
- [`dicionario_de_dados.md`](docs/dicionario_de_dados.md) — fontes, granularidade e colunas de cada tabela, cruzamento e descartes (gerado);
- [`qualidade_dos_dados.md`](docs/qualidade_dos_dados.md) — quarentena, deduplicação, cruzamento e idempotência;
- [`ml-ready.md`](docs/ml-ready.md) — rótulo, coorte, t0, janelas, split, baseline e métrica;
- [`anti-vazamentos.md`](docs/anti-vazamentos.md) — o que foi corrigido, como provamos e o checklist;
- [`decisao.md`](docs/decisao.md) — decisor, ação, custos de erro, limiar e limitações;
- [`pendencias.md`](docs/pendencias.md) — situação por requisito, o que falta e roteiro da defesa.

## Fontes

| Fonte | Instituição | Acesso | Formato | Licença |
| --- | --- | --- | --- | --- |
| [Consumo mensal de energia elétrica](https://www.epe.gov.br/sites-pt/publicacoes-dados-abertos/dados-abertos/Documents/Dados_abertos_Consumo_Mensal.xlsx) (alvo) | EPE | arquivo | XLSX | CC BY 4.0 |
| [Oceanic Niño Index (ONI)](https://psl.noaa.gov/data/correlation/oni.data) | NOAA (CPC, via PSL) | arquivo | texto separado por espaço | domínio público (governo federal dos EUA) |
| [Archive API](https://archive-api.open-meteo.com/v1/archive) — clima diário da capital de cada UF | Open-Meteo (reanálise ERA5, Copernicus C3S) | API REST paginada | JSON | CC BY 4.0 — "Weather data by Open-Meteo.com"; ERA5 sob a licença do Copernicus |

Chave de cruzamento: **código IBGE da UF + ano/mês** (ONI só por ano/mês). A data de coleta de cada
fonte e o URL ficam nos dicionários de dados (`data/silver/_relatorios/dicionario_silver.csv` e
`data/gold/dicionario_gold.csv`), calculados a partir das cargas efetivamente usadas.

## Como rodar do zero

Requer Python 3.14 e acesso à internet.

```bash
git clone <url-do-repositório> && cd el-nino-energy-effects-brazil-analysis
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd notebooks
for nb in ingestao silver gold; do
  jupyter nbconvert --to notebook --execute $nb.ipynb --output-dir /tmp/nb_out --ExecutePreprocessor.timeout=1800
done
cd ..

python scripts/gerar_dicionario.py   # atualiza docs/dicionario_de_dados.md (commitar se mudar)
streamlit run app/main.py
```

- Os notebooks rodam com `notebooks/` como diretório de trabalho (os caminhos saem de `Path.cwd().parent`).
- A primeira ingestão leva ~16 min: são 594 páginas do Open-Meteo (27 capitais × 22 anos), 1 s
  entre elas, perto do limite gratuito de 5.000 chamadas por hora. As seguintes só baixam as páginas
  que ainda não estão completas na bronze (checkpoint), e EPE e NOAA vêm inteiros de novo.
- `--output-dir` deixa os notebooks versionados sem as saídas da execução.
- Tudo é gravado em `data/` (fora do Git). Apagar `data/` e rodar de novo reconstrói o pipeline.

## Camadas

| Camada | Onde | O que tem |
| --- | --- | --- |
| raw | `data/raw/<fonte>/<id_carga>/` | bytes como vieram + sidecar `.meta.json` (origem, horário, carga, sha256) |
| bronze | `data/bronze/<tabela>/<id_carga>.parquet` | um registro da origem por linha, tudo `string`, com metadados técnicos e hash do registro |
| quarentena | `data/quarentena/<tabela>/<id_carga>.parquet` | registros com erro estrutural e o motivo |
| silver | `data/silver/` | tipada, deduplicada (versão mais recente vence), regras de negócio, cruzamento e órfãos; violações em `silver_quarentena` |
| gold | `data/gold/` | dimensões, fato de consumo, clima com anomalias e a base ML-Ready `gold_features_uf_mes` |

Cada carga tem um `id_carga` (`AAAAmmddTHHMMSSZ`, UTC) e nada é sobrescrito na raw, na bronze nem
na quarentena. Silver e gold são reconstruídas inteiras e provam idempotência comparando hashes numa
segunda execução.

## Verificações

Não há suíte de testes separada: as checagens rodam dentro dos notebooks e interrompem a execução
quando uma crítica falha.

- **ingestao** — quarentena com dados sintéticos, checkpoint do Open-Meteo, sidecars, metadados,
  hashes únicos e contagens.
- **silver** — chave primária única e sem nulos, junção sem perda de linhas nem de consumo, unidades,
  idempotência.
- **gold** — defasagens por data, indicadores de ENSO causais, dias úteis, conferência dos lags e
  `testar_sem_vazamento`: perturba um mês em toda a silver e prova que nenhuma feature usa o futuro
  nem o consumo do próprio mês.

## Uso de IA

Ferramentas de IA generativa foram usadas neste projeto, conforme exige o enunciado. Todo o grupo
deve saber explicar qualquer trecho.

- **Claude Code (Anthropic)** — <!-- grupo: confirmar e completar com o que cada integrante usou -->
  revisão das camadas silver e gold, auditoria de nulos e de vazamento, correção dos vazamentos da
  gold (`testar_sem_vazamento`, papéis das colunas), dashboard em `app/`, fixação das versões, este
  README, os dicionários de dados com origem e licença e a carga incremental do Open-Meteo.
