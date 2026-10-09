# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Rule: do not touch `src/`

`src/` is frozen. Do not create, edit, or delete anything under it without a direct,
explicit instruction from the user naming that intent. The pipeline is being built in the
notebooks first; scripts come later, once the notebooks settle. `src/01_extract.py` exists
but is **stale and unused** — treat it as a leftover, not as the source of truth.

## Project

Academic data project (Portuguese-language, CESUPA): does El Niño influence electricity
consumption in Brazil? Target is a predictive ML model. `docs/dataset.md` is the spec —
research question, data sources, the intended causal chain (ONI → rainfall → reservoir
levels → thermal dispatch → price/consumption), and the **known traps of each bronze file**.
Read it before touching ingestion or building silver. If it and the code ever disagree, the code wins.

## State of the repo

Ingestion was rewritten from scratch. Live notebooks: **`notebooks/ingestao.ipynb`**
(stops at bronze), **`notebooks/silver.ipynb`** (bronze → `data/silver/`) and
**`notebooks/gold.ipynb`** (silver → `data/gold/`). Silver is **owned by another person** —
change it only when asked (the 2004–2025 window change was an explicit request). The old per-source notebooks (`eda-energy`, `eda-noa`,
`eda-open`) were deleted; their silver code is in git history (and in `stash@{0}` for the
uncommitted last versions) if it's ever useful as reference.

Sources are **only EPE, NOAA ONI and Open-Meteo** — the group's decision. ONS, INMET and
ANEEL were mapped and dropped; their access notes live in `docs/dataset.md` ("Fontes
avaliadas e não usadas"). Don't re-add them unasked.

`main.py`, `README.md`, and every file under `sql/` are empty placeholders.
Don't assume a module exists because its file does — `cat` it first. `usabilidade.ipynb` (repo
root) is an early exploration reading a gitignored `../Bases/` CSV — not part of the pipeline.

## Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # torch/keras are for the future model; the pipeline only needs pandas/pyarrow/openpyxl/requests/jupyter

# full pipeline, in order (each layer reads the previous one from data/)
cd notebooks
for nb in ingestao silver gold; do
  jupyter nbconvert --to notebook --execute $nb.ipynb --output-dir /tmp/nb_out --ExecutePreprocessor.timeout=1800
done
```

`--output-dir` keeps executed outputs out of the tracked notebooks (use `--output $nb.ipynb` only
when you mean to commit outputs — never for `silver.ipynb` unasked). Notebooks must run with
`notebooks/` as the working directory — paths are built from `Path.cwd().parent`.

The first ingestion takes ~16 min (594 Open-Meteo pages = 27 capitals × 22 years, 1 s apart;
~4,600 weighted calls, close to the 5,000/h free-tier cap). Later runs take under a minute:
Open-Meteo is incremental — `paginas_completas()` treats bronze as the checkpoint and only
requests (UF, year) pages missing or incomplete there; EPE and NOAA are re-downloaded whole.
Don't `pip install` into `.venv` while a notebook kernel is running (a pyarrow swap mid-run
broke one ingestion). Silver and
gold take seconds. No pytest, linter, or build; the checks live in the notebooks and run on
every execution:

- **ingestao** — `testar_quarentena()` (synthetic bad lines must land in quarantine) and a final
  cell asserting sidecars, metadata columns, unique hashes and expected counts.
- **silver** — `checar(...)` asserts (critical ones abort): PK unique/non-null, join preserves
  rows and total consumption, units from sidecars. Sections 10–11 re-run the whole silver and
  compare table hashes (idempotence). Report: `data/silver/_relatorios/silver_relatorio.json`.
- **gold** — synthetic tests run first (`testar_defasagem_por_data`, `testar_flags_causais`,
  `testar_dias_uteis`), then `testar_lags_nas_features` re-checks lags by independent lookup,
  `informativos()` asserts where nulls are allowed, and section 11 proves idempotence.
  Report: `data/gold/_relatorios/gold_<timestamp>.json` (includes `nulos_features`).

To run one check, execute the notebook's setup/function cells in a kernel and call it.

## Architecture

Every run is a **load** (`ID_CARGA`, `YYYYmmddTHHMMSSZ` UTC). Append-only: a new load lands
next to the old ones, nothing is overwritten. `data/` is gitignored and re-runnable.

- **raw** — `data/raw/<fonte>/<id_carga>/`: bytes verbatim from the origin plus a
  `.meta.json` sidecar (`_origem`, `_extraido_em`, `_id_carga`, `_sha256`). The only
  faithful copy; reprocess from here.
- **bronze** — `data/bronze/<tabela>/<id_carga>.parquet`: one row per source record,
  original column names, **every column `string`**, no typing/renaming/filtering, plus
  `_id_carga`, `_extraido_em`, `_origem`, `_arquivo_raw`, `_linha`, `_hash_registro`
  (sha256 of the raw record — same data, same hash across loads).
- **quarentena** — `data/quarentena/<tabela>/<id_carga>.parquet`: records that failed
  *structural* parsing (encoding, field count, empty required field, misaligned arrays),
  with `_registro_bruto` and `_motivo`. Business rules (ranges, the `-99.9` sentinel,
  calendar) are silver's job, not quarantine's.
- **silver** — `notebooks/silver.ipynb` → `data/silver/*.parquet`: typed, deduplicated by
  load (newest wins: `DataVersao`, then `_id_carga`), business rules applied, idempotent
  (hash-proven). Rows that break a business rule go to `silver_quarentena` (not dropped
  silently); EPE negatives are reversals (estornos), kept with `flag_estorno`. Overwrites in
  place (atomic `os.replace`), unlike the append-only layers. Every column's type and meaning
  is declared once in `COLUNAS`/`SCHEMAS` and exported as a data dictionary CSV — gold copies
  this pattern.
- **gold** — `notebooks/gold.ipynb` → `data/gold/*.parquet`: dimensions (`gold_dim_tempo`,
  `gold_dim_enso`, `gold_dim_uf`), fact (`gold_fato_consumo_uf_mes`), climate (normals,
  anomalies, weighted aggregates) and the model table `gold_features_uf_mes`. Lags are by
  date, never by row position. `fase_enso` is retrospective (uses future months): it stays
  descriptive in `gold_dim_enso`; features use only the causal flags. No train/test split in gold.
  Column roles in `gold_features_uf_mes` are `COLS_CHAVE` / `COLS_ALVO` / everything else =
  feature (exported as `papel` in `dicionario_gold.csv`). No feature may use the current month's
  consumption (it stays in the fact table; features get `*_lag1`). `testar_sem_vazamento`
  perturbs month T across silver and rebuilds via `montar_tabelas` — any new feature must pass it.
  Gold reads only `dim_uf`, `silver_energia_uf`, `silver_clima_uf_mes`, `silver_oni_mes`
  (not `silver_energia_clima`), sums cativo + livre and all subsystems per UF × month × class,
  and **aborts** if climate doesn't cover every energy UF-month (widening the window means
  re-ingesting Open-Meteo, then re-running silver). Nulls in gold are by design: lag-1
  columns in the first month, `ar_y_log_lag12`/`y_yoy_*` in the first 12 months,
  `y_log_*`/`pct_livre` where summed consumption ≤ 0, ENSO intensity/episode columns in
  neutral months.
- **app** — Streamlit dashboard (`streamlit run app/main.py` from the repo root). Reads only
  `data/gold/`; `main.py` routes via `st.navigation`, the page is `pages/main_page.py`,
  gold loading and aggregations live in `components/metrics.py`. The commentary under each chart
  comes from `app/analise.md` (one `## <key>` section per chart, re-read on every page load):
  edit the text there, not in the page code.

Analysis window is 2004–2025 (`START_YEAR`/`END_YEAR` in `ingestao.ipynb`, `JANELA_INI`/`JANELA_FIM` in
`silver.ipynb`). Gold derives its window from silver and fixes the baseline for climate normals and
weights at 2004–2014 (`BASE_ANOS`).

### Data sources

| Source | Access | Bronze table(s) |
| --- | --- | --- |
| EPE consumo mensal (target) | direct `.xlsx` download, all years since 2004 | `epe_consumo_subsistema`, `epe_consumo_uf` (one per sheet) |
| NOAA ONI | direct download of `oni.data` (utf-8, whitespace-separated) | `noaa_oni` (one row per year; footer → sidecar) |
| Open-Meteo archive | REST, paginated by time window: one page per state capital × year | `openmeteo_clima` (one row per day per capital) |

## Conventions

- Code, comments, and prose are in Portuguese. Match it.
- Paths are built with `pathlib` relative to `Path.cwd().parent`, never hardcoded absolutes.
- HTTP goes through `baixar()` (User-Agent, timeout, retry/backoff honoring `Retry-After`;
  429/5xx transient, other 4xx definitive). Raw bytes go through `salvar_raw()`; text is
  split into records by `ler_delimitado()` (strict per-line decode, declared encoding and
  separator); everything lands via `gravar_bronze()`. All defined once, in
  `ingestao.ipynb` — add a new source as a new section there reusing them.
