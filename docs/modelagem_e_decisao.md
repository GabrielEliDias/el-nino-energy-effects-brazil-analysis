# Base ML-Ready, anti-vazamento e decisão

Documento dos Requisitos 5 e 6 do enunciado (`docs/Projeto_Da_Ingestao_a_Decisao.md`), escrito
**antes de treinar qualquer modelo**. Todos os números saem da gold de 2026-10-09 (carga
`20261009T101740Z`) e podem ser reproduzidos com o código da seção 1.2.

> **Proposta a validar pelo grupo.** O decisor, a ação e o limiar abaixo são a opção mais bem
> sustentada pelos dados que temos. Se o grupo escolher outro decisor, as seções 1 e 3 mudam junto.

---

## 0. Por que este problema

A análise exploratória (dashboard, seção "região × classe") mostrou que o El Niño **quase não muda o
consumo nacional**, mas muda o consumo **regional, com sinais opostos**. O efeito mais robusto em
consumo residencial está no **Norte**, onde o El Niño traz 22,7 mm/mês a menos de chuva e +0,43 °C:

- Norte residencial: +2,6 p.p. na variação anual. O sinal é o mesmo nas defasagens de 1 a 6 meses,
  nas duas metades da série e ao tirar cada um dos 7 episódios de El Niño, um de cada vez.
- Pará residencial: até +5,0 p.p., 3 meses depois de o El Niño ser confirmado.

Uma distribuidora que compra energia com base na tendência recente do consumo fica **subcontratada**
nesses meses. Esse é o problema que o modelo resolve.

---

## 1. Base ML-Ready

### 1.1 Os nove elementos

| Elemento | Definição |
| --- | --- |
| **Unidade** | Uma linha por **UF × classe de consumo × mês** (`gold_features_uf_mes`, PK `cod_ibge_uf, data_ref, classe`). O modelo é treinado no painel inteiro (27 UFs × 5 classes); a decisão usa o recorte Pará residencial. |
| **Label** | **Positivo = "surpresa de consumo"**: o consumo faturado do mês *t* cresce, sobre o mesmo mês do ano anterior, **pelo menos 3 p.p. acima da tendência** que a distribuidora conhecia no t0. Na prática é o mês em que quem comprou energia pela tendência fica subcontratado. O evento só é conhecido quando a EPE publica o consumo de *t*, cerca de um mês depois. |
| **Regra de rotulagem** | `surpresa = y_yoy_log_consumo_dia(t) − mediana(y_yoy_log_consumo_dia, t−13..t−2)` por UF × classe, casando por data; `rótulo = surpresa ≥ 0,03`. A tendência usa só os 12 meses **já publicados** no t0 (por isso termina em *t−2*). Código em 1.2. |
| **Coorte** | Linhas com rótulo definido e fora do período da COVID: **28.460 linhas**, de 2006-02 a 2025-12. Ficam de fora 3.400 linhas sem os 12 meses de histórico que a tendência exige (2004-01 a 2006-01, mais a cascata do único grão com consumo ≤ 0, AP/rural/2007-03) e **3.780 linhas de 2020-03 a 2022-06**. Esse corte cobre a COVID e os 12 meses de efeito-base depois dela, quando a variação anual compara com meses de pandemia e "explode" sem relação com o clima. |
| **Ponto de corte (t0)** | **Dia 10 do mês *t***. Nessa data já foram publicados o ONI até *t−2* (o ONI de um mês usa o mês seguinte, e a NOAA atualiza no começo do mês), a reanálise ERA5 até *t−1* (cerca de 5 dias de atraso) e o consumo da EPE até *t−2*. |
| **Janela de observação** | Tudo o que estava publicado no t0: calendário de *t*, clima até *t−1*, ONI e indicadores de ENSO até *t−2* e consumo até *t−12* (feature) e *t−2* (tendência do rótulo). A lista exata das features está na seção 1.3. |
| **Janela de predição** | O consumo faturado do mês *t*, observado quando a EPE o publica, depois do t0. |
| **Split** | **Temporal**, sem embaralhar. Treino de 2006-02 a 2016-12 (17.660 linhas, 29,6% positivos, 20 meses com El Niño confirmado); validação de 2017-01 a 2020-02 (5.130 linhas, 33,9%, 6 meses); teste de 2022-07 a 2025-12 (5.670 linhas, 29,8%, 8 meses). O período 2020-03 a 2022-06 fica fora da coorte. O limiar e os hiperparâmetros são escolhidos na validação, e o teste é usado uma única vez. |
| **Baseline** | **B0**: classificador constante, que prevê a prevalência do treino; o PR-AUC dele é igual à prevalência, cerca de 30%. **B1**: regra simples "alerta se o El Niño estava confirmado em *t−2*" (`el_nino_causal_lag2`). O modelo só tem valor se superar B0 **e** B1 na validação e no teste, tanto no painel quanto no recorte Norte/Pará residencial. |
| **Métrica** | **PR-AUC (average precision)** como métrica principal. Os positivos são cerca de 30% e o que interessa é a classe positiva; a acurácia premiaria quem nunca alerta (70%). No limiar de operação: **recall**, precisão e **custo esperado** (seção 3.3). Sementes fixas em `42` (`random_state` do modelo e de qualquer amostragem). |

### 1.2 Regra de rotulagem em código

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

### 1.3 Features permitidas no t0

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

---

## 2. Checklist anti-vazamento

**1. Toda feature existia antes do t0?** Sim, para o subconjunto da seção 1.3, que respeita o atraso de
publicação de cada fonte. A gold prova a parte estrutural a cada execução com `testar_sem_vazamento`:
perturbar o mês *T* em toda a silver não muda nenhuma linha anterior a *T*. Uma auditoria externa
cortou a silver em 2015-06, 2019-12 e 2023-12, e nenhuma feature anterior ao corte mudou.

**Vazamento residual que admitimos:**
- **Revisão do ONI.** Os valores históricos do ONI são reprocessados quando muda a versão do ERSST
  (hoje v6). O modelo treina com o ONI revisado, que pode diferir um pouco do valor publicado na época.
- **Escolha do recorte.** O recorte da decisão (Pará e Norte residencial) e o próprio limiar de 3 p.p.
  foram escolhidos olhando a série inteira (2004–2025), teste incluído. A avaliação do teste nesse
  recorte é, portanto, **otimista**. Mitigações:
  - o modelo é treinado no painel inteiro, sem saber qual recorte será destacado;
  - o efeito sobreviveu a tirar cada episódio de El Niño;
  - o resultado do teste será reportado também no painel inteiro, que não foi escolhido a dedo.

**2. As agregações usam só dados anteriores ao t0 de cada observação?**
- A tendência do rótulo usa *t−13..t−2*.
- Os indicadores `*_causal` só olham o passado; há teste com dados sintéticos que corta o futuro e
  confere que o passado não muda.
- Exceção: as **normais climatológicas** e os **pesos regionais** usam o período-base fixo 2004–2014.
  Para linhas de treino desse período, a anomalia é calculada com uma normal que inclui anos
  posteriores à linha. Isso fica **inteiramente dentro do treino**: validação e teste (2017 em diante)
  só usam médias de anos anteriores a eles.

**3. O split respeita tempo e grupo? Alguma entidade aparece em treino e teste?** O split é temporal.
As mesmas UFs aparecem em treino e teste **de propósito**: a decisão é prever o futuro **das mesmas
distribuidoras**, e um split por UF responderia a outra pergunta (generalizar para um estado nunca
visto). O vazamento que importa entre entidades é o contemporâneo: o ONI de um mês é igual para
todas as UFs. O split temporal o elimina, porque cada mês inteiro, com todas as UFs, fica em um único
conjunto.

**4. Scalers, encoders e imputadores foram ajustados só no treino?** O one-hot de `regiao`/`classe` e
a padronização ficam dentro de um `sklearn.pipeline.Pipeline` com `ColumnTransformer`, ajustado com
`fit` apenas no treino. Não há imputação: os nulos das features são estruturais (primeiro mês e
primeiros 12 meses) e caem fora da coorte, que começa em 2006-02. O limiar é escolhido na validação e
congelado antes de olhar o teste.

> Itens 3 e 4 descrevem como o notebook de modelagem **deve** ser feito; serão verificados nele.

---

## 3. A decisão

### 3.1 A frase do enunciado

> *"Cruzando o consumo mensal da EPE, o ONI da NOAA e o clima do Open-Meteo, identificamos que, quando
> o El Niño é confirmado, o consumo residencial do Pará passa a crescer até 5 p.p. acima dos meses sem
> ENSO nos 3 meses seguintes (Norte: +3,1 a +3,8 p.p.), junto com 22,7 mm/mês a menos de chuva na
> região. Recomendamos que **a distribuidora do Pará (Equatorial Pará)** **revise para cima a previsão
> de carga residencial do mês e cubra o déficit nos instrumentos de ajuste de curto prazo** sempre que
> o alerta disparar, **a cada mês, enquanto durar um El Niño confirmado**, priorizando os meses de
> maior carga. Se agir, evita comprar de **16 a 24 GWh/mês** no mercado de curto prazo (3,3 a 5 p.p.
> sobre cerca de 479 GWh/mês residenciais em 2025); se errarmos, o custo é sobrecontratar esse volume,
> que fica dentro da margem de 105% repassável à tarifa."*

### 3.2 Decisor e ação

- **Quem:** a área de compra de energia e planejamento de mercado da distribuidora do Pará.
- **Ação:** no dia 10 de cada mês, se o modelo der alerta para o residencial do Pará, revisar para
  cima a previsão de carga do mês. A distribuidora então cobre o déficit previsto com os instrumentos
  de ajuste disponíveis e programa a operação para o pico: equipes, manutenção fora dos meses de alerta.
- **Por que essa ação existe:** a distribuidora precisa ter 100% do mercado coberto por contratos
  (Decreto nº 5.163/2004, art. 2º), e a falta de cobertura é penalizada (art. 3º). A energia não
  contratada é liquidada no mercado de curto prazo, ao PLD.

### 3.3 Custo de errar e limiar

| Erro | O que acontece | Custo |
| --- | --- | --- |
| **Falso negativo** (não alertou e o pico veio) | a distribuidora fica subcontratada no mês | compra o déficit ao PLD e se expõe a penalidade por falta de cobertura (art. 3º). Se a seca do El Niño também reduzir a geração hidrelétrica, o PLD pode estar mais alto justamente nesses meses (não medido aqui: o ONS ficou fora das fontes) |
| **Falso positivo** (alertou e o pico não veio) | a distribuidora contrata energia a mais | até **105% da carga** o custo é repassado à tarifa (art. 38): pesa no consumidor, não no caixa da distribuidora. Acima disso, vende a sobra ao PLD |

Para a distribuidora, o falso negativo custa bem mais que o falso positivo. **Premissa: o falso
negativo custa 3 vezes o falso positivo.** Pela regra de decisão de menor custo esperado, o modelo
alerta quando a probabilidade prevista for maior ou igual a

&nbsp;&nbsp;&nbsp;&nbsp;**p\* = c_FP / (c_FP + c_FN) = 1 / (1 + 3) = 0,25**

Ou seja, um alerta vale a pena com uma chance de pico de 25% ou mais, abaixo dos 50% "naturais". O
limiar prioriza **recall**. Esse p\* é o ponto de partida; o limiar final sai da validação, como o que
minimiza o custo esperado com essa razão de custos, e é congelado antes do teste.

A razão 3:1 é uma premissa. Calibrá-la exige o PLD e o preço dos contratos de ajuste (dados da CCEE),
que não estão nas nossas fontes. Na defesa, mostrar como o limiar muda com razões de 2:1 e 5:1
(p\* = 0,33 e 0,17).

### 3.4 Limitações

- **Amostra efetiva pequena.** São 7 episódios de El Niño na janela, e o teste tem só um (2023–24).
  Um bom resultado no teste é um indício, não uma prova.
- **Correlação, não causalidade.** O mecanismo é coerente: seca mais calor no Norte levam a mais
  refrigeração. Mas há fatores de confusão. A recessão de 2015–16 coincide com o El Niño mais forte, e
  as séries do Norte têm quebras estruturais, como a interligação de Manaus (2013) e do Amapá (2015) ao
  SIN e os programas de eletrificação.
- **Consumo faturado, não medido.** A EPE publica o consumo faturado, que atrasa cerca de 1 mês em
  relação ao consumo real. O rótulo herda esse ruído de calendário de faturamento.
- **Clima de uma capital por UF.** Belém representa todo o Pará, um estado do tamanho de países.
- **Valor em reais.** O ganho está em GWh. Convertê-lo em reais exige o PLD e os preços de contrato
  (CCEE), fora das nossas fontes.
- **O que seria preciso para afirmar mais:**
  - dados do ONS (reservatórios e carga medida, sem o atraso do faturamento);
  - o PLD da CCEE;
  - dados por município ou por estação meteorológica (INMET);
  - mais episódios de El Niño, isto é, esperar ou estender a série para antes de 2004, o que a EPE
    não oferece.
