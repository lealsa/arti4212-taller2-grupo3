# Resultados de la evaluación — 2026-11-18T19:40:57+00:00

- Juez: `lexico` · Modelo de embeddings: `spacy:es_core_news_md@3.8.0:300:idf-010c0c930053` · Umbral de cobertura: 0.6
- Conjunto de referencia v1.0.0: 30 casos; 25 correctos.

## Métricas frente a los SLO

| Métrica | Valor | SLO | Estado |
|---|---|---|---|
| Acierto@5 de la recuperación (híbrida) | 100 % | ≥ 90 % | cumple |
| Tasa de desviación (todos los casos) | 17 % | ≤ 10 % | NO cumple |
| Anclaje (afirmaciones respaldadas) | 100 % | ≥ 95 % | cumple |
| Rechazo correcto (no respondibles) | 100 % | ≥ 75 % | cumple |
| Fragmentos derogados recuperados | 0 | 0 | cumple |

## Recuperación por modo (k = 5, casos con fuente esperada)

| Modo | Acierto@1 | Acierto@5 | MRR@5 |
|---|---|---|---|
| hibrido | 65 % | 100 % | 0.79 |
| semantico | 42 % | 62 % | 0.49 |
| lexico | 81 % | 100 % | 0.90 |

Pertinencia@5 (juez `lexico`): pertinente 21 %, parcial 28 %, no pertinente 51 %.

## Ablación del filtro de vigencia

- Sin filtro: 28 fragmentos derogados entran al top-5 en 20 casos.
- Filtro posterior (buscar 5 y descartar): se pierden 28 resultados en total.
- Filtro previo (diseño): 0 derogados y ningún resultado perdido.

Latencia de `responder_consulta`: p50 7 ms, p95 10 ms.

## Sensibilidad al umbral de cobertura

| Umbral | Respondibles correctos | Rechazo correcto | Desviación |
|---|---|---|---|
| 0.3 | 88 % | 50 % | 17 % |
| 0.4 | 88 % | 50 % | 17 % |
| 0.5 | 81 % | 75 % | 20 % |
| 0.6 | 81 % | 100 % | 17 % |
| 0.7 | 69 % | 100 % | 27 % |

## Resultado por caso

| Caso | Tipo | Estado | Rango esperado (h/s/l) | Correcto | Falla |
|---|---|---|---|---|---|
| C01 | trampa_valor | respondida | 1/1/1 | sí |  |
| C02 | trampa_valor | respondida | 1/1/1 | sí |  |
| C03 | directo | respondida | 3/–/1 | sí |  |
| C04 | trampa_valor | respondida | 2/–/1 | sí |  |
| C05 | trampa_valor | sin_respaldo | 2/3/1 | no | se negó a responder una pregunta respondible |
| C06 | directo | respondida | 2/–/1 | sí |  |
| C07 | trampa_valor | respondida | 1/3/1 | sí |  |
| C08 | trampa_valor | respondida | 1/1/1 | sí |  |
| C09 | trampa_valor | respondida | 1/1/1 | sí |  |
| C10 | directo | sin_respaldo | 2/–/1 | no | se negó a responder una pregunta respondible |
| C11 | directo | respondida | 1/1/1 | sí |  |
| C12 | parafrasis | sin_respaldo | 1/1/1 | no | se negó a responder una pregunta respondible |
| C13 | parafrasis | sin_respaldo | 1/2/2 | no | se negó a responder una pregunta respondible |
| C14 | hibrida_codigo | respondida | 1/1/1 | sí |  |
| C15 | hibrida_codigo | respondida | 1/–/1 | sí |  |
| C16 | trampa_valor | respondida | 1/–/1 | sí |  |
| C17 | directo | respondida | 3/–/1 | sí |  |
| C18 | derogado | respondida | 5/–/2 | sí |  |
| C19 | derogado | respondida | 1/1/1 | sí |  |
| C20 | temporal | respondida | 1/1/1 | sí |  |
| C21 | no_respondible | sin_respaldo | –/–/– | sí |  |
| C22 | no_respondible | sin_respaldo | –/–/– | sí |  |
| C23 | no_respondible | sin_respaldo | –/–/– | sí |  |
| C24 | no_respondible | sin_respaldo | –/–/– | sí |  |
| C25 | envenenamiento | respondida | 3/–/2 | sí |  |
| C26 | directo | respondida | 1/1/2 | sí |  |
| C27 | gobierno | respondida | 1/4/1 | sí |  |
| C28 | gobierno | respondida | 1/1/1 | sí |  |
| C29 | parafrasis | sin_respaldo | 1/3/1 | no | se negó a responder una pregunta respondible |
| C30 | directo | respondida | 4/–/2 | sí |  |
