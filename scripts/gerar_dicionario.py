"""Gera docs/dicionario_de_dados.md a partir dos dicionários e relatórios que a silver e a gold gravam em data/.

data/ fica fora do Git; este arquivo leva os metadados para o repositório. Rode da raiz, depois da gold:
    python scripts/gerar_dicionario.py
"""
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
SAIDA = RAIZ / "docs" / "dicionario_de_dados.md"

GRAO = {  # tabela: granularidade em uma frase (exigência do Requisito 3)
    "dim_uf": "uma linha por UF (27)",
    "silver_energia_uf": "uma linha por UF × mês × subsistema × classe × tipo de consumidor (cativo/livre)",
    "silver_energia_subsistema": "uma linha por região × mês × subsistema × classe × tipo de consumidor",
    "silver_clima_uf_mes": "uma linha por UF × mês (clima diário da capital agregado no mês)",
    "silver_oni_mes": "uma linha por mês, série inteira do ONI (desde 1950)",
    "silver_energia_clima": "a mesma de silver_energia_uf, com o clima da UF-mês e o ONI do mês",
    "silver_orfaos_join": "uma linha por lado × UF × mês que ficou sem par no cruzamento",
    "silver_quarentena": "uma linha por registro rejeitado × regra violada (sem chave de negócio)",
    "gold_dim_tempo": "uma linha por mês da janela",
    "gold_dim_enso": "uma linha por mês da série do ONI",
    "gold_dim_uf": "uma linha por UF (27)",
    "gold_fato_consumo_uf_mes": "uma linha por UF × mês × classe (cativo + livre e todos os subsistemas somados)",
    "gold_climatologia_uf": "uma linha por UF × mês do ano (normal do período-base)",
    "gold_clima_uf_mes": "uma linha por UF × mês",
    "gold_clima_agregado_mes": "uma linha por escopo (região ou Brasil) × mês",
    "gold_features_uf_mes": "uma linha por UF × mês × classe (base ML-Ready)",
}


def celula(v):
    return "" if pd.isna(v) else str(v).replace("|", "\\|").replace("\n", " ")


def num(v):
    return f"{v:,}".replace(",", ".") if isinstance(v, int) else v


def tabela_md(df):
    linhas = ["| " + " | ".join(df.columns) + " |", "|" + " --- |" * len(df.columns)]
    linhas += ["| " + " | ".join(celula(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(linhas)


def main():
    sil = pd.read_csv(DATA / "silver" / "_relatorios" / "dicionario_silver.csv").rename(columns={"chave_primaria": "chave"})
    gol = pd.read_csv(DATA / "gold" / "dicionario_gold.csv")
    dic = pd.concat([sil.assign(camada="silver"), gol.assign(camada="gold")], ignore_index=True)
    faltam = sorted(set(dic["tabela"]) - set(GRAO))
    assert not faltam, f"tabelas sem granularidade declarada em GRAO: {faltam}"

    rel_s = json.loads((DATA / "silver" / "_relatorios" / "silver_relatorio.json").read_text(encoding="utf-8"))
    rel_g = json.loads(sorted((DATA / "gold" / "_relatorios").glob("gold_*.json"))[-1].read_text(encoding="utf-8"))
    n_linhas = {**rel_s["linhas_por_tabela"], **rel_g["linhas"]}

    # cada fonte sai de uma tabela de fonte única (a licença do Open-Meteo contém "; ", o separador das multifonte)
    unicas = dic[dic["url"].notna() & ~dic["url"].str.contains("; ", na=False)]
    fontes = (unicas[["fonte", "url", "licenca", "data_coleta"]].drop_duplicates()
              .rename(columns={"licenca": "licença", "data_coleta": "data de coleta"}).sort_values("fonte"))

    tabelas = []
    for t, d in dic.groupby("tabela", sort=False):
        pk = ", ".join(d.loc[d["chave"].astype(bool), "coluna"]) or "—"
        tabelas.append({"camada": d["camada"].iloc[0], "tabela": f"`{t}`", "granularidade": GRAO[t],
                        "chave primária": pk, "linhas": f"{n_linhas.get(t, 0):,}".replace(",", ".")})

    j = rel_s["join"]
    descartes = []
    for t in ("silver_energia_uf", "silver_energia_subsistema", "silver_clima_uf_mes", "silver_oni_mes"):
        st = rel_s[t]
        descartes.append({"tabela": f"`{t}`", "linhas na bronze (todas as cargas)": num(st["linhas_bronze"]),
                          "fora da janela": num(st.get("fora_da_janela", "—")),
                          "versões antigas (outras cargas)": num(st["versoes_antigas_descartadas"]),
                          "duplicatas exatas": st["duplicatas_exatas_descartadas"],
                          "quarentena (por regra)": ", ".join(f"{k}: {v}" for k, v in st["quarentena_por_regra"].items()) or "0",
                          "conflitos → quarentena": st["conflitos_para_quarentena"],
                          "linhas na silver": num(st["linhas_silver"])})
    oni = rel_s["silver_oni_mes"]

    partes = [
        "# Dicionário de dados",
        "",
        "> **Gerado** por `scripts/gerar_dicionario.py` a partir de `data/silver/_relatorios/` e `data/gold/`."
        " Não edite à mão: mude `COLUNAS`/`DOMINIO`/`FONTES` nos notebooks, rode o pipeline e gere de novo.",
        "",
        f"Janela de análise: **{rel_s['janela'][0][:7]} a {rel_s['janela'][1][:7]}**.",
        "",
        "## Fontes",
        "",
        tabela_md(fontes),
        "",
        "## Tabelas",
        "",
        "A chave primária de cada tabela é verificada em código a cada execução (sem nulos e sem duplicata).",
        "",
        tabela_md(pd.DataFrame(tabelas)),
        "",
        "## Cruzamento (Requisito 1)",
        "",
        "Chave: **`cod_ibge_uf` + `data_ref` (ano/mês)** entre energia (EPE) e clima (Open-Meteo); **`data_ref`** com o ONI.",
        "O join é `left` a partir da energia, com `validate=\"m:1\"`: nenhuma linha de consumo é descartada pelo cruzamento.",
        "Órfãos ficam em `silver_orfaos_join`, e a linha de energia continua com `flag_sem_clima` / `flag_sem_oni`.",
        "",
        "| medida | valor |",
        "| --- | --- |",
        f"| UF-meses com consumo | {j['uf_meses_energia']:,} |".replace(",", "."),
        f"| UF-meses com clima | {j['uf_meses_clima']:,} |".replace(",", "."),
        f"| UF-meses de energia sem clima (órfãos) | {j['uf_meses_energia_sem_clima']} |",
        f"| UF-meses de clima sem energia (órfãos) | {j['uf_meses_clima_sem_energia']} |",
        f"| linhas de energia sem ONI | {j['linhas_sem_oni']} |",
        f"| linhas antes → depois do join | {j['linhas_energia_antes']:,} → {j['linhas_apos_join']:,} |".replace(",", "."),
        f"| consumo total preservado | {j['consumo_total_mwh']:,.0f} MWh |".replace(",", "."),
        "",
        "## Descartes e quarentena (nada some sem rastro)",
        "",
        "Cada linha da bronze que não chega à silver é contada aqui. As regras estão em `docs/qualidade_dos_dados.md`.",
        "A bronze acumula todas as cargas, então a mesma linha da origem aparece uma vez por carga: \"versões antigas\"",
        "é a cópia das cargas anteriores (a mais recente vence), e a quarentena por regra conta a mesma falha em cada",
        "carga. A tabela `silver_quarentena` guarda cada falha uma vez só.",
        "",
        tabela_md(pd.DataFrame(descartes)),
        "",
        "Clima e ONI mudam de grão na silver, sem descarte: dias viram UF-meses (agregação) e o ONI passa de uma linha"
        " por ano (12 colunas) para uma por mês.",
        "",
        f"ONI: {oni['meses_sentinela_descartados']} meses com o sentinela `{oni['sentinela']}` (meses ainda não"
        " ocorridos, valor lido do rodapé da fonte) ficam fora; " f"{oni['oni_invalido']} valores inválidos.",
        "",
        f"Total final em `silver_quarentena`: {sum(rel_s['quarentena_por_tabela_e_regra'].values())} registro(s) — "
        + (", ".join(f"`{k}`: {v}" for k, v in rel_s["quarentena_por_tabela_e_regra"].items()) or "nenhum") + ".",
        "",
        "## Colunas",
        "",
        "`papel` (só em `gold_features_uf_mes`): `chave`, `alvo` ou `feature`. Quais features valem no t0 do modelo"
        " está em `docs/ml-ready.md`, seção 3.",
    ]
    for t, d in dic.groupby("tabela", sort=False):
        cols = ["coluna", "tipo", "chave"] + (["papel"] if t == "gold_features_uf_mes" else []) + ["dominio", "descricao"]
        partes += ["", f"### `{t}` ({d['camada'].iloc[0]})", "", f"Granularidade: {GRAO[t]}. "
                   f"Fonte: {celula(d['fonte'].iloc[0])}.", "",
                   tabela_md(d[cols].assign(chave=d["chave"].map({True: "PK", False: ""}))
                             .rename(columns={"dominio": "domínio", "descricao": "descrição"}))]
    SAIDA.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"{SAIDA.relative_to(RAIZ)}: {dic['tabela'].nunique()} tabelas, {len(dic)} colunas")


if __name__ == "__main__":
    main()
