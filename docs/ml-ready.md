# Base ML-Ready

Requisito 5 do enunciado (`docs/Projeto_Da_Ingestao_a_Decisao.md`), documentado **antes de treinar
qualquer modelo**. Todos os números saem da gold de 2026-10-09 (carga `20261009T101740Z`) e podem ser
reproduzidos com o código da seção 2.

Documentos relacionados:
- [`anti-vazamentos.md`](anti-vazamentos.md): como provamos que nenhuma feature usa o futuro, e o
  checklist do enunciado respondido;
- [`decisao.md`](decisao.md): a decisão que o modelo apoia (decisor, custos e limiar).

> **Proposta a validar pelo grupo.** O rótulo e o recorte seguem a decisão proposta em `decisao.md`.
> Se o grupo escolher outro decisor, este documento muda junto.

## Por que este problema

A análise exploratória (dashboard, seção "região × classe") mostrou que o El Niño **quase não muda o
consumo nacional**, mas muda o consumo **regional, com sinais opostos**. O efeito mais robusto em
consumo residencial está no **Norte**, onde o El Niño traz 22,7 mm/mês a menos de chuva e +0,43 °C:

- Norte residencial: +2,6 p.p. na variação anual. O sinal é o mesmo nas defasagens de 1 a 6 meses,
  nas duas metades da série e ao tirar cada um dos 7 episódios de El Niño, um de cada vez.
- Pará residencial: até +5,0 p.p., 3 meses depois de o El Niño ser confirmado.

Uma distribuidora que compra energia com base na tendência recente do consumo fica **subcontratada**
nesses meses. Esse é o problema que o modelo resolve.

## 1. Os nove elementos

| Elemento | Definição |
| --- | --- |
| **Unidade** | Uma linha por **UF × classe de consumo × mês** (`gold_features_uf_mes`, PK `cod_ibge_uf, data_ref, classe`). O modelo é treinado no painel inteiro (27 UFs × 5 classes); a decisão usa o recorte Pará residencial. |
| **Label** | **Positivo = "surpresa de consumo"**: o consumo faturado do mês *t* cresce, sobre o mesmo mês do ano anterior, **pelo menos 3 p.p. acima da tendência** que a distribuidora conhecia no t0. Na prática é o mês em que quem comprou energia pela tendência fica subcontratado. O evento só é conhecido quando a EPE publica o consumo de *t*, cerca de um mês depois. |
| **Regra de rotulagem** | `surpresa = y_yoy_log_consumo_dia(t) − mediana(y_yoy_log_consumo_dia, t−13..t−2)` por UF × classe, casando por data; `rótulo = surpresa ≥ 0,03`. A tendência usa só os 12 meses **já publicados** no t0 (por isso termina em *t−2*). Código na seção 2. |
| **Coorte** | Linhas com rótulo definido e fora do período da COVID: **28.460 linhas**, de 2006-02 a 2025-12. Ficam de fora 3.400 linhas sem os 12 meses de histórico que a tendência exige (2004-01 a 2006-01, mais a cascata do único grão com consumo ≤ 0, AP/rural/2007-03) e **3.780 linhas de 2020-03 a 2022-06**. Esse corte cobre a COVID e os 12 meses de efeito-base depois dela, quando a variação anual compara com meses de pandemia e "explode" sem relação com o clima. |
| **Ponto de corte (t0)** | **Dia 10 do mês *t***. Nessa data já foram publicados o ONI até *t−2* (o ONI de um mês usa o mês seguinte, e a NOAA atualiza no começo do mês), a reanálise ERA5 até *t−1* (cerca de 5 dias de atraso) e o consumo da EPE até *t−2*. |
| **Janela de observação** | Tudo o que estava publicado no t0: calendário de *t*, clima até *t−1*, ONI e indicadores de ENSO até *t−2* e consumo até *t−12* (feature) e *t−2* (tendência do rótulo). A lista exata das features está na seção 3. |
| **Janela de predição** | O consumo faturado do mês *t*, observado quando a EPE o publica, depois do t0. |
| **Split** | **Temporal**, sem embaralhar. Treino de 2006-02 a 2016-12 (17.660 linhas, 29,6% positivos, 20 meses com El Niño confirmado); validação de 2017-01 a 2020-02 (5.130 linhas, 33,9%, 6 meses); teste de 2022-07 a 2025-12 (5.670 linhas, 29,8%, 8 meses). O período 2020-03 a 2022-06 fica fora da coorte. O limiar e os hiperparâmetros são escolhidos na validação, e o teste é usado uma única vez. Por que as mesmas UFs aparecem em treino e teste: [`anti-vazamentos.md`](anti-vazamentos.md), checklist item 3. |
| **Baseline** | **B0**: classificador constante, que prevê a prevalência do treino; o PR-AUC dele é igual à prevalência, cerca de 30%. **B1**: regra simples "alerta se o El Niño estava confirmado em *t−2*" (`el_nino_causal_lag2`). O modelo só tem valor se superar B0 **e** B1 na validação e no teste, tanto no painel quanto no recorte Norte/Pará residencial. |
| **Métrica** | **PR-AUC (average precision)** como métrica principal. Os positivos são cerca de 30% e o que interessa é a classe positiva; a acurácia premiaria quem nunca alerta (70%). No limiar de operação: **recall**, precisão e **custo esperado** (limiar em [`decisao.md`](decisao.md), seção 3). Sementes fixas em `42` (`random_state` do modelo e de qualquer amostragem). |

## 2. Regra de rotulagem em código

Testado sobre a gold. Reproduz as contagens acima (coorte de 28.460 linhas e 30,4% de positivos com
`X = 0,03`):

```python
import pandas as pd

COVID_EXT = (pd.Timestamp("2020-03-01"), pd.Timestamp("2022-06-01"))  # COVID + 12 meses de efeito-base


def rotular(feat, X=0.03):
    """Positivo = variação anual do consumo em t supera a tendência conhecida no t0 em >= X (log ≈ p.p./100).
    Tendência = mediana da variação anual dos 12 meses já publicados no t0 (t-13..t-2), por UF × classe, por data."""
    y = feat.pivot(index="data_ref", columns=["cod_ibge_uf", "classe"], values="y_yoy_log_consumo_dia").asfreq("MS")
    tend = y.shift(2).rolling(12, min_periods=12).median()
    tend = tend.stack(["cod_ibge_uf", "classe"], future_stack=True).rename("tendencia").reset_index()
    f = feat.merge(tend, on=["data_ref", "cod_ibge_uf", "classe"], how="left", validate="1:1")
    f["surpresa"] = f["y_yoy_log_consumo_dia"] - f["tendencia"]
    f["na_coorte"] = f["surpresa"].notna() & ~f["data_ref"].between(*COVID_EXT)
    f["rotulo"] = (f["surpresa"] >= X).where(f["na_coorte"])
    return f
```

`asfreq("MS")` força a grade mensal antes do `shift`, então a defasagem é por data e não por posição,
a mesma regra da gold.

**Por que 3 p.p.** É o tamanho do efeito do El Niño no residencial do Norte (+3,1 a +3,8 p.p.). Com
2 p.p., 36% dos meses seriam positivos, e boa parte disso é ruído do calendário de faturamento.

**O rótulo carrega o sinal do El Niño?** Taxa de positivos (X = 3 p.p.) com e sem El Niño confirmado
em *t−2*:

| Recorte | Com El Niño | Sem El Niño |
| --- | --- | --- |
| Painel inteiro | 34,2% | 29,7% |
| Norte residencial | **47,9%** (238 meses-UF) | 30,9% (1.239) |
| Pará residencial | **52,9%** (34 meses) | 28,2% (177) |
| Sul rural | 19,6% (102) | 35,6% (531) |

O sinal tem o sentido esperado: sobe no Norte e cai no Sul rural, onde o El Niño traz mais chuva e
reduz a irrigação. Os números do Pará são uma amostra pequena (34 meses).

## 3. Features permitidas no t0

`gold_features_uf_mes` marca como `feature` tudo o que não depende do consumo do próprio mês. A gold
serve tanto para *nowcast* (fim do mês) quanto para previsão. **Para o t0 deste problema (dia 10 do
mês *t*), só este subconjunto vale:**

| Usar | Não usar no t0 | Por quê |
| --- | --- | --- |
| `ano`, `mes`, `mes_sin`, `mes_cos`, `t`, `dias_no_mes`, `dias_uteis` | | calendário, conhecido com antecedência |
| `temp_media_c_lag1`, `temp_max_media_c_lag1`, `precip_total_mm_lag1`, `anom_*_lag1` | `temp_media_c`, `precip_total_mm`, `dias_chuva`, `dias_calor`, `anom_*` (sem lag) | o clima de *t* ainda não terminou; o de *t−1* sai na ERA5 em cerca de 5 dias |
| `oni_lag2` … `oni_lag6`, `el_nino_causal_lag2`, `la_nina_causal_lag2` | `oni_lag1`, `*_causal_lag1` | o ONI de *t−1* usa a temperatura do mar de *t*, publicada só em *t+1* |
| `ar_y_log_lag12` | `ar_y_log_lag1`, `pct_livre_lag1` | o consumo de *t−1* só sai na EPE cerca de um mês depois |
| `regiao`, `classe` (one-hot) | `flag_covid` | o período da COVID está fora da coorte, então a coluna seria constante |

Para ampliar: com `ar_y_log_lag2` e o clima `*_lag2` na gold, dá para antecipar o t0 ou prever *t+1*.
Hoje a gold não tem essas colunas.
