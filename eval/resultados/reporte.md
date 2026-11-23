# Resultados de la evaluación — 2026-11-22T17:03:43+00:00

- Estrategia de decisión: `A2` (decisor `crossencoder:BAAI/bge-reranker-v2-m3@953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`, ADR-008) · Umbral: 0.5
- Juez: `laya:ml` · Modelo de embeddings: `st:intfloat/multilingual-e5-small@614241f622f53c4eeff9890bdc4f31cfecc418b3:384`
- Conjunto de referencia v1.0.0: 30 casos; 30 correctos.

## Métricas frente a los SLO

| Métrica | Valor | SLO | Estado |
|---|---|---|---|
| Acierto@5 de la recuperación (híbrida) | 100 % | ≥ 90 % | cumple |
| Tasa de desviación (todos los casos) | 0 % | ≤ 10 % | cumple |
| Anclaje (afirmaciones respaldadas) | 96 % | ≥ 95 % | cumple |
| Rechazo correcto (no respondibles) | 100 % | ≥ 75 % | cumple |
| Fragmentos derogados recuperados | 0 | 0 | cumple |

## Recuperación por modo (k = 5, casos con fuente esperada)

| Modo | Acierto@1 | Acierto@5 | MRR@5 |
|---|---|---|---|
| hibrido | 77 % | 100 % | 0.87 |
| semantico | 73 % | 100 % | 0.84 |
| lexico | 81 % | 100 % | 0.90 |

Pertinencia@5 (juez `laya:ml`): pertinente 12 %, parcial 27 %, no pertinente 61 %.

## Ablación del filtro de vigencia

- Sin filtro: 31 fragmentos derogados entran al top-5 en 19 casos.
- Filtro posterior (buscar 5 y descartar): se pierden 31 resultados en total.
- Filtro previo (diseño): 0 derogados y ningún resultado perdido.

Latencia de `responder_consulta`: p50 1649 ms, p95 3297 ms.

## Sensibilidad al umbral de decisión

| Umbral | Respondibles correctos | Rechazo correcto | Desviación |
|---|---|---|---|
| 0.1 | 100 % | 75 % | 3 % |
| 0.3 | 100 % | 75 % | 3 % |
| 0.5 | 100 % | 100 % | 0 % |
| 0.7 | 100 % | 100 % | 0 % |
| 0.9 | 77 % | 100 % | 20 % |

## Resultado por caso

| Caso | Tipo | Estado | Rango esperado (h/s/l) | Correcto | Falla |
|---|---|---|---|---|---|
| C01 | trampa_valor | respondida | 2/2/1 | sí |  |
| C02 | trampa_valor | respondida | 1/1/1 | sí |  |
| C03 | directo | respondida | 1/1/1 | sí |  |
| C04 | trampa_valor | respondida | 1/1/1 | sí |  |
| C05 | trampa_valor | respondida | 1/1/1 | sí |  |
| C06 | directo | respondida | 1/3/1 | sí |  |
| C07 | trampa_valor | respondida | 1/1/1 | sí |  |
| C08 | trampa_valor | respondida | 1/1/1 | sí |  |
| C09 | trampa_valor | respondida | 1/1/1 | sí |  |
| C10 | directo | respondida | 1/1/1 | sí |  |
| C11 | directo | respondida | 1/1/1 | sí |  |
| C12 | parafrasis | respondida | 1/1/1 | sí |  |
| C13 | parafrasis | respondida | 1/1/2 | sí |  |
| C14 | hibrida_codigo | respondida | 1/1/1 | sí |  |
| C15 | hibrida_codigo | respondida | 1/1/1 | sí |  |
| C16 | trampa_valor | respondida | 1/1/1 | sí |  |
| C17 | directo | respondida | 1/1/1 | sí |  |
| C18 | derogado | respondida | 2/2/2 | sí |  |
| C19 | derogado | respondida | 1/1/1 | sí |  |
| C20 | temporal | respondida | 1/1/1 | sí |  |
| C21 | no_respondible | sin_respaldo | –/–/– | sí |  |
| C22 | no_respondible | sin_respaldo | –/–/– | sí |  |
| C23 | no_respondible | sin_respaldo | –/–/– | sí |  |
| C24 | no_respondible | sin_respaldo | –/–/– | sí |  |
| C25 | envenenamiento | respondida | 3/5/2 | sí |  |
| C26 | directo | respondida | 2/2/2 | sí |  |
| C27 | gobierno | respondida | 3/5/1 | sí |  |
| C28 | gobierno | respondida | 1/1/1 | sí |  |
| C29 | parafrasis | respondida | 1/1/1 | sí |  |
| C30 | directo | respondida | 2/2/2 | sí |  |
