# Dicionário de dados

> **Gerado** por `scripts/gerar_dicionario.py` a partir de `data/silver/_relatorios/` e `data/gold/`. Não edite à mão: mude `COLUNAS`/`DOMINIO`/`FONTES` nos notebooks, rode o pipeline e gere de novo.

Janela de análise: **2004-01 a 2025-12**.

## Fontes

| fonte | url | licença | data de coleta |
| --- | --- | --- | --- |
| EPE — consumo mensal de energia elétrica | https://www.epe.gov.br/sites-pt/publicacoes-dados-abertos/dados-abertos/Documents/Dados_abertos_Consumo_Mensal.xlsx | CC BY 4.0 | 2026-10-09 |
| NOAA CPC/PSL — Oceanic Niño Index | https://psl.noaa.gov/data/correlation/oni.data | Domínio público (governo federal dos EUA) | 2026-10-09 |
| Open-Meteo Archive API (reanálise ERA5, Copernicus C3S) | https://archive-api.open-meteo.com/v1/archive | CC BY 4.0 (Open-Meteo); ERA5 sob a licença do Copernicus | 2026-10-09 |

## Tabelas

A chave primária de cada tabela é verificada em código a cada execução (sem nulos e sem duplicata).

| camada | tabela | granularidade | chave primária | linhas |
| --- | --- | --- | --- | --- |
| silver | `dim_uf` | uma linha por UF (27) | cod_ibge_uf | 27 |
| silver | `silver_energia_uf` | uma linha por UF × mês × subsistema × classe × tipo de consumidor (cativo/livre) | cod_ibge_uf, data_ref, subsistema, classe, tipo_consumidor | 59.238 |
| silver | `silver_energia_subsistema` | uma linha por região × mês × subsistema × classe × tipo de consumidor | data_ref, regiao, subsistema, classe, tipo_consumidor | 18.088 |
| silver | `silver_clima_uf_mes` | uma linha por UF × mês (clima diário da capital agregado no mês) | cod_ibge_uf, data_ref | 7.128 |
| silver | `silver_oni_mes` | uma linha por mês, série inteira do ONI (desde 1950) | data_ref | 920 |
| silver | `silver_energia_clima` | a mesma de silver_energia_uf, com o clima da UF-mês e o ONI do mês | cod_ibge_uf, data_ref, subsistema, classe, tipo_consumidor | 59.238 |
| silver | `silver_orfaos_join` | uma linha por lado × UF × mês que ficou sem par no cruzamento | lado, cod_ibge_uf, data_ref | 0 |
| silver | `silver_quarentena` | uma linha por registro rejeitado × regra violada (sem chave de negócio) | — | 1 |
| gold | `gold_dim_tempo` | uma linha por mês da janela | data_ref | 264 |
| gold | `gold_dim_enso` | uma linha por mês da série do ONI | data_ref | 920 |
| gold | `gold_dim_uf` | uma linha por UF (27) | cod_ibge_uf | 27 |
| gold | `gold_fato_consumo_uf_mes` | uma linha por UF × mês × classe (cativo + livre e todos os subsistemas somados) | cod_ibge_uf, data_ref, classe | 35.640 |
| gold | `gold_climatologia_uf` | uma linha por UF × mês do ano (normal do período-base) | cod_ibge_uf, mes | 324 |
| gold | `gold_clima_uf_mes` | uma linha por UF × mês | cod_ibge_uf, data_ref | 7.128 |
| gold | `gold_clima_agregado_mes` | uma linha por escopo (região ou Brasil) × mês | escopo, id_escopo, data_ref | 1.584 |
| gold | `gold_features_uf_mes` | uma linha por UF × mês × classe (base ML-Ready) | cod_ibge_uf, data_ref, classe | 35.640 |

## Cruzamento (Requisito 1)

Chave: **`cod_ibge_uf` + `data_ref` (ano/mês)** entre energia (EPE) e clima (Open-Meteo); **`data_ref`** com o ONI.
O join é `left` a partir da energia, com `validate="m:1"`: nenhuma linha de consumo é descartada pelo cruzamento.
Órfãos ficam em `silver_orfaos_join`, e a linha de energia continua com `flag_sem_clima` / `flag_sem_oni`.

| medida | valor |
| --- | --- |
| UF-meses com consumo | 7.128 |
| UF-meses com clima | 7.128 |
| UF-meses de energia sem clima (órfãos) | 0 |
| UF-meses de clima sem energia (órfãos) | 0 |
| linhas de energia sem ONI | 0 |
| linhas antes → depois do join | 59.238 → 59.238 |
| consumo total preservado | 9.924.027.411 MWh |

## Descartes e quarentena (nada some sem rastro)

Cada linha da bronze que não chega à silver é contada aqui. As regras estão em `docs/qualidade_dos_dados.md`.
A bronze acumula todas as cargas, então a mesma linha da origem aparece uma vez por carga: "versões antigas"
é a cópia das cargas anteriores (a mais recente vence), e a quarentena por regra conta a mesma falha em cada
carga. A tabela `silver_quarentena` guarda cada falha uma vez só.

| tabela | linhas na bronze (todas as cargas) | fora da janela | versões antigas (outras cargas) | duplicatas exatas | quarentena (por regra) | conflitos → quarentena | linhas na silver |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `silver_energia_uf` | 122.436 | 3.958 | 59.238 | 0 | consumidores_invalido: 2 | 0 | 59.238 |
| `silver_energia_subsistema` | 37.456 | 1.280 | 18.088 | 0 | 0 | 0 | 18.088 |
| `silver_clima_uf_mes` | 216.972 | 0 | 0 | 0 | 0 | 0 | 7.128 |
| `silver_oni_mes` | 154 | — | 77 | 0 | 0 | 0 | 920 |

Clima e ONI mudam de grão na silver, sem descarte: dias viram UF-meses (agregação) e o ONI passa de uma linha por ano (12 colunas) para uma por mês.

ONI: 4 meses com o sentinela `-99.9` (meses ainda não ocorridos, valor lido do rodapé da fonte) ficam fora; 0 valores inválidos.

Total final em `silver_quarentena`: 1 registro(s) — `silver_energia_uf/consumidores_invalido`: 1.

## Colunas

`papel` (só em `gold_features_uf_mes`): `chave`, `alvo` ou `feature`. Quais features valem no t0 do modelo está em `docs/ml-ready.md`, seção 3.

### `dim_uf` (silver)

Granularidade: uma linha por UF (27). Fonte: referência fixa no código (códigos de UF do IBGE).

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| cod_ibge_uf | string | PK | 27 códigos IBGE de UF (dim_uf) | Código IBGE da UF (2 dígitos, texto); chave de junção |
| uf | string |  | 27 siglas (dim_uf) | Sigla da UF |
| nome_uf | string |  | 27 nomes (dim_uf) | Nome da UF |
| regiao | string |  | norte, nordeste, centro_oeste, sudeste, sul | Região geográfica: norte, nordeste, centro_oeste, sudeste, sul |
| capital_proxy_clima | string |  | 27 capitais (dim_uf) | Capital cujo clima representa a UF |

### `silver_energia_uf` (silver)

Granularidade: uma linha por UF × mês × subsistema × classe × tipo de consumidor (cativo/livre). Fonte: EPE — consumo mensal de energia elétrica.

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| cod_ibge_uf | string | PK | 27 códigos IBGE de UF (dim_uf) | Código IBGE da UF (2 dígitos, texto); chave de junção |
| uf | string |  | 27 siglas (dim_uf) | Sigla da UF |
| data_ref | datetime64[ns] | PK | dia 1 de cada mês; 2004-01 a 2025-12 (ONI: série inteira, desde 1950) | Mês de referência (sempre dia 1); chave de junção |
| ano | Int16 |  | ano de data_ref | Ano de data_ref |
| mes | Int8 |  | 1 a 12 | Mês de data_ref (1-12) |
| regiao | string |  | norte, nordeste, centro_oeste, sudeste, sul | Região geográfica: norte, nordeste, centro_oeste, sudeste, sul |
| subsistema | string | PK | ISOLADO, N, NE, S, SE_CO | Subsistema elétrico: N, NE, SE_CO, S ou ISOLADO |
| em_sin | boolean |  | True, False | True se pertence ao SIN; False = sistemas isolados |
| classe | string | PK | residencial, comercial, industrial, rural, outros | Classe de consumo: residencial, comercial, industrial, rural, outros |
| tipo_consumidor | string | PK | cativo, livre | cativo ou livre |
| consumo_mwh | float64 |  | real; negativo = estorno | Consumo faturado no mês, na unidade da EPE (MWh; confirmar no dicionário da EPE). Negativo = estorno |
| n_consumidores | Int64 |  | inteiro >= 0 | Número de consumidores |
| flag_estorno | boolean |  | True, False | True quando consumo_mwh < 0 (estorno do mercado livre, mantido como publicado) |
| data_versao_epe | datetime64[ns] |  | data | Data da versão publicada pela EPE |
| _id_carga | string |  | AAAAmmddTHHMMSSZ (UTC) | Carga da bronze que originou o registro (a mais recente da chave) |
| _hash_registro | string |  | sha256 (64 hex) | Hash do registro bruto na bronze |

### `silver_energia_subsistema` (silver)

Granularidade: uma linha por região × mês × subsistema × classe × tipo de consumidor. Fonte: EPE — consumo mensal de energia elétrica.

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| data_ref | datetime64[ns] | PK | dia 1 de cada mês; 2004-01 a 2025-12 (ONI: série inteira, desde 1950) | Mês de referência (sempre dia 1); chave de junção |
| ano | Int16 |  | ano de data_ref | Ano de data_ref |
| mes | Int8 |  | 1 a 12 | Mês de data_ref (1-12) |
| regiao | string | PK | norte, nordeste, centro_oeste, sudeste, sul | Região geográfica: norte, nordeste, centro_oeste, sudeste, sul |
| subsistema | string | PK | ISOLADO, N, NE, S, SE_CO | Subsistema elétrico: N, NE, SE_CO, S ou ISOLADO |
| em_sin | boolean |  | True, False | True se pertence ao SIN; False = sistemas isolados |
| classe | string | PK | residencial, comercial, industrial, rural, outros | Classe de consumo: residencial, comercial, industrial, rural, outros |
| tipo_consumidor | string | PK | cativo, livre | cativo ou livre |
| consumo_mwh | float64 |  | real; negativo = estorno | Consumo faturado no mês, na unidade da EPE (MWh; confirmar no dicionário da EPE). Negativo = estorno |
| n_consumidores | Int64 |  | inteiro >= 0 | Número de consumidores |
| flag_estorno | boolean |  | True, False | True quando consumo_mwh < 0 (estorno do mercado livre, mantido como publicado) |
| data_versao_epe | datetime64[ns] |  | data | Data da versão publicada pela EPE |
| _id_carga | string |  | AAAAmmddTHHMMSSZ (UTC) | Carga da bronze que originou o registro (a mais recente da chave) |
| _hash_registro | string |  | sha256 (64 hex) | Hash do registro bruto na bronze |

### `silver_clima_uf_mes` (silver)

Granularidade: uma linha por UF × mês (clima diário da capital agregado no mês). Fonte: Open-Meteo Archive API (reanálise ERA5, Copernicus C3S).

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| cod_ibge_uf | string | PK | 27 códigos IBGE de UF (dim_uf) | Código IBGE da UF (2 dígitos, texto); chave de junção |
| uf | string |  | 27 siglas (dim_uf) | Sigla da UF |
| data_ref | datetime64[ns] | PK | dia 1 de cada mês; 2004-01 a 2025-12 (ONI: série inteira, desde 1950) | Mês de referência (sempre dia 1); chave de junção |
| ano | Int16 |  | ano de data_ref | Ano de data_ref |
| mes | Int8 |  | 1 a 12 | Mês de data_ref (1-12) |
| temp_media_c | float64 |  | média de dias em [-30.0, 50.0] °C | Média mensal da temperatura média diária (°C) |
| temp_max_media_c | float64 |  | média de dias em [-30.0, 55.0] °C | Média mensal da temperatura máxima diária (°C) |
| temp_max_abs_c | float64 |  | [-30.0, 55.0] °C | Maior temperatura máxima do mês (°C) |
| precip_total_mm | float64 |  | >= 0 (cada dia em [0.0, 1000.0] mm) | Precipitação total do mês (mm) |
| dias_chuva | Int16 |  | 0 a 31 | Dias com precipitação >= LIMIAR_CHUVA_MM |
| dias_calor | Int16 |  | 0 a 31 | Dias com temperatura máxima >= LIMIAR_CALOR_C |
| dias_com_dado | Int16 |  | 1 a 31 | Dias válidos no mês |
| dias_no_mes | Int8 |  | 28 a 31 | Dias do mês no calendário |
| cobertura_completa | boolean |  | True, False | True se todos os dias do mês têm dado válido |
| lat_grade | float64 |  | -90 a 90 | Latitude da célula de grade ERA5 usada pela API |
| lon_grade | float64 |  | -180 a 180 | Longitude da célula de grade ERA5 usada pela API |
| _id_carga | string |  | AAAAmmddTHHMMSSZ (UTC) | Carga da bronze que originou o registro (a mais recente da chave) |

### `silver_oni_mes` (silver)

Granularidade: uma linha por mês, série inteira do ONI (desde 1950). Fonte: NOAA CPC/PSL — Oceanic Niño Index.

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| data_ref | datetime64[ns] | PK | dia 1 de cada mês; 2004-01 a 2025-12 (ONI: série inteira, desde 1950) | Mês de referência (sempre dia 1); chave de junção |
| ano | Int16 |  | ano de data_ref | Ano de data_ref |
| mes | Int8 |  | 1 a 12 | Mês de data_ref (1-12) |
| oni | float64 |  | [-5.0, 5.0] °C (anomalia) | Oceanic Niño Index (média móvel centrada de 3 meses). Em modelos, usar defasagem >= 1 mês |
| fase_enso | string |  | el_nino, la_nina, neutro | el_nino, la_nina ou neutro (episódio: \|ONI\| >= 0,5 por 5 meses seguidos, critério NOAA) |
| intensidade_enso | string |  | fraca, moderada, forte, muito_forte ou nulo (neutro) | fraca, moderada, forte ou muito_forte (nulo se neutro) |
| _id_carga | string |  | AAAAmmddTHHMMSSZ (UTC) | Carga da bronze que originou o registro (a mais recente da chave) |

### `silver_energia_clima` (silver)

Granularidade: a mesma de silver_energia_uf, com o clima da UF-mês e o ONI do mês. Fonte: EPE — consumo mensal de energia elétrica; Open-Meteo Archive API (reanálise ERA5, Copernicus C3S); NOAA CPC/PSL — Oceanic Niño Index.

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| cod_ibge_uf | string | PK | 27 códigos IBGE de UF (dim_uf) | Código IBGE da UF (2 dígitos, texto); chave de junção |
| uf | string |  | 27 siglas (dim_uf) | Sigla da UF |
| data_ref | datetime64[ns] | PK | dia 1 de cada mês; 2004-01 a 2025-12 (ONI: série inteira, desde 1950) | Mês de referência (sempre dia 1); chave de junção |
| ano | Int16 |  | ano de data_ref | Ano de data_ref |
| mes | Int8 |  | 1 a 12 | Mês de data_ref (1-12) |
| regiao | string |  | norte, nordeste, centro_oeste, sudeste, sul | Região geográfica: norte, nordeste, centro_oeste, sudeste, sul |
| subsistema | string | PK | ISOLADO, N, NE, S, SE_CO | Subsistema elétrico: N, NE, SE_CO, S ou ISOLADO |
| em_sin | boolean |  | True, False | True se pertence ao SIN; False = sistemas isolados |
| classe | string | PK | residencial, comercial, industrial, rural, outros | Classe de consumo: residencial, comercial, industrial, rural, outros |
| tipo_consumidor | string | PK | cativo, livre | cativo ou livre |
| consumo_mwh | float64 |  | real; negativo = estorno | Consumo faturado no mês, na unidade da EPE (MWh; confirmar no dicionário da EPE). Negativo = estorno |
| n_consumidores | Int64 |  | inteiro >= 0 | Número de consumidores |
| flag_estorno | boolean |  | True, False | True quando consumo_mwh < 0 (estorno do mercado livre, mantido como publicado) |
| data_versao_epe | datetime64[ns] |  | data | Data da versão publicada pela EPE |
| _id_carga | string |  | AAAAmmddTHHMMSSZ (UTC) | Carga da bronze que originou o registro (a mais recente da chave) |
| _hash_registro | string |  | sha256 (64 hex) | Hash do registro bruto na bronze |
| temp_media_c | float64 |  | média de dias em [-30.0, 50.0] °C | Média mensal da temperatura média diária (°C) |
| temp_max_media_c | float64 |  | média de dias em [-30.0, 55.0] °C | Média mensal da temperatura máxima diária (°C) |
| temp_max_abs_c | float64 |  | [-30.0, 55.0] °C | Maior temperatura máxima do mês (°C) |
| precip_total_mm | float64 |  | >= 0 (cada dia em [0.0, 1000.0] mm) | Precipitação total do mês (mm) |
| dias_chuva | Int16 |  | 0 a 31 | Dias com precipitação >= LIMIAR_CHUVA_MM |
| dias_calor | Int16 |  | 0 a 31 | Dias com temperatura máxima >= LIMIAR_CALOR_C |
| clima_cobertura_completa | boolean |  | True, False ou nulo (sem clima) | cobertura_completa do clima do mês (nulo se sem clima) |
| oni | float64 |  | [-5.0, 5.0] °C (anomalia) | Oceanic Niño Index (média móvel centrada de 3 meses). Em modelos, usar defasagem >= 1 mês |
| fase_enso | string |  | el_nino, la_nina, neutro | el_nino, la_nina ou neutro (episódio: \|ONI\| >= 0,5 por 5 meses seguidos, critério NOAA) |
| intensidade_enso | string |  | fraca, moderada, forte, muito_forte ou nulo (neutro) | fraca, moderada, forte ou muito_forte (nulo se neutro) |
| flag_sem_clima | boolean |  | True, False | True se a UF-mês não tem clima (órfão do join) |
| flag_sem_oni | boolean |  | True, False | True se o mês não tem ONI (órfão do join) |
| _id_carga_clima | string |  | AAAAmmddTHHMMSSZ (UTC) | Carga da bronze do clima usada no join |
| _id_carga_oni | string |  | AAAAmmddTHHMMSSZ (UTC) | Carga da bronze do ONI usada no join |

### `silver_orfaos_join` (silver)

Granularidade: uma linha por lado × UF × mês que ficou sem par no cruzamento. Fonte: EPE — consumo mensal de energia elétrica; Open-Meteo Archive API (reanálise ERA5, Copernicus C3S).

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| lado | string | PK | energia_sem_clima, clima_sem_energia | Lado órfão: energia_sem_clima ou clima_sem_energia |
| cod_ibge_uf | string | PK | 27 códigos IBGE de UF (dim_uf) | Código IBGE da UF (2 dígitos, texto); chave de junção |
| uf | string |  | 27 siglas (dim_uf) | Sigla da UF |
| data_ref | datetime64[ns] | PK | dia 1 de cada mês; 2004-01 a 2025-12 (ONI: série inteira, desde 1950) | Mês de referência (sempre dia 1); chave de junção |
| motivo | string |  | texto | Motivo do órfão |

### `silver_quarentena` (silver)

Granularidade: uma linha por registro rejeitado × regra violada (sem chave de negócio). Fonte: EPE — consumo mensal de energia elétrica; Open-Meteo Archive API (reanálise ERA5, Copernicus C3S); NOAA CPC/PSL — Oceanic Niño Index.

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| tabela | string |  | nome de tabela silver | Tabela silver de origem do registro rejeitado |
| regra | string |  | nome de regra de negócio desta silver | Regra de negócio violada |
| valor_original | string |  | texto (valor ou chave rejeitada) | Valor original (ou chave) que violou a regra |
| _id_carga | string |  | AAAAmmddTHHMMSSZ (UTC) | Carga da bronze que originou o registro (a mais recente da chave) |
| _hash_registro | string |  | sha256 (64 hex) | Hash do registro bruto na bronze |

### `gold_dim_tempo` (gold)

Granularidade: uma linha por mês da janela. Fonte: gerada no código (calendário e feriados nacionais).

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| data_ref | datetime64[ns] | PK | dia 1 de cada mês da janela da silver (gold_dim_enso: série inteira do ONI) | Mês de referência (sempre dia 1) |
| ano | Int16 |  | ano de data_ref | Ano de data_ref |
| mes | Int8 |  | 1 a 12 | Mês (1-12) de data_ref |
| trimestre | Int8 |  | 1 a 4 | Trimestre civil |
| dias_no_mes | Int8 |  | 28 a 31 | Dias corridos do mês |
| dias_uteis | Int8 |  | 0 a 23 | Dias úteis: seg-sex menos feriados nacionais (sem feriados estaduais/municipais, Carnaval, Corpus Christi) |
| mes_sin | float64 |  | -1 a 1 | sen(2π·mes/12): sazonalidade contínua |
| mes_cos | float64 |  | -1 a 1 | cos(2π·mes/12): sazonalidade contínua |
| t | Int16 |  | inteiro >= 0 | Tendência: meses desde o início da janela (0 = primeiro mês) |
| flag_covid | boolean |  | True, False | Mês dentro do recorte COVID (COVID_INI..COVID_FIM) |

### `gold_dim_enso` (gold)

Granularidade: uma linha por mês da série do ONI. Fonte: NOAA CPC/PSL — Oceanic Niño Index.

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| data_ref | datetime64[ns] | PK | dia 1 de cada mês da janela da silver (gold_dim_enso: série inteira do ONI) | Mês de referência (sempre dia 1) |
| oni | float64 |  | -5 a 5 °C (anomalia) | Oceanic Niño Index (média móvel centrada de 3 meses: usa o mês seguinte) |
| fase_enso | string |  | el_nino, la_nina, neutro | RETROSPECTIVA (usa meses futuros): el_nino/la_nina/neutro. Não usar como feature |
| intensidade_enso | string |  | fraca, moderada, forte, muito_forte ou nulo (neutro) | RETROSPECTIVA: intensidade do episódio. Não usar como feature |
| episodio_id | Int16 |  | inteiro >= 1 ou nulo (neutro) | RETROSPECTIVO: sequência do episódio El Niño/La Niña (nulo no neutro) |
| mes_no_episodio | Int16 |  | inteiro >= 1 ou nulo (neutro) | RETROSPECTIVO: mês dentro do episódio (1..n) |
| meses_consec_quente | Int16 |  | inteiro >= 0 | Meses seguidos até t com ONI >= 0.5 (só passado) |
| meses_consec_frio | Int16 |  | inteiro >= 0 | Meses seguidos até t com ONI <= -0.5 (só passado) |
| el_nino_causal | boolean |  | True, False | meses_consec_quente >= 5: El Niño já confirmado em t (só passado) |
| la_nina_causal | boolean |  | True, False | meses_consec_frio >= 5: La Niña já confirmada em t (só passado) |

### `gold_dim_uf` (gold)

Granularidade: uma linha por UF (27). Fonte: EPE — consumo mensal de energia elétrica.

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| cod_ibge_uf | string | PK | 27 códigos IBGE de UF | Código IBGE da UF (2 dígitos, texto) |
| uf | string |  | 27 siglas | Sigla da UF |
| nome_uf | string |  | 27 nomes | Nome da UF |
| regiao | string |  | norte, nordeste, centro_oeste, sudeste, sul | Região geográfica: norte, nordeste, centro_oeste, sudeste, sul |
| capital_proxy_clima | string |  | 27 capitais | Capital cujo clima representa a UF |
| subsistema_predominante | string |  | N, NE, SE_CO, S, ISOLADO | Subsistema com maior consumo da UF no período-base |
| n_subsistemas | Int8 |  | 1 a 5 | Subsistemas distintos em que a UF aparece (>1: ex. SIN + isolado) |
| consumo_base_mwh | float64 |  | real > 0 | Consumo total da UF no período-base |
| peso_br | float64 |  | 0 a 1; soma 1 | Participação fixa da UF no consumo do Brasil (período-base); soma 1 |
| peso_regiao | float64 |  | 0 a 1; soma 1 por região | Participação fixa da UF no consumo da região (período-base); soma 1 por região |

### `gold_fato_consumo_uf_mes` (gold)

Granularidade: uma linha por UF × mês × classe (cativo + livre e todos os subsistemas somados). Fonte: EPE — consumo mensal de energia elétrica.

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| cod_ibge_uf | string | PK | 27 códigos IBGE de UF | Código IBGE da UF (2 dígitos, texto) |
| uf | string |  | 27 siglas | Sigla da UF |
| regiao | string |  | norte, nordeste, centro_oeste, sudeste, sul | Região geográfica: norte, nordeste, centro_oeste, sudeste, sul |
| data_ref | datetime64[ns] | PK | dia 1 de cada mês da janela da silver (gold_dim_enso: série inteira do ONI) | Mês de referência (sempre dia 1) |
| ano | Int16 |  | ano de data_ref | Ano de data_ref |
| mes | Int8 |  | 1 a 12 | Mês (1-12) de data_ref |
| classe | string | PK | residencial, comercial, industrial, rural, outros | Classe de consumo (EPE) |
| consumo_mwh | float64 |  | real (estornos podem deixar <= 0) | Consumo faturado, cativo + livre, todos os subsistemas da UF (unidade a confirmar na EPE; MWh) |
| consumo_mwh_cativo | float64 |  | real | Parcela cativa |
| consumo_mwh_livre | float64 |  | real | Parcela livre (pode ter estornos negativos) |
| n_consumidores | Int64 |  | inteiro >= 0 | Consumidores (cativo + livre) |
| consumo_mwh_por_dia | float64 |  | real | consumo_mwh / dias_no_mes (neutraliza o tamanho do mês) |
| consumo_mwh_por_consumidor | float64 |  | real ou nulo (sem consumidores) | consumo_mwh / n_consumidores |
| pct_livre | float64 |  | real ou nulo (consumo <= 0); normalmente 0 a 1, sai disso por estornos | Parcela livre / consumo total (nulo se consumo <= 0; pode sair de [0,1] por estornos) |
| tem_estorno | boolean |  | True, False | Alguma linha da silver neste grão tem consumo negativo |
| flag_consumo_nao_positivo | boolean |  | True, False | consumo_mwh <= 0 após a soma (alvo em log fica nulo) |

### `gold_climatologia_uf` (gold)

Granularidade: uma linha por UF × mês do ano (normal do período-base). Fonte: Open-Meteo Archive API (reanálise ERA5, Copernicus C3S).

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| cod_ibge_uf | string | PK | 27 códigos IBGE de UF | Código IBGE da UF (2 dígitos, texto) |
| uf | string |  | 27 siglas | Sigla da UF |
| mes | Int8 | PK | 1 a 12 | Mês (1-12) de data_ref |
| clim_temp_media_c | float64 |  | -30 a 50 °C | Normal (média no período-base) da temperatura média, por UF e mês do ano |
| clim_temp_max_media_c | float64 |  | -30 a 55 °C | Normal da média das máximas |
| clim_precip_total_mm | float64 |  | real >= 0 | Normal da precipitação total |
| clim_dias_calor | float64 |  | 0 a 31 | Normal de dias_calor |
| n_anos_base | Int8 |  | 1 a 11 | Anos do período-base usados na normal |

### `gold_clima_uf_mes` (gold)

Granularidade: uma linha por UF × mês. Fonte: Open-Meteo Archive API (reanálise ERA5, Copernicus C3S).

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| cod_ibge_uf | string | PK | 27 códigos IBGE de UF | Código IBGE da UF (2 dígitos, texto) |
| uf | string |  | 27 siglas | Sigla da UF |
| data_ref | datetime64[ns] | PK | dia 1 de cada mês da janela da silver (gold_dim_enso: série inteira do ONI) | Mês de referência (sempre dia 1) |
| ano | Int16 |  | ano de data_ref | Ano de data_ref |
| mes | Int8 |  | 1 a 12 | Mês (1-12) de data_ref |
| temp_media_c | float64 |  | -30 a 50 °C | Temperatura média do mês (°C) |
| temp_max_media_c | float64 |  | -30 a 55 °C | Média das máximas diárias (°C) |
| temp_max_abs_c | float64 |  | -30 a 55 °C | Máxima absoluta do mês (°C) |
| precip_total_mm | float64 |  | real >= 0 | Precipitação total do mês (mm) |
| dias_chuva | Int16 |  | 0 a 31 | Dias com chuva (limiar da silver) |
| dias_calor | Int16 |  | 0 a 31 | Dias com Tmax acima do limiar da silver (35 °C): pode ser quase sempre 0 |
| anom_temp_media_c | float64 |  | real | temp_media_c - normal (°C) |
| anom_temp_max_media_c | float64 |  | real | temp_max_media_c - normal (°C) |
| anom_precip_mm | float64 |  | real | precip_total_mm - normal (mm) |
| anom_dias_calor | float64 |  | real | dias_calor - normal |

### `gold_clima_agregado_mes` (gold)

Granularidade: uma linha por escopo (região ou Brasil) × mês. Fonte: Open-Meteo Archive API (reanálise ERA5, Copernicus C3S); EPE — consumo mensal de energia elétrica.

| coluna | tipo | chave | domínio | descrição |
| --- | --- | --- | --- | --- |
| escopo | string | PK | regiao, brasil | Nível de agregação: regiao ou brasil |
| id_escopo | string | PK | uma das 5 regiões ou brasil | Região ou 'brasil' |
| data_ref | datetime64[ns] | PK | dia 1 de cada mês da janela da silver (gold_dim_enso: série inteira do ONI) | Mês de referência (sempre dia 1) |
| ano | Int16 |  | ano de data_ref | Ano de data_ref |
| mes | Int8 |  | 1 a 12 | Mês (1-12) de data_ref |
| temp_media_c | float64 |  | -30 a 50 °C | Temperatura média do mês (°C) |
| temp_max_media_c | float64 |  | -30 a 55 °C | Média das máximas diárias (°C) |
| precip_total_mm | float64 |  | real >= 0 | Precipitação total do mês (mm) |
| dias_chuva_pond | float64 |  | 0 a 31 | dias_chuva médio ponderado pelos pesos fixos |
| dias_calor_pond | float64 |  | 0 a 31 | dias_calor médio ponderado pelos pesos fixos |
| anom_temp_media_c | float64 |  | real | temp_media_c - normal (°C) |
| anom_temp_max_media_c | float64 |  | real | temp_max_media_c - normal (°C) |
| anom_precip_mm | float64 |  | real | precip_total_mm - normal (mm) |
| anom_dias_calor | float64 |  | real | dias_calor - normal |

### `gold_features_uf_mes` (gold)

Granularidade: uma linha por UF × mês × classe (base ML-Ready). Fonte: EPE — consumo mensal de energia elétrica; Open-Meteo Archive API (reanálise ERA5, Copernicus C3S); NOAA CPC/PSL — Oceanic Niño Index.

| coluna | tipo | chave | papel | domínio | descrição |
| --- | --- | --- | --- | --- | --- |
| cod_ibge_uf | string | PK | chave | 27 códigos IBGE de UF | Código IBGE da UF (2 dígitos, texto) |
| uf | string |  | chave | 27 siglas | Sigla da UF |
| regiao | string |  | chave | norte, nordeste, centro_oeste, sudeste, sul | Região geográfica: norte, nordeste, centro_oeste, sudeste, sul |
| data_ref | datetime64[ns] | PK | chave | dia 1 de cada mês da janela da silver (gold_dim_enso: série inteira do ONI) | Mês de referência (sempre dia 1) |
| classe | string | PK | chave | residencial, comercial, industrial, rural, outros | Classe de consumo (EPE) |
| y_log_consumo_dia | float64 |  | alvo | real ou nulo (consumo <= 0) | ln(consumo_mwh_por_dia); nulo se consumo <= 0 |
| y_yoy_log_consumo_dia | float64 |  | alvo | real ou nulo (primeiros 12 meses) | y_log_consumo_dia - mesmo mês do ano anterior (remove sazonalidade e boa parte da tendência) |
| ano | Int16 |  | feature | ano de data_ref | Ano de data_ref |
| mes | Int8 |  | feature | 1 a 12 | Mês (1-12) de data_ref |
| pct_livre_lag1 | float64 |  | feature | real ou nulo (consumo <= 0); normalmente 0 a 1, sai disso por estornos | pct_livre do mês anterior (o do próprio mês sai do consumo-alvo) |
| dias_no_mes | Int8 |  | feature | 28 a 31 | Dias corridos do mês |
| dias_uteis | Int8 |  | feature | 0 a 23 | Dias úteis: seg-sex menos feriados nacionais (sem feriados estaduais/municipais, Carnaval, Corpus Christi) |
| mes_sin | float64 |  | feature | -1 a 1 | sen(2π·mes/12): sazonalidade contínua |
| mes_cos | float64 |  | feature | -1 a 1 | cos(2π·mes/12): sazonalidade contínua |
| t | Int16 |  | feature | inteiro >= 0 | Tendência: meses desde o início da janela (0 = primeiro mês) |
| flag_covid | boolean |  | feature | True, False | Mês dentro do recorte COVID (COVID_INI..COVID_FIM) |
| temp_media_c | float64 |  | feature | -30 a 50 °C | Temperatura média do mês (°C) |
| temp_max_media_c | float64 |  | feature | -30 a 55 °C | Média das máximas diárias (°C) |
| precip_total_mm | float64 |  | feature | real >= 0 | Precipitação total do mês (mm) |
| dias_chuva | Int16 |  | feature | 0 a 31 | Dias com chuva (limiar da silver) |
| dias_calor | Int16 |  | feature | 0 a 31 | Dias com Tmax acima do limiar da silver (35 °C): pode ser quase sempre 0 |
| anom_temp_media_c | float64 |  | feature | real | temp_media_c - normal (°C) |
| anom_temp_max_media_c | float64 |  | feature | real | temp_max_media_c - normal (°C) |
| anom_precip_mm | float64 |  | feature | real | precip_total_mm - normal (mm) |
| anom_dias_calor | float64 |  | feature | real | dias_calor - normal |
| temp_media_c_lag1 | float64 |  | feature | -30 a 50 °C | temp_media_c do mês anterior (o faturamento defasa o consumo em ~1 mês) |
| temp_max_media_c_lag1 | float64 |  | feature | -30 a 55 °C | temp_max_media_c do mês anterior (o faturamento defasa o consumo em ~1 mês) |
| precip_total_mm_lag1 | float64 |  | feature | real >= 0 | precip_total_mm do mês anterior (o faturamento defasa o consumo em ~1 mês) |
| anom_temp_media_c_lag1 | float64 |  | feature | real | anom_temp_media_c do mês anterior (o faturamento defasa o consumo em ~1 mês) |
| anom_temp_max_media_c_lag1 | float64 |  | feature | real | anom_temp_max_media_c do mês anterior (o faturamento defasa o consumo em ~1 mês) |
| anom_precip_mm_lag1 | float64 |  | feature | real | anom_precip_mm do mês anterior (o faturamento defasa o consumo em ~1 mês) |
| oni_lag1 | float64 |  | feature | -5 a 5 °C (anomalia) | ONI de 1 mês(es) antes. Lag 1 só é conhecido ao fim do mês-alvo; lag >= 2 antes de ele começar |
| oni_lag2 | float64 |  | feature | -5 a 5 °C (anomalia) | ONI de 2 mês(es) antes. Lag 1 só é conhecido ao fim do mês-alvo; lag >= 2 antes de ele começar |
| oni_lag3 | float64 |  | feature | -5 a 5 °C (anomalia) | ONI de 3 mês(es) antes. Lag 1 só é conhecido ao fim do mês-alvo; lag >= 2 antes de ele começar |
| oni_lag4 | float64 |  | feature | -5 a 5 °C (anomalia) | ONI de 4 mês(es) antes. Lag 1 só é conhecido ao fim do mês-alvo; lag >= 2 antes de ele começar |
| oni_lag5 | float64 |  | feature | -5 a 5 °C (anomalia) | ONI de 5 mês(es) antes. Lag 1 só é conhecido ao fim do mês-alvo; lag >= 2 antes de ele começar |
| oni_lag6 | float64 |  | feature | -5 a 5 °C (anomalia) | ONI de 6 mês(es) antes. Lag 1 só é conhecido ao fim do mês-alvo; lag >= 2 antes de ele começar |
| el_nino_causal_lag1 | boolean |  | feature | True, False | el_nino_causal de 1 mês(es) antes |
| la_nina_causal_lag1 | boolean |  | feature | True, False | la_nina_causal de 1 mês(es) antes |
| el_nino_causal_lag2 | boolean |  | feature | True, False | el_nino_causal de 2 mês(es) antes |
| la_nina_causal_lag2 | boolean |  | feature | True, False | la_nina_causal de 2 mês(es) antes |
| ar_y_log_lag1 | float64 |  | feature | real ou nulo (primeiro mês) | y_log_consumo_dia do mês anterior (exige horizonte de 1 mês) |
| ar_y_log_lag12 | float64 |  | feature | real ou nulo (primeiros 12 meses) | y_log_consumo_dia de 12 meses antes |
