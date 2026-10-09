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
Read it before touching ingestion or building silver.

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

`main.py`, `app/**/*.py`, and every file under `sql/` are empty placeholders.
Don't assume a module exists because its file does — `cat` it first.

## Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd notebooks && jupyter nbconvert --to notebook --execute ingestao.ipynb --output ingestao.ipynb --ExecutePreprocessor.timeout=1800
```

The notebook must run with `notebooks/` as the working directory — paths are built from
`Path.cwd().parent`. One run takes ~16 min (594 Open-Meteo pages, 1 s apart to stay under
the free-tier rate limit; ~4,600 weighted calls, close to the 5,000/h cap — run it once). Its built-in checks: `testar_quarentena()` (synthetic bad lines
must land in quarantine) and a final cell asserting sidecars, metadata columns, unique
hashes and expected counts. No tests, linter, or build.

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
  load (newest wins), business rules applied, idempotent (hash-proven).
- **gold** — `notebooks/gold.ipynb` → `data/gold/*.parquet`: dimensions (`gold_dim_tempo`,
  `gold_dim_enso`, `gold_dim_uf`), fact (`gold_fato_consumo_uf_mes`), climate (normals,
  anomalies, weighted aggregates) and the model table `gold_features_uf_mes`. Lags are by
  date, never by row position. `fase_enso` is retrospective (uses future months): it stays
  descriptive in `gold_dim_enso`; features use only the causal flags. No train/test split in gold.
- `app/` — Streamlit-shaped dashboard, empty.

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
