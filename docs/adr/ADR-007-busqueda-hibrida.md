# ADR-007 · Búsqueda híbrida con fusión RRF y filtro de vigencia dentro de la consulta

- **Estado:** aceptada · **Fecha:** 2026-11-17

## Contexto

La similitud semántica falla con códigos, identificadores y números de resolución (nota RAG–EIP §5.2), y no distingue un procedimiento vigente de su versión derogada: suelen ser los dos documentos más parecidos de todo el corpus. El corpus está lleno de ambos casos (PRO-OPE-012 v2 y v3; VL-AC-061; OT-2021-03117; Resolución 0112 de 2021).

## Decisión

- Dos vectores por fragmento: denso (ADR-004) y **BM25 como vector disperso** de Qdrant, con IDF del corpus congelado en el manifiesto. El tokenizador conserva enteros los identificadores (`pro-ope-012`, `k`, `061+800`, `1.100`, `0,5`) y además los descompone.
- Fusión por **Reciprocal Rank Fusion** en el propio Qdrant: no exige calibrar puntuaciones densas contra BM25.
- El **mismo filtro** de vigencia va en las dos subconsultas (`prefetch`). Por defecto: `estado_vigencia ∈ {vigente, pendiente_certificacion, no_normativo}`. Con `fecha_referencia`: `vigente_desde ≤ f < vigente_hasta`.

## Alternativas

- **Solo semántica**: con el modelo débil de spaCy falla con códigos (acierto@5 de 62 %). Con e5 llega a 100 % de acierto@5, pero pone primero documentos no normativos que hablan del tema (C06: el acta del comité antes que PRO-MED-007).
- **Solo léxica**: la mejor en acierto@1 con ambos modelos (81 %), porque las preguntas del conjunto repiten el vocabulario de los documentos; falla en paráfrasis (C13: fuente en el rango 2). Se mantiene como modo disponible.
- **Fusión lineal de puntuaciones normalizadas**: exige un peso calibrado por modelo; RRF no.
- **Filtrar después de buscar**: la ablación muestra que con k = 5 y `multilingual-e5-small` se pierden 31 resultados en los 30 casos y que, sin filtro, entran 31 fragmentos derogados en 19 casos (con el modelo alterno de spaCy: 28 resultados perdidos y 28 fragmentos derogados en 20 casos).

## Consecuencias

- Medición: con el modelo débil de spaCy, la fusión **empeoraba el primer resultado** frente a la léxica (65 % frente a 81 % en acierto@1). Con `multilingual-e5-small` queda entre las dos (77 %, frente a 73 % semántica y 81 % léxica), con acierto@5 de 100 % en los tres modos. No gana en el primer puesto, pero compensa los casos en que una de las dos se equivoca (C06, C13). La composición mitiga el primer puesto porque puntúa unidades de los 6 primeros fragmentos.
- Casos para la sustentación: C06 (la híbrida corrige a la semántica) y C13 (la híbrida corrige a la léxica).
