# El ninõ e a sua influência nas contas referentes ao Brasil:

* **Pergunta Central:** Como a presença do fenômeno El Niño influencia o consumo de energia elétrica no Brasil?
* **Título:** *Impacto do Fenômeno El Niño na Demanda de Energia Elétrica no Brasil: Uma Abordagem Preditiva via Aprendizado de Máquina* 

Possíveis base para análise preditívas:

|psl.noaa.gov/data/timeseries/month/DS/ONI/| 
|epe.gov.br/pt/publicacoes-dados-abertos/dados-abertos/dados-do-consumo-mensal-de-energia-eletrica| 
|dadosabertos.aneel.gov.br/dataset/samp|
|servicodados.ibge.gov.br/api/docs/agregados| 
|ipeadata.gov.br/api| 
|dados.ons.org.br| 

Sobre as bases

O fenômeno El Niño eleva as temperaturas médias e altera a distribuição de chuvas no Brasil, gerando um pico imediato na demanda por refrigeração (elevando o consumo residencial e comercial) e reduzindo o nível dos reservatórios hidrelétricos, o que aciona usinas térmicas e encarece o custo da energia.

**Fontes de Dados para a Análise**

| Fonte | Base / API | Frequência | Aplicação Principal no Modelo |
| --- | --- | --- | --- |
| **NOAA** | Oceanic Niño Index (ONI) | Mensal | **Sinal Climático:** Mede anomalias na temperatura do Pacífico Equatorial (Região Niño 3.4) para categorizar eventos de El Niño, La Niña e Neutralidade. |
| **EPE** | Consumo Mensal de Energia | Mensal | **Target (Macro):** Consumo agregado de energia por classe (residencial, industrial, comercial, rural) e por subsistema elétrico. |
| **ANEEL** | Sistema SAMP | Anual/Mensal | **Target (Micro):** Dados granulares por distribuidora (mercado, faturamento, receita, consumo e quantidade de unidades consumidoras). |
| **ONS** | Portal de Dados Abertos | Horário a Mensal | **Operação e Custo:** Carga de energia, geração por fonte, nível dos reservatórios (EAR) e Custo Marginal de Operação (CMO). |
| **IBGE** | API de Agregados (SIDRA) | Variável (API) | **Controle Econômico:** Extração automatizada de indicadores de atividade econômica e inflação (IPCA, PIMC, PMC) regionalizados. |
| **IPEAdata** | API REST (OData) | Variável (API) | **Controle Macroeconômico:** Ingestão de séries de longo prazo (PIB, taxa de câmbio, juros, produção industrial). |

**Arquitetura do Fluxo de Dados**

* **Clima e Oferta Futura:** O índice ONI (NOAA) antecipa o regime climático → Afeta o volume de chuvas nas bacias hidrográficas → Impacta a vazão e o nível dos reservatórios monitorados pelo ONS.
* **Operação e Preço do Setor:** O ONS registra o equilíbrio entre oferta e demanda em tempo real, ditando o nível de acionamento térmico e o Custo Marginal de Operação (CMO).
* **Demanda de Mercado:** A EPE fornece a curva do consumo agregado por setor, enquanto a ANEEL (SAMP) detalha o comportamento do mercado distribuidor a distribuidor.
* **Covariáveis de Controle:** As APIs do IBGE e do IPEAdata isolam o impacto estritamente climático do consumo, controlando variáveis como crescimento do PIB, inflação e atividade industrial dentro dos algoritmos de Aprendizado de Máquina.
