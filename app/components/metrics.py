"""Leitura da gold e agregações do dashboard. Nada aqui lê a silver."""
from pathlib import Path

import pandas as pd
import streamlit as st

GOLD = Path(__file__).resolve().parents[2] / "data" / "gold"
TABELAS = ["gold_fato_consumo_uf_mes", "gold_dim_enso", "gold_dim_tempo", "gold_clima_agregado_mes"]


@st.cache_data
def carregar():
    faltam = [t for t in TABELAS if not (GOLD / f"{t}.parquet").exists()]
    if faltam:
        st.error(f"Gold ausente: {faltam}. Rode notebooks/ingestao, silver e gold, nessa ordem.")
        st.stop()
    return {t: pd.read_parquet(GOLD / f"{t}.parquet") for t in TABELAS}


def enso_defasado(dim_enso, k):
    """ENSO do mês t-k na linha do mês t (casando por data, como na gold)."""
    return dim_enso[["data_ref", "oni", "fase_enso"]].assign(data_ref=dim_enso["data_ref"] + pd.DateOffset(months=k))


def consumo_mensal(fato, regioes, classes):
    """Consumo por dia do recorte, mês a mês, e variação sobre o mesmo mês do ano anterior (%)."""
    f = fato[fato["regiao"].isin(regioes) & fato["classe"].isin(classes)]
    s = f.groupby("data_ref", as_index=False)["consumo_mwh"].sum()
    s["consumo_mwh_por_dia"] = s["consumo_mwh"] / s["data_ref"].dt.days_in_month
    ant = s[["data_ref", "consumo_mwh_por_dia"]].assign(data_ref=s["data_ref"] + pd.DateOffset(months=12))
    s = s.merge(ant, on="data_ref", how="left", suffixes=("", "_ano_ant"))
    s["yoy_pct"] = 100 * (s["consumo_mwh_por_dia"] / s["consumo_mwh_por_dia_ano_ant"] - 1)
    return s.drop(columns="consumo_mwh_por_dia_ano_ant")


def com_enso(serie, dim_enso, dim_tempo, k):
    return (serie.merge(enso_defasado(dim_enso, k), on="data_ref", how="left")
                 .merge(dim_tempo[["data_ref", "flag_covid"]], on="data_ref", how="left"))


def sem_covid(df):
    return df[~df["flag_covid"].fillna(False).astype(bool)]


def efeito_por_fase(serie):
    """Resume a variação anual do consumo por fase do ENSO.

    Entrada: uma linha por mês com `yoy_pct` (pode ter nulos nos 12 primeiros meses) e
    `fase_enso` (el_nino, neutro, la_nina), já defasada e, se pedido, sem os meses de COVID.
    Saída: uma linha por fase com `fase_enso`, `n_meses`, `yoy_pct` (o resumo da fase) e
    `dif_vs_neutro` (yoy_pct da fase menos o do neutro, em pontos percentuais).
    """
    r = (serie.dropna(subset=["yoy_pct", "fase_enso"])
              .groupby("fase_enso", as_index=False)
              .agg(n_meses=("yoy_pct", "size"), yoy_pct=("yoy_pct", "mean")))
    neutro = r.loc[r["fase_enso"] == "neutro", "yoy_pct"]
    r["dif_vs_neutro"] = r["yoy_pct"] - (neutro.iloc[0] if len(neutro) else float("nan"))
    return r


def clima_por_fase(clima_agr, dim_enso, k, regioes):
    """Anomalia média de temperatura e chuva por escopo (regiões escolhidas + Brasil) e fase do ENSO em t-k."""
    c = clima_agr[(clima_agr["escopo"] == "brasil") | clima_agr["id_escopo"].isin(regioes)]
    c = c.merge(enso_defasado(dim_enso, k), on="data_ref", how="left")
    return c.groupby(["id_escopo", "fase_enso"], as_index=False)[["anom_temp_media_c", "anom_precip_mm"]].mean()


def correlacao_por_defasagem(serie, dim_enso, dim_tempo, lags, excluir_covid):
    linhas = []
    for k in lags:
        d = com_enso(serie, dim_enso, dim_tempo, k)
        if excluir_covid:
            d = sem_covid(d)
        linhas.append({"defasagem_meses": k, "correlacao": d["yoy_pct"].corr(d["oni"])})
    return pd.DataFrame(linhas)
