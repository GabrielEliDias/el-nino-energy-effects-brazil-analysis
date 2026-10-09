# Análise do dashboard

Cada seção `## nome` aparece no dashboard embaixo do gráfico de mesmo nome. Edite o texto à vontade
(markdown) e recarregue a página: não precisa mexer no código. Seção vazia some do dashboard.

Os números citados valem para o recorte padrão (todas as regiões e classes, sem COVID) e para a análise
de robustez feita sobre a gold de 2026-10-09; com outros filtros os gráficos mudam e o texto não.

Rascunho: o grupo deve revisar e reescrever com as próprias palavras. A decisão (Req. 6) entra na
`conclusao` quando estiver definida.

## resumo

**Resposta curta:** no Brasil como um todo, o El Niño quase não muda o consumo. O efeito existe, mas é
**regional e tem sinais opostos**: o consumo sobe no Norte e cai no Sul, e por isso se cancela na média
nacional. O caminho é o previsto na documentação: o El Niño mexe na chuva e na temperatura de cada
região, e o consumo responde com alguns meses de atraso.

## linha_do_tempo

As barras são o ONI: vermelho = El Niño, azul = La Niña. Na janela há **7 episódios de El Niño**, e o
de 2014-10 a 2016-04 é o mais forte da série.

Na linha de consumo, as quedas fortes têm causa econômica e não climática: **2009** (crise, −0,8% no ano),
**2015–16** (recessão, −2,0% e −0,9%) e **2020** (COVID, pior mês em 2020-05, −11,3%). O ponto
delicado é que a recessão de 2015–16 coincide com o El Niño mais forte. Por isso a análise remove um
episódio de cada vez para ver se o resultado depende dele (seção região × classe).

## clima

Este é o 1º elo da cadeia: ENSO → clima local. Compare a barra do El Niño com a do neutro em cada região.
Na média das defasagens de 1 a 6 meses, o El Niño deixa o país **0,4 °C mais quente** em todas as regiões,
e a chuva muda em direções opostas:

- **Norte:** 22,7 mm/mês **menos** chuva e +0,43 °C (seca mais calor).
- **Sul:** 12,8 mm/mês **mais** chuva.
- **Centro-Oeste:** 5,4 mm/mês menos chuva.

É o padrão clássico do El Niño no Brasil (Norte seco, Sul chuvoso), e explica os sinais opostos do consumo.

## consumo

Este é o 2º elo: ENSO → consumo. A tabela compara a variação anual média do consumo em cada fase com a
dos meses neutros. Com a defasagem padrão (2 meses), a diferença nacional fica perto de zero.

Mude a defasagem na barra lateral: o efeito nacional do El Niño vai de **−0,4 p.p. (1 mês)** a
**+1,2 p.p. (4–5 meses)**. Há um atraso: parte vem do faturamento da EPE, que chega cerca de 1 mês
depois do consumo real, e parte do tempo que a seca leva para pesar.

## regiao_classe

A tabela mostra **onde** o efeito está. Na média das defasagens de 1 a 6 meses, os efeitos que **se
mantêm** passaram por três testes: mesmo sinal nas 6 defasagens, nas duas metades da série (2004–14 e
2015–25) e ao tirar cada um dos 7 episódios de El Niño, um de cada vez:

| Recorte | El Niño − neutro | Mecanismo provável |
| --- | --- | --- |
| Norte, residencial | +2,6 p.p. | mais calor e seca → mais refrigeração |
| Norte, comercial | +1,8 p.p. | idem |
| Norte, todas as classes | +1,3 p.p. | idem |
| Centro-Oeste, rural | +4,1 p.p. | menos chuva → mais irrigação bombeada |
| Sul, rural | −3,3 p.p. | mais chuva → menos irrigação |

Não se mantêm: Brasil residencial (um único episódio inverte o sinal) e Nordeste comercial (cai para
+0,15 p.p. sem o episódio de 2009).

Usando só o que o decisor sabe no momento (El Niño **confirmado**, ONI ≥ 0,5 por 5 meses seguidos), o
residencial do **Norte** cresce de +3,1 a +3,8 p.p. a mais nos 1–3 meses seguintes, e o do **Pará**
chega a **+5,0 p.p.** em 3 meses.

## defasagem

A correlação entre o ONI e a variação anual do consumo, para cada defasagem. Com todas as regiões
juntas ela é fraca, porque os efeitos do Norte e do Sul se cancelam. Filtre só o Norte ou só a classe
rural do Sul para ver o sinal aparecer, com sentidos opostos.

## conclusao

- O El Niño influencia o consumo de energia no Brasil **por região e classe, não no agregado**. Mais
  consumo residencial e comercial no Norte e mais consumo rural no Centro-Oeste; menos consumo rural no Sul.
- O efeito chega com **1 a 5 meses de atraso**. Isso dá tempo de agir a partir do momento em que o
  El Niño é confirmado.
- **Limitações:** são 7 episódios de El Niño, então a amostra efetiva é pequena; trata-se de correlação
  com mecanismo coerente, não de prova causal; o elo reservatório → térmica → preço depende do ONS,
  que ficou fora das fontes; e as séries do Norte têm quebras estruturais, como a interligação de
  Manaus (2013) e do Amapá (2015) ao SIN.
