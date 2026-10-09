# Anti-vazamento

Como garantimos e **provamos** que nenhuma informação do futuro, e nenhum pedaço do alvo, entra nas
features. Fecha o checklist do Requisito 5 do enunciado. Rótulo, t0 e features permitidas estão em
[`ml-ready.md`](ml-ready.md).

## 1. Os dois tipos de vazamento que importam aqui

- **Vazamento do futuro.** A feature da linha do mês *t* usa um dado de depois de *t*. Exemplos:
  - um `shift` por posição que, com um mês faltando, puxa o valor errado;
  - a `fase_enso`, que só é conhecida quando o episódio de 5 meses termina;
  - o ONI do mês *t* sem defasagem, porque ele é uma média de *t−1*, *t* e ***t+1***.
- **Vazamento do alvo.** A feature é o próprio consumo do mês, ou deriva dele: o consumo do mês, o
  número de consumidores do mês, a participação do mercado livre no mês.

Há um terceiro, mais sutil: **disponibilidade**. O dado é do passado, mas ainda não foi publicado no
t0. É o caso do consumo de *t−1* no dia 10 de *t*. Ele é tratado pela escolha de features em
[`ml-ready.md`](ml-ready.md), seção 3.

## 2. O que foi encontrado e corrigido

Uma auditoria da gold em 2026-10-09 encontrou vazamento do alvo em `gold_features_uf_mes`. A correção
está em `notebooks/gold.ipynb`:

| Coluna | Problema | Correção |
| --- | --- | --- |
| `consumo_mwh`, `consumo_mwh_por_dia` | o alvo do mês (`consumo_mwh_por_dia` é exatamente `exp(y_log_consumo_dia)`) | saíram da tabela de features; ficam só em `gold_fato_consumo_uf_mes` |
| `n_consumidores` | publicado junto com o consumo do mês | idem |
| `pct_livre` | parcela livre ÷ consumo do mês: deriva do alvo | trocada por `pct_livre_lag1` |
| `y_log_consumo_dia` × `y_yoy_log_consumo_dia` | um é função do outro; se um é alvo, o outro não pode ser feature | os dois marcados como `alvo` |
| (todas) | nada dizia o que era feature e o que era alvo | papéis explícitos: `COLS_CHAVE`, `COLS_ALVO` e o resto = `feature`, exportados na coluna `papel` do dicionário |

O que já estava certo e foi mantido:
- defasagens **por data** (`com_defasagem`);
- `fase_enso` e `intensidade_enso` fora das features;
- nenhum ONI com lag 0;
- indicadores de El Niño/La Niña causais (`*_causal`), que só olham o passado.

## 3. Como provamos

### 3.1 Testes que rodam a cada execução da gold

| Teste | O que prova | Como |
| --- | --- | --- |
| `testar_defasagem_por_data` | defasagem casa por data, não por posição | série sintética com um mês faltando: o lag desse mês tem de ser nulo, e UFs diferentes não se misturam |
| `testar_flags_causais` | `el_nino_causal` / `la_nina_causal` não usam o futuro | ONI sintético: cortar a série em vários pontos não pode mudar nenhum valor anterior ao corte |
| `testar_lags_nas_features` | os lags da tabela real estão certos | 300 linhas sorteadas (`random_state=1`), conferidas contra uma busca independente, linha a linha |
| **`testar_sem_vazamento`** | **nenhuma feature usa o futuro nem o consumo do próprio mês** | ver 3.2 |

### 3.2 `testar_sem_vazamento`: prova por perturbação

Em vez de listar colunas suspeitas, o teste **mexe nos dados e observa o que muda**. O mês testado é
*T*, 24 meses antes do fim da janela.

1. Copia a silver e altera o mês *T* em todas as fontes:
   - consumo **cativo** × 1,7 (só o cativo, para que a parcela livre também mude);
   - +1.000 consumidores;
   - +5 °C e +5 mm de chuva;
   - ONI + 1.
2. Reconstrói a gold inteira a partir da silver alterada (`montar_tabelas`).
3. Compara com a gold original e exige três coisas:
   - **antes de *T*:** nenhuma coluna de nenhuma linha muda. Se mudar, alguma feature olha o futuro;
   - **em *T*:** só podem mudar os alvos e o clima do próprio mês, que é exógeno. Se mudar outra
     coluna, alguma feature usa o consumo do mês;
   - **em *T+1*:** `ar_y_log_lag1`, `pct_livre_lag1`, `oni_lag1` e `temp_media_c_lag1` **têm de**
     mudar. Isso prova que a perturbação chegou aos dados; um teste que não perturba nada passaria
     sempre.

Resultado em 2026-10-09: as três checagens deram OK.

### 3.3 Auditoria externa (uma vez, fora do pipeline)

- **Corte do futuro.** A silver foi truncada em 2015-06, 2019-12 e 2023-12 e a gold reconstruída. Em
  nenhum dos três cortes alguma coluna das linhas até o corte mudou.
- **Correlação com o alvo.** Entre as features, só `ar_y_log_lag1` e `ar_y_log_lag12` têm
  |correlação| > 0,95 com `y_log_consumo_dia` (0,998 e 0,997). Isso **não é vazamento**: a
  perturbação prova que elas não usam o mês corrente. O consumo em nível é dominado pelo tamanho de
  cada UF e classe, então o consumo do mês anterior é quase igual ao do mês atual. Consequência
  prática: para medir o efeito do El Niño, use o alvo em variação (`y_yoy_*` ou o rótulo de
  `ml-ready.md`), ou compare modelos com e sem as `ar_*`.

## 4. Checklist do enunciado

**1. Toda feature existia antes do t0?** Sim, para o subconjunto de [`ml-ready.md`](ml-ready.md)
seção 3, que respeita o atraso de publicação de cada fonte. A parte estrutural é provada a cada
execução (seção 3.2) e foi auditada cortando o futuro (seção 3.3).

**2. As agregações usam só dados anteriores ao t0 de cada observação?**
- A tendência do rótulo usa *t−13..t−2*.
- Os indicadores `*_causal` só olham o passado; um teste sintético corta o futuro e confere que o
  passado não muda.
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

## 5. Vazamentos residuais que admitimos

- **Revisão do ONI.** Os valores históricos do ONI são reprocessados quando muda a versão do ERSST
  (hoje v6). O modelo treina com o ONI revisado, que pode diferir um pouco do valor publicado na época.
- **Escolha do recorte.** O recorte da decisão (Pará e Norte residencial) e o limiar de 3 p.p. foram
  escolhidos olhando a série inteira (2004–2025), teste incluído. A avaliação do teste nesse recorte é,
  portanto, **otimista**. Mitigações:
  - o modelo é treinado no painel inteiro, sem saber qual recorte será destacado;
  - o efeito sobreviveu a tirar cada episódio de El Niño;
  - o resultado do teste será reportado também no painel inteiro, que não foi escolhido a dedo.

## 6. Como adicionar uma feature sem vazar

1. **Defasagem por data:** use `com_defasagem` (nunca `shift` por posição).
2. **Declare a coluna** em `COLUNAS` (tipo e descrição), em `SCHEMAS["gold_features_uf_mes"]` e em
   `DOMINIO`; o dicionário recusa coluna sem domínio.
3. **Nada do consumo do mês *t*** nem derivado dele. Se precisar dele, entre com lag ≥ 1 e, para o t0
   do modelo, lag ≥ 2.
4. **Rode a gold:** `testar_sem_vazamento` tem de continuar OK. Se a nova coluna mudar em *T* sem ser
   alvo nem clima do mês, ela vaza.
5. **Disponibilidade no t0:** confira quando a fonte publica o dado e atualize a tabela de
   [`ml-ready.md`](ml-ready.md), seção 3.
