from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from components.metrics import (carregar, clima_por_fase, com_enso, consumo_mensal, correlacao_por_defasagem,
                                efeito_por_fase, efeito_regiao_classe, sem_covid)

FASES = alt.Scale(domain=["el_nino", "neutro", "la_nina"], range=["#d62728", "#9e9e9e", "#1f77b4"])
ANALISE = Path(__file__).resolve().parents[1] / "analise.md"


def analise(secao):
    """Texto da seção `## secao` de app/analise.md, lido a cada recarga (editar o .md e dar F5)."""
    texto = ANALISE.read_text(encoding="utf-8") if ANALISE.exists() else ""
    blocos = dict(b.split("\n", 1) for b in texto.split("\n## ")[1:] if "\n" in b)
    if blocos.get(secao, "").strip():
        with st.container(border=True):
            st.markdown(blocos[secao])

g = carregar()
fato, dim_enso, dim_tempo = g["gold_fato_consumo_uf_mes"], g["gold_dim_enso"], g["gold_dim_tempo"]

st.title("El Niño e o consumo de energia elétrica no Brasil")
st.caption("Pergunta central: como a presença do El Niño influencia o consumo de energia elétrica no Brasil? "
           "Consumo faturado da EPE, ONI da NOAA e clima das capitais (Open-Meteo).")

with st.sidebar:
    todas_regioes, todas_classes = sorted(fato["regiao"].unique()), sorted(fato["classe"].unique())
    regioes = st.multiselect("Regiões", todas_regioes, default=todas_regioes)
    classes = st.multiselect("Classes de consumo", todas_classes, default=todas_classes)
    k = st.slider("Defasagem do ENSO (meses)", 0, 12, 2,
                  help="Compara o mês t com o ENSO de t−k. O consumo da EPE é faturado ~1 mês depois do real.")
    excluir_covid = st.checkbox("Excluir meses de COVID das estatísticas", True,
                                help="2020–21 coincide com La Niña; sem excluir, a queda da pandemia vira 'efeito' do ENSO.")
if not regioes or not classes:
    st.warning("Escolha ao menos uma região e uma classe.")
    st.stop()


def recorte(cls, filtrar=True):
    s = com_enso(consumo_mensal(fato, regioes, cls), dim_enso, dim_tempo, k)
    return sem_covid(s) if filtrar and excluir_covid else s


serie, base = recorte(classes, filtrar=False), recorte(classes)

c1, c2, c3, c4 = st.columns(4)
fases = base["fase_enso"].value_counts()
c1.metric("Consumo no recorte", f"{serie['consumo_mwh'].sum() / 1e6:,.0f} TWh")
c2.metric("Meses de El Niño", int(fases.get("el_nino", 0)))
c3.metric("Meses de La Niña", int(fases.get("la_nina", 0)))
c4.metric(f"Correlação ONI(t−{k}) × consumo", f"{base['yoy_pct'].corr(base['oni']):+.2f}",
          help="Pearson entre o ONI defasado e a variação anual do consumo.")
analise("resumo")

st.header("Linha do tempo")
janela = dim_enso[dim_enso["data_ref"].between(serie["data_ref"].min(), serie["data_ref"].max())]
x = alt.X("data_ref:T", title=None)
st.altair_chart(alt.Chart(janela).mark_bar().encode(
    x, alt.Y("oni:Q", title="ONI"), alt.Color("fase_enso:N", scale=FASES, title="Fase"),
    tooltip=["data_ref:T", "oni:Q", "fase_enso:N"]).properties(height=180), width="stretch")
st.altair_chart(alt.Chart(serie).mark_line().encode(
    x, alt.Y("yoy_pct:Q", title="Consumo: variação anual (%)"),
    tooltip=["data_ref:T", alt.Tooltip("yoy_pct:Q", format=".1f")]).properties(height=220), width="stretch")
analise("linha_do_tempo")

st.header("1º elo: ENSO → clima local")
st.caption(f"Anomalia média (vs. normal 2004–2014) por fase do ENSO em t−{k}. A doc espera mais calor e chuva alterada no El Niño.")
clima = clima_por_fase(g["gold_clima_agregado_mes"], dim_enso, k, regioes)
col_t, col_p = st.columns(2)
for col, campo, titulo in ((col_t, "anom_temp_media_c", "Anomalia de temperatura (°C)"),
                           (col_p, "anom_precip_mm", "Anomalia de chuva (mm/mês)")):
    col.altair_chart(alt.Chart(clima).mark_bar().encode(
        alt.X("fase_enso:N", title=None, sort=FASES.domain), alt.Y(f"{campo}:Q", title=titulo),
        alt.Color("fase_enso:N", scale=FASES, legend=None), alt.Column("id_escopo:N", title=None),
        tooltip=["id_escopo:N", "fase_enso:N", alt.Tooltip(f"{campo}:Q", format=".2f")]))
analise("clima")

st.header("2º elo: ENSO → consumo")
st.dataframe(efeito_por_fase(base), hide_index=True)
st.caption("Diferença da variação anual em relação aos meses neutros, por classe. "
           "A doc espera alta em residencial e comercial (refrigeração).")
por_classe = pd.concat([efeito_por_fase(recorte([c])).assign(classe=c) for c in classes])
st.altair_chart(alt.Chart(por_classe).mark_bar().encode(
    alt.X("fase_enso:N", title=None, sort=FASES.domain), alt.Y("dif_vs_neutro:Q", title="p.p. vs. neutro"),
    alt.Color("fase_enso:N", scale=FASES, legend=None), alt.Column("classe:N", title=None),
    tooltip=["classe:N", "fase_enso:N", "n_meses:Q", alt.Tooltip("dif_vs_neutro:Q", format=".2f")]))
analise("consumo")

st.header("Onde o efeito aparece: região × classe")
st.caption(f"El Niño em t−{k} menos neutro, em p.p. de variação anual do consumo. Usa todas as regiões e classes "
           "(ignora os filtros); segue a defasagem e a exclusão da COVID da barra lateral.")
rc = efeito_regiao_classe(fato, dim_enso, dim_tempo, k, excluir_covid)
eixo_x = alt.X("classe:N", title=None, sort=todas_classes + ["todas"])
eixo_y = alt.Y("regiao:N", title=None, sort=todas_regioes + ["brasil"])
limite = float(rc["el_nino_pp"].abs().max())
mapa = alt.Chart(rc).encode(eixo_x, eixo_y)
st.altair_chart(
    mapa.mark_rect().encode(
        alt.Color("el_nino_pp:Q", title="p.p.", scale=alt.Scale(scheme="redblue", reverse=True, domain=[-limite, limite])),
        tooltip=["regiao:N", "classe:N", alt.Tooltip("el_nino_pp:Q", format="+.2f"), "n_meses:Q"])
    + mapa.mark_text(fontSize=13).encode(alt.Text("el_nino_pp:Q", format="+.1f")),
    width="stretch")
analise("regiao_classe")

st.header("Em quantos meses o sinal aparece?")
corr = correlacao_por_defasagem(consumo_mensal(fato, regioes, classes), dim_enso, dim_tempo, range(13), excluir_covid)
st.altair_chart(alt.Chart(corr).mark_bar().encode(
    alt.X("defasagem_meses:O", title="Defasagem do ONI (meses)"), alt.Y("correlacao:Q", title="Correlação com o consumo"),
    tooltip=["defasagem_meses:O", alt.Tooltip("correlacao:Q", format="+.3f")]).properties(height=220), width="stretch")
analise("defasagem")

st.header("Conclusão")
analise("conclusao")

st.divider()
st.caption("Leitura: correlação não é causalidade; a tendência e a migração cativo→livre pesam no consumo. "
           "`fase_enso` é retrospectiva (usa meses futuros): serve para descrever, não como feature do modelo. "
           "O elo reservatório → térmica → preço depende do ONS, que ficou fora das fontes.")
