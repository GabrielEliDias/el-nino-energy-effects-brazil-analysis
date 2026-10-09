# Situação do projeto, pendências e roteiro da defesa

Situação em **2026-10-09**, conferida contra o enunciado
([`Projeto_Da_Ingestao_a_Decisao.md`](Projeto_Da_Ingestao_a_Decisao.md)). Atualize este arquivo
quando uma pendência fechar.

## 1. Situação por requisito

| Requisito | Situação | Onde está |
| --- | --- | --- |
| **1. Bases e cruzamento** | ✅ Três instituições (EPE, NOAA, Open-Meteo) e três formatos (XLSX, texto, JSON), com fonte por API e por arquivo. A chave está documentada, e os casamentos e órfãos são reportados (7.128 UF-meses, 0 órfãos). Licença, URL e data de coleta estão no dicionário. | [`dicionario_de_dados.md`](dicionario_de_dados.md), [`qualidade_dos_dados.md`](qualidade_dos_dados.md) §4 |
| **2. Ingestão** | ✅ Três formas: arquivo, API REST paginada com retry/backoff e carga incremental com checkpoint. Metadados técnicos em toda a bronze, quarentena com motivo e idempotência provada. | `notebooks/ingestao.ipynb`, [`qualidade_dos_dados.md`](qualidade_dos_dados.md) §1 e §5 |
| **3. Medalhão** | ✅ Granularidade em uma frase e PK verificada em código para as 16 tabelas. A gold não limpa nada. | [`dicionario_de_dados.md`](dicionario_de_dados.md) → Tabelas |
| **4. Repositório** | ⚠️ Prontos: `requirements.txt` com versões fixadas, README do zero, `data/` fora do Git, dicionário versionado. **Atenção: os commits até aqui estão em um único autor** (item 2.2). As sementes só valem quando houver modelo. | `README.md`, `requirements.txt` |
| **5. ML-Ready** | ⚠️ Os 9 elementos e o checklist anti-vazamento estão documentados, e a gold prova que não há vazamento. **Falta: o notebook de modelagem** (item 2.1); os itens 3 e 4 do checklist só fecham com ele. | [`ml-ready.md`](ml-ready.md), [`anti-vazamentos.md`](anti-vazamentos.md) |
| **6. Decisão** | ⚠️ Há uma proposta completa: decisor, ação, custos de FP/FN, limiar e limitações. **Falta: o grupo validar o decisor e a premissa de custo 3:1** (item 2.3). | [`decisao.md`](decisao.md) |
| **§9. Uso de IA** | ⚠️ A seção existe no README. **Falta: o grupo completar quem usou o quê** e garantir que todos sabem explicar o código (item 2.4). | `README.md` → Uso de IA |

## 2. Pendências, em ordem de prioridade

### 2.1 Notebook de modelagem (essencial)

O enunciado pede uma recomendação "sustentada por um modelo preditivo honesto". Hoje a decisão se
apoia na análise exploratória. O notebook segue [`ml-ready.md`](ml-ready.md)
sem mudar as definições de lá:

1. Ler `gold_features_uf_mes` e aplicar `rotular()` (código em `ml-ready.md`, seção 2).
2. Usar só as features de `ml-ready.md`, seção 3, as permitidas no t0.
3. Fazer o split temporal: treino 2006–2016, validação 2017 a 2020-02, teste 2022-07 a 2025.
4. Montar `Pipeline` + `ColumnTransformer` (one-hot de `regiao`/`classe` e padronização), com `fit`
   só no treino e `random_state=42`.
5. Treinar uma regressão logística (interpretável) e, se o grupo quiser, um
   `HistGradientBoostingClassifier`.
6. Comparar com os baselines B0 (prevalência) e B1 (`el_nino_causal_lag2`) na validação, pelo PR-AUC,
   no painel inteiro e no recorte Norte/Pará residencial.
7. Escolher o limiar na validação (custo esperado, razão FN:FP de 3:1, partindo de p\* = 0,25) e
   congelá-lo.
8. Avaliar o teste **uma única vez** e reportar o resultado mesmo que o modelo não supere B1. Um
   resultado honesto vale mais que um alto.

### 2.2 Autoria dos commits daqui em diante (essencial)

Os commits de 2026-10-09 (branch `feat/ml-ready-dashboard`) estão todos no mesmo autor e no mesmo dia,
e já entraram na `main` pelos PRs #1 e #2. O enunciado trata um histórico assim como trabalho de uma
pessoa só. Reescrever a `main` para trocar o autor não compensa: quebraria o histórico de quem já
puxou.

O que fazer:
- **Daqui em diante, cada integrante commita o que fizer**, com o próprio usuário do Git
  (`git config user.name` e `user.email`). Isso vale para o notebook de modelagem (2.1), a revisão do
  texto de `app/analise.md`, a declaração de IA (2.4) e a validação da decisão (2.3).
- **Na defesa, dizer como o trabalho foi dividido**, com honestidade, e cada um apresentar a parte que
  domina (2.4).

### 2.3 Validar a decisão (grupo)

- **Decisor e recorte:** a proposta é a distribuidora do Pará, residencial. A alternativa é a carga
  rural do Sul e do Centro-Oeste, ligada à irrigação.
- **Premissa de custo FN:FP = 3:1:** calibrá-la exige o PLD e o preço dos contratos de ajuste (CCEE),
  que estão fora das fontes. Na defesa, mostrar o limiar com 2:1 e 5:1.
- **Limiar do rótulo, 3 p.p.:** o tamanho do efeito do El Niño no Norte. Com 2 p.p., quase metade dos
  positivos seria ruído de faturamento.

### 2.4 Todos precisam saber explicar (essencial, §9)

Pontos que a banca tende a perguntar e que cada integrante deve saber explicar:

| Ponto | Onde |
| --- | --- |
| Por que a bronze guarda tudo como texto e o que é o `_hash_registro` | `ingestao.ipynb` → `gravar_bronze` |
| Como funciona o checkpoint do Open-Meteo | `ingestao.ipynb` → `paginas_completas` |
| Como a silver deduplica entre cargas | `silver.ipynb` → `deduplicar` |
| Por que as defasagens são por data e não por posição | `gold.ipynb` → `com_defasagem` |
| Por que `fase_enso` não pode ser feature e `el_nino_causal` pode | `gold.ipynb` §5, [`ml-ready.md`](ml-ready.md) §3 |
| Como `testar_sem_vazamento` prova que não há vazamento | [`anti-vazamentos.md`](anti-vazamentos.md) §3.2, `gold.ipynb` §8 |
| O que é o rótulo e por que a tendência termina em *t−2* | [`ml-ready.md`](ml-ready.md) §1–2 |
| Por que o limiar é 0,25 e não 0,5 | [`decisao.md`](decisao.md) §3 |

### 2.5 Decisões menores

- **Linha em quarentena com `Consumidores = -232`.** A silver descarta a linha inteira, inclusive o
  consumo válido. Quem cuida da silver decide se anula só o número de consumidores.
- **`src/` e `usabilidade.ipynb`.** O `src/01_extract.py` está desatualizado e não é usado, e
  `usabilidade.ipynb` lê uma pasta fora do repositório (`../Bases/`). Apagar ou explicar no README, para
  não confundir a banca.
- **Publicar os commits de documentação.** Os PRs #1 e #2 já foram integrados à `main`. Os commits de
  documentação feitos depois deles (dicionário gerado, qualidade, ML-Ready, anti-vazamento, decisão e
  este arquivo) sobem com `git push` na branch `feat/ml-ready-dashboard` e entram por um novo PR (#3).
  Depois, atualizar a `main` local com `git fetch origin main:main`. A `main` local estava 10 commits
  atrás, e foi por isso que um `git push origin main` foi rejeitado; nada foi perdido.
- **Enunciado no repositório.** `docs/Projeto_Da_Ingestao_a_Decisao.md` ainda não está no Git, e este
  arquivo aponta para ele. Se o grupo concordar em versionar o enunciado, commitar o arquivo; senão,
  trocar o link por uma menção ao nome do arquivo.

### 2.6 Rotina depois de rodar o pipeline

Depois de rodar a gold, regenerar o dicionário e commitar se ele mudar:

```bash
python scripts/gerar_dicionario.py
```

## 3. Roteiro da defesa

### 3.1 Demonstrar a idempotência (o enunciado exige a execução dupla)

Rode com o pipeline completo já executado uma vez:

```bash
cd notebooks
ls ../data/bronze/epe_consumo_uf/          # uma carga
jupyter nbconvert --to notebook --execute ingestao.ipynb --output-dir /tmp/nb_out
ls ../data/bronze/epe_consumo_uf/          # duas cargas lado a lado (nada sobrescrito)
jupyter nbconvert --to notebook --execute silver.ipynb --output-dir /tmp/nb_out
```

O que mostrar:
- A segunda ingestão leva cerca de 1 minuto e baixa **0 páginas** do Open-Meteo (célula do checkpoint).
- Na seção 10 da silver, os hashes da 1ª e da 2ª execução são iguais.
- A "prova extra" da mesma seção mostra conteúdo idêntico com duas cargas na bronze.

Se a EPE tiver publicado uma nova `DataVersao` desde a primeira carga, o conteúdo muda **de verdade**.
Explique que é atualização da fonte, não duplicação.

### 3.2 Demonstrar que não há vazamento

Abra a saída da gold e mostre as três linhas `anti-vazamento: …` com OK:
- perturbar o mês T não muda nenhuma linha anterior;
- em T só mudam os alvos e o clima do próprio mês;
- em T+1 os lags reagem, o que prova que o teste é sensível.

Depois, os dois vazamentos residuais que admitimos ([`anti-vazamentos.md`](anti-vazamentos.md)
§5). Apontá-los antes da banca mostra domínio do assunto.

### 3.3 Perguntas prováveis

| Pergunta | Resposta curta | Onde |
| --- | --- | --- |
| Por que não usaram ONS, INMET ou ANEEL? | Decisão do grupo; os acessos foram mapeados e documentados | [`dataset.md`](dataset.md) → Fontes avaliadas e não usadas |
| Quantos registros casaram, e os órfãos? | 7.128 UF-meses de cada lado e 0 órfãos; os órfãos iriam para `silver_orfaos_join` | [`dicionario_de_dados.md`](dicionario_de_dados.md) → Cruzamento |
| O El Niño muda o consumo do Brasil? | Quase nada no agregado; muda por região, com sinais opostos | dashboard; [`ml-ready.md`](ml-ready.md), "Por que este problema" |
| Por que o Pará? | Efeito residencial mais robusto, com mecanismo claro (seca e calor) | [`ml-ready.md`](ml-ready.md), "Por que este problema" e §2 |
| Por que o t0 é o dia 10? | É quando as três fontes já publicaram o que o modelo usa | [`ml-ready.md`](ml-ready.md) §1 |
| Por que PR-AUC e não acurácia? | Os positivos são cerca de 30%; a acurácia premia quem nunca alerta | [`ml-ready.md`](ml-ready.md) §1 |
| E a COVID? | Fica fora da coorte (2020-03 a 2022-06, incluindo o efeito-base) e é excluída das estatísticas do dashboard | idem |
| O que os dados não permitem afirmar? | Causalidade; valor em reais; generalizar além de 7 episódios | [`decisao.md`](decisao.md) §4 |

## 4. Fora do escopo (decidido)

- **Novas fontes** (ONS, INMET, ANEEL, PLD da CCEE): melhorariam as limitações, mas reabririam o pipeline
  perto da entrega. Ficam listadas como "o que seria preciso para afirmar mais".
- **Mais recursos no dashboard:** o que está lá responde à pergunta. Nesta fase o modelo vale mais que o
  acabamento.
