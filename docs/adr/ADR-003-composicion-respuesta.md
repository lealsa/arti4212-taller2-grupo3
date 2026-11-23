# ADR-003 · Composición de la respuesta: determinista y extractiva, sin modelo generativo

- **Estado:** aceptada, modificada por [ADR-008](ADR-008-estrategia-de-decision.md) · **Fecha:** 2026-11-17

> **Modificación (ADR-008, 2026-11-19).** La composición sigue siendo extractiva y sin modelo generativo. Cambia el paso 2–3: en operación, la frase se puntúa con un decisor local que no genera texto (`bge-reranker-v2-m3`, umbral 0,5), hay una guarda de entidades y se devuelve una sola frase. La cobertura léxica de este ADR queda como estrategia A0 y, con guarda, como modo degradado (A0G). La latencia pasa de ~10 ms a ~1,5 s por respuesta, y la tabla y las cifras de abajo describen la versión original.

## Contexto

La respuesta debe citar documento, versión y sección en toda afirmación, no usar conocimiento ajeno al contexto recuperado y declarar cuando la respuesta no está en el corpus (enunciado §3.2). El enunciado deja elegir entre un modelo generativo gratuito o local y una composición determinista, y pide justificar qué cambia en la evaluación.

## Alternativas

| | A. Modelo generativo (local, p. ej. Ollama con un modelo de 7–8B, o API gratuita) | B. Composición determinista extractiva (elegida) |
|---|---|---|
| Citas | Se piden en el prompt; hay que verificarlas después | Por construcción: cada afirmación ES una unidad citada |
| Anclaje | Probabilístico: puede agregar datos, mezclar tramos o redondear cifras | Total: el texto se copia literal de la fuente |
| Negativa honesta | Depende de que el modelo obedezca «si no está, dilo» | Regla explícita: cobertura de la pregunta por debajo del umbral → `sin_respaldo` |
| Envenenamiento | El modelo lee el anexo y puede obedecerlo | No hay quien obedezca; el anexo además está en cuarentena |
| Redacción | Fluida, sintetiza varias fuentes, responde paráfrasis | Literal, a veces seca; no sintetiza ni infiere |
| Costo y latencia | GPU o cuota de API; segundos por respuesta | CPU; ~10 ms por respuesta en el prototipo |
| Reproducibilidad | Baja (dos ejecuciones pueden diferir) | Total |

## Decisión

**B. Composición determinista extractiva** (`composicion.componer`):

1. Recupera k = 6 fragmentos con la búsqueda híbrida filtrada.
2. Puntúa cada unidad (cláusula, viñeta o fila) por **cobertura ponderada por IDF**: qué fracción del peso de los términos de la pregunta aparece en la unidad más el contexto de su sección. Los términos que el corpus no contiene pesan el IDF máximo, así que una pregunta sobre algo ajeno al corpus («Brent», «gasoductos») baja la cobertura.
3. Si la mejor cobertura es menor que el umbral (0,6), responde `sin_respaldo` y lista los fragmentos más cercanos sin afirmar nada.
4. Si no, devuelve hasta tres unidades literales con su cita, prefiriendo la norma sobre el antecedente cuando cubren casi igual.
5. Si la pregunta nombra un documento derogado, lo advierte (regla, fecha y certificador) y reescribe la consulta hacia el documento vigente antes de buscar.

El umbral de 0,6 se eligió mirando el barrido del conjunto de referencia (sesgo declarado: no hay un conjunto de validación separado). La regla de elección fue de riesgo: preferimos negarnos de más que responder mal, porque una cifra errada de un umbral de alarma es un incidente y una negativa solo es una molestia.

## Qué cambia en la evaluación

- **Anclaje deja de ser informativo**: con composición extractiva es 100 % por construcción. Lo medimos igual, como prueba de integridad de la cita (que el texto citado exista literal en el fragmento citado), pero no prueba calidad.
- **La calidad se desplaza a la recuperación y a la selección**: qué fragmento se trae y qué unidad se elige. Por eso el arnés mide acierto@k por modo, pertinencia y, sobre todo, **tasa de desviación con hechos esperados y prohibidos**.
- **El modo de falla cambia de signo**: un generador falla respondiendo algo plausible y falso; este diseño falla **negándose** ante paráfrasis que no comparten palabras con la fuente (C12, C13, C29). La tasa de falsas negativas es la métrica a vigilar.
- Con la opción A habría que medir anclaje con el juez (laya `noul`) sobre cada afirmación generada, y la tasa de desviación incluiría cifras alteradas por el modelo, que hoy no pueden ocurrir.
- Con el decisor de ADR-008, las paráfrasis de referencia (C12, C13, C29) ya se responden y quedan 3 negativas de más en validación. Aparece un modo de falla nuevo, la frase literal de la fuente correcta que no contesta (V04, V21), que solo se ve con hechos esperados por caso. Por eso la comparación de estrategias se hizo con el mismo juez y el mismo conjunto para todas.

## Consecuencias

- Toda cifra que entrega `responder_consulta` está literal en un documento vigente, pero puede ser la de otra fila de la tabla correcta (V04). Por eso el Escenario B lee la tolerancia con `obtener_fragmento` y no con `responder_consulta`.
- Las respuestas no sintetizan («el umbral bajó de 1.200 a 1.100 porque…» exige un generador). Si el negocio pide síntesis, la opción A se agrega **después** de esta capa, recibiendo solo las unidades ya citadas, y con su propio juez de anclaje.
