# ADR-008 · Quién decide si responder: tres alternativas medidas y la elegida

- **Estado:** aceptada · **Fecha:** 2026-11-19 · **Modifica:** ADR-003 (la composición sigue siendo extractiva; cambia quién puntúa la frase y cuántas se devuelven)
- **Evidencia:** `eval/comparacion/` (ronda 3, final), `eval/comparacion_ronda1/`, `eval/comparacion_ronda2/`; conjuntos `eval/casos_referencia.yaml` (30) y `eval/casos_validacion.yaml` (23)

## Contexto

Con `multilingual-e5-small` y laya, el sistema entregado (A0) dio 20 % de desviación frente a un SLO propio de 10 %. Cinco de los seis fallos eran negativas de más ante paráfrasis («meterle mano», «apagada», «revisar en sitio»). En los cinco la recuperación sí traía la fuente en el rango 1 o 2: lo que fallaba era la **decisión de responder**, una regla léxica (la frase debe cubrir el 60 % de la pregunta). Cambiar spaCy por e5 subió la búsqueda semántica de 62 % a 100 % de acierto@5 y no movió esas negativas.

La pregunta de arquitectura es qué poner en ese paso de decisión sin perder las dos garantías que justifican el diseño: toda cifra es texto literal de un documento vigente (ADR-003) y «no lo sé» es una respuesta correcta.

## Alternativas

Las tres comparten índice, búsqueda híbrida, filtro de vigencia dentro de la consulta, composición extractiva y citas. Cambia solo el paso de decisión. Ninguna es un agente: no hay bucle de razonamiento ni herramientas, solo un paso de modelo dentro de un flujo fijo, como pide el enunciado para el Escenario A.

| | Qué hace | Peldaño de autonomía |
|---|---|---|
| **A0** · cobertura léxica (entregada) | La frase se elige y se acepta por cobertura ponderada por IDF ≥ 0,6 | Workflow determinista |
| **A1** · LLM interpreta | Un LLM local (`Qwen2.5-1.5B-Instruct`, Apache-2.0, en CPU) reescribe la pregunta con el vocabulario de los documentos; se busca con original + reescritura; decide la cobertura | Workflow aumentado con un paso **generativo** |
| **A2** · decisor local tipo Sistema 1 | Un clasificador local (`bge-reranker-v2-m3`, Apache-2.0) puntúa P(la frase responde la pregunta); responde si ≥ 0,5 | Workflow aumentado con un paso de **clasificación**, sin generación |

En vocabulario EIP, A1 agrega un Message Translator no determinista delante del Content Enricher, y A2 es el «reordenamiento posterior» de la sesión 10, que mejora la precisión a costa de latencia.

Se midieron además:

- **A0G**: A0 + guarda de entidades, sin modelo (ablación).
- **A3**: la cadena completa, LLM que amplía la búsqueda + decisor.

**Guarda de entidades** (`guardas.py`), común a A1, A2 y A3: una frase solo puede responder si nombra los tramos, códigos, equipos y lugares de la pregunta. En A1, además, la reescritura se descarta si pierde una entidad o agrega una cifra.

**Juez:** laya (`laya:ml`) para las tres. No participa en ninguna decisión. Por eso el decisor de A2 no es laya: si el mismo modelo decide y califica, la evaluación deja de ser independiente.

## Método: tres rondas, sin ajustar con los casos que se reportan

1. **Ronda 1:** A0, A0G, A1 y A2 sobre referencia (30) y validación v1.0 (17 casos nuevos, escritos antes de correr nada con modelos).
   - Hallazgo: A2 tuvo **3 respuestas indebidas** en referencia (C01, C03, C20). Elegía bien la primera frase y agregaba otras que el decisor también puntuaba cerca de 1: la MAOP junto al umbral de alarma, y el acta con «de 1.200 a 1.100».
2. **Ronda 2:** antes de corregir, se agregaron 6 trampas de valor nuevas a la validación (v1.1: V18–V23). Luego se probó la regla «frases adicionales solo del mismo documento» (A2md).
   - Resultado: referencia 30/30, pero en la validación nueva **V23 mezcló otra vez** dos filas de la misma tabla (temperatura de cojinetes y vibración de la P-101). La corrección era incompleta, y la validación lo detectó.
3. **Ronda 3 (final):** A2 devuelve **una sola frase**. Esta regla se eligió después de ver V23, así que ningún conjunto es ya independiente para ella (ver Sesgos).

## Resultados (ronda 3, Windows, Ryzen 5 9600X, 32 GB, CPU)

| | A0 | A0G | A1 | A2 (elegida) | A3 |
|---|---|---|---|---|---|
| **Referencia: correctos** | 24/30 | 24/30 | 25/30 | **30/30** | 30/30 |
| **Validación: correctos** | 12/23 | 14/23 | 15/23 | **18/23** | 18/23 |
| Desviación referencia / validación | 20 % / 48 % | 20 % / 39 % | 17 % / 35 % | **0 % / 22 %** | 0 % / 22 % |
| **Indebidas** (fuera del corpus o valor prohibido), ref. + val. | 0 + **2** | 0 + 0 | 0 + 0 | **0 + 0** | 0 + 0 |
| Negativas de más, ref. + val. | 5 + 8 | 5 + 8 | 5 + 7 | **0 + 3** | 0 + 3 |
| Erradas (otro dato u otra cita), ref. + val. | 1 + 1 | 1 + 1 | 0 + 1 | 0 + 2 | 0 + 2 |
| Rechazo correcto (validación) | 60 % | 100 % | 100 % | 100 % | 100 % |
| Fidelidad de la reescritura (laya) | — | — | 80 % / 83 % | — | 80 % / 83 % |
| Latencia p50 (p95) | 15 ms | 15 ms | 2,7 s (4,4 s) | **1,5 s (3,4 s)** | 4,1 s (7,1 s) |
| Modelo adicional | — | — | 3,1 GB · ~6 GB de RAM | 2,3 GB | ambos |

Para comparar: A2 tal como corrió en la ronda 1 (A2r1) dio 27/30 con 3 indebidas y 19/23 con 1 indebida, y A2md dio 30/30 y 19/23 con 1 indebida.

**Lectura:**

- **A2 es la única alternativa que ataca la causa.** Un clasificador entrenado para decidir si un pasaje responde una pregunta reconoce «apagada» → «parada» sin reescribir nada. Rescata C05, C10, C12, C13 y C29 en referencia y 4 de las 8 paráfrasis de validación (V02, V05, V06, V07); una quinta (V04) la responde, pero con la fila equivocada.
- **El LLM interpretativo casi no aporta y agrega un riesgo nuevo.**
  - Frente a la misma guarda sin modelo (A0G), A1 mejora un caso en cada conjunto (C26 y V01) y tarda 2,7 s.
  - laya juzga que en 17–20 % de las reescrituras la pregunta cambió. Ejemplos: «energía peligrosa» pasó a «equipo eléctrico» (C12); «cada cuánto» pasó a «cómo se determina la frecuencia» (C09); para V17 inventó un documento («Procedimiento General de Gestión»).
  - Hay cambios que laya no detecta: «transferencia de custodia» pasó a «transiciones entre puntos de control» (C08, laya 0,94). Vigilar la fidelidad necesitaría su propio juez calibrado.
  - La guarda descartó 3 reescrituras que perdían una entidad («Gerencia» → «Gestión»).
  - A3 (LLM + decisor) da exactamente lo mismo que A2 con 2,5 s más.
- **La guarda es barata y necesaria.** Sin guarda, A0 respondió el umbral de otro tramo cuando le preguntaron por «Barrancabermeja – Coveñas», que no existe (V13), y el año de la P-101 cuando le preguntaron por la P-205 (V14). A0G elimina esas dos respuestas indebidas sin costo en referencia. El modo degradado usa A0G por eso.
- **El trade-off que queda en A2: una sola frase.**
  - Elimina las mezclas de valores, pero en 2 casos de validación la única frase elegida, de la fuente correcta, no es la que contesta:
    - V04: la fila «Autoridad competente, 24 horas», cuyo responsable es la Gerencia de Seguridad Física, cuando se preguntaba por el plazo para avisar a esa Gerencia (2 horas). Es el fallo más delicado: un lector apurado podría tomar 24 horas por la respuesta.
    - V21: la cláusula 3.2 (investigar en tres días hábiles) en vez de la fila de tolerancia; no da ningún valor.
  - Con varias frases (A2md), esos dos casos salían bien y V23 traía un valor ajeno.
  - Elegimos con el criterio declarado antes de medir: un valor prohibido en la respuesta es peor que una fila equivocada con su etiqueta, porque la etiqueta permite al operador ver que no es lo que preguntó. En V04 esa defensa es débil, y el conjunto no marcó «24 horas» como prohibido: con esa marca, A2 tendría 1 indebida y A2md 2, porque A2md devuelve la misma fila en primer lugar. La preferencia por una sola frase se mantiene, pero no con cero indebidas (documento A, §8.5).

## Matriz de decisión

Formato de la matriz de decisión estratégica de la sesión 15. Criterios en orden de prioridad.

| Criterio y fundamento | A0 | A1 | **A2** | A3 |
|---|---|---|---|---|
| 1. No responder fuera del corpus ni con un valor ajeno | ✗ 2 indebidas en validación | ✓ (gracias a la guarda) | ✓ | ✓ |
| 2. Cifras literales de un documento vigente (ADR-003) | ✓ | ✓ | ✓ | ✓ |
| 3. Utilidad: desviación en validación | 48 % | 35 % | **22 %** | 22 % |
| 4. Peldaño de autonomía y predecibilidad (el más bajo que resuelva) | Determinista, pero no resuelve | Generativo; 17–20 % de cambios de sentido | **Clasificador; misma entrada, mismo puntaje** | Generativo + clasificador, sin ganancia |
| 5. Costo y latencia (TCO) | 15 ms, sin modelo | 2,7 s, ~6 GB de RAM | 1,5 s, 2,3 GB | 4,1 s, ambos |
| 6. Operación y evaluación continua (reevaluar ante cada cambio de modelo o de prompt) | Nada que reevaluar | Modelo y prompt; hay que vigilar la fidelidad | Modelo con revisión fijada; correr `comparar` al cambiarlo | Los dos |
| 7. Superficie de ataque | Ninguna nueva | La pregunta del usuario entra a un generador | El clasificador no produce texto | Como A1 |
| 8. Soberanía | — | Local, Apache-2.0 | Local, Apache-2.0 | Local |

## Decisión

**A2 en operación** (`PETROANDES_ESTRATEGIA=A2`, por defecto en el servidor MCP, en `preguntar` y en `evaluar`):

- decisor local `BAAI/bge-reranker-v2-m3`, umbral 0,5;
- guarda de entidades;
- una sola frase por respuesta.

**Modo degradado explícito:** si el modelo no se puede cargar, el sistema pasa a **A0G** y lo dice en la respuesta. Así conserva la garantía de no responder fuera del corpus, con más negativas.

**Se descartan A1 y A3.** El paso generativo no ganó su lugar: sube un peldaño de autonomía y agrega latencia, un modo de falla nuevo (cambiar el sentido de la pregunta) y una obligación de evaluación continua, sin mejorar sobre A2. Queda implementado (`--estrategia A1`) como evidencia y para volver a medirlo si cambia el modelo.

**El umbral 0,5 se fijó antes de medir** (punto medio de la probabilidad). El barrido muestra que 0,1 baja la desviación de validación a 13 %, pero agrega una respuesta indebida en referencia, así que no se cambió.

## Sesgos y límites declarados

- **Los números de A2 son optimistas.** La regla de adicionales se diseñó mirando la referencia (ronda 1) y la de una sola frase mirando V23 (ronda 2). Solo la ronda 1 de validación fue ciega. Antes de producción hace falta un tercer conjunto, construido con las áreas emisoras, que nadie del equipo haya visto.
- 53 casos en total son pocos: una diferencia de 1–2 casos no es concluyente. Lo robusto son las diferencias grandes (5 negativas de más rescatadas en referencia; 2 indebidas eliminadas por la guarda) y los mecanismos observados.
- Ninguna alternativa cumple el SLO agregado de ≤ 10 % en validación; A2 lo deja en 22 % (5 de 23 casos).
  - **Desglose de A2:** 0 % de respuestas indebidas, 9 % con otra frase de la fuente correcta (V04, V21) y 13 % de negativas de más (V01, V03, V08).
  - **El SLO no se cambia a posteriori.** Se propone, para la siguiente versión, separarlo por gravedad: indebidas 0 %, otra frase u otra cita ≤ 10 %, negativas de más ≤ 20 % (el umbral de abandono ya declarado en el documento A, §8.3).
  - **Contra ese esquema A2 cumple los tres tipos,** pero es una lectura posterior (con la lectura estricta de V04 no cumpliría el de indebidas): el esquema se formuló después de medir y con 23 casos cada caso pesa 4,3 puntos (documento A, §8.5).
- laya como juez:
  - confirma el anclaje;
  - sus preguntas «¿responde?» y «¿pertinente?» discrepan de las etiquetas de oro: puntúa bajo filas de tabla correctas y literales;
  - por eso esas dos métricas se reportan sin usarse para decidir (ADR-006);
  - la decisión se apoya en la desviación medida con hechos de oro, que es determinista.
- Las latencias son de un solo equipo con CPU. En el contenedor de producción (ADR-005, sección 10 del documento A) A2 cabe en CPU, pero conviene medir allí.

## Consecuencias

- La respuesta deja de ser 100 % determinista en el paso de decisión. El clasificador da el mismo puntaje ante la misma entrada, pero un cambio de modelo o de revisión puede cambiar respuestas. Por eso:
  - el modelo se fija por revisión;
  - `petroandes-docs comparar` es el Control Bus para reevaluar antes de cambiarlo.
- Cada respuesta registra en la auditoría la estrategia y el decisor que la produjeron (Wire Tap).
- La experiencia de demostración cambia: «Antes de meterle mano a un equipo con energía peligrosa…» ya se responde (C12), y la pregunta por un tramo inexistente se sigue negando.
