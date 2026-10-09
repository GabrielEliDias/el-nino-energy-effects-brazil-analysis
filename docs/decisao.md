# A decisão

Requisito 6 do enunciado (`docs/Projeto_Da_Ingestao_a_Decisao.md`): quem decide, o que faz, quanto
custa errar e qual limiar usar. O rótulo, o t0 e a métrica do modelo que apoia esta decisão estão em
[`ml-ready.md`](ml-ready.md); a prova de que ele não usa o futuro, em [`anti-vazamentos.md`](anti-vazamentos.md).

> **Proposta a validar pelo grupo.** O decisor, a ação e o limiar abaixo são a opção mais bem
> sustentada pelos dados que temos. Se o grupo escolher outro decisor, `ml-ready.md` muda junto.

## 1. A frase do enunciado

> *"Cruzando o consumo mensal da EPE, o ONI da NOAA e o clima do Open-Meteo, identificamos que, quando
> o El Niño é confirmado, o consumo residencial do Pará passa a crescer até 5 p.p. acima dos meses sem
> ENSO nos 3 meses seguintes (Norte: +3,1 a +3,8 p.p.), junto com 22,7 mm/mês a menos de chuva na
> região. Recomendamos que **a distribuidora do Pará (Equatorial Pará)** **revise para cima a previsão
> de carga residencial do mês e cubra o déficit nos instrumentos de ajuste de curto prazo** sempre que
> o alerta disparar, **a cada mês, enquanto durar um El Niño confirmado**, priorizando os meses de
> maior carga. Se agir, evita comprar de **16 a 24 GWh/mês** no mercado de curto prazo (3,3 a 5 p.p.
> sobre cerca de 479 GWh/mês residenciais em 2025); se errarmos, o custo é sobrecontratar esse volume,
> que fica dentro da margem de 105% repassável à tarifa."*

De onde vêm os números:
- **Efeito no Pará e no Norte:** diferença entre os meses com El Niño confirmado (`el_nino_causal`) e
  os meses sem ENSO, com defasagem de 1 a 3 meses e sem os meses de COVID.
- **Chuva:** anomalia média do Norte em El Niño menos neutro, com defasagem de 1 a 6 meses.
- **Volume:** consumo residencial do Pará em 2025 (`gold_fato_consumo_uf_mes`).

## 2. Decisor e ação

- **Quem:** a área de compra de energia e planejamento de mercado da distribuidora do Pará.
- **Ação:** no dia 10 de cada mês (o t0 do modelo), se o modelo der alerta para o residencial do Pará,
  revisar para cima a previsão de carga do mês. A distribuidora então cobre o déficit previsto com os
  instrumentos de ajuste disponíveis e programa a operação para o pico: equipes, manutenção fora dos
  meses de alerta.
- **Por que essa ação existe:** a distribuidora precisa ter 100% do mercado coberto por contratos
  (Decreto nº 5.163/2004, art. 2º), e a falta de cobertura é penalizada (art. 3º). A energia não
  contratada é liquidada no mercado de curto prazo, ao PLD.

## 3. Custo de errar e limiar

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

**Ligação entre a métrica técnica e a consequência:** o PR-AUC mede o quão bem o modelo ordena os
meses de risco. No limiar p\*, cada falso negativo é um mês de exposição ao PLD, e cada falso positivo
é uma compra que vai para a tarifa. O custo esperado na validação (FN × 3 + FP × 1) é o número que
decide se o modelo vale mais que a regra simples "alerta com El Niño confirmado" (baseline B1).

## 4. Limitações

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
