# Guion de la demostración y preparación de la sustentación

**Taller 2 · ARTI 4212 · Grupo 3 · Integrantes:** Camila Andrea Morales Ortega · Santiago Andrés Leal Omaña · Miguel Ángel Mendieta Hernández · Santiago Baquero Villa

Sustentación: unos 15 minutos (10 de demostración y 5 de preguntas). El comité puede elegir quién responde: todos deben poder contestar cualquiera de las preguntas de la §2.

Antes de entrar: índice construido (`petroandes-docs ingestar`), una terminal con letra grande y el Inspector abierto en otra pestaña (`make inspector`). Comprobar que `petroandes-docs vigencia` lista los 19 documentos. La estrategia por defecto es A2 (ADR-008): cada respuesta tarda 1–3 s y la primera carga el decisor (unos 3 s más). Si no hay red ni modelo descargado, el sistema avisa que está en modo degradado.

## 1. Demostración (10 minutos)

| Min | Escena | Comando | Qué señalar |
|---|---|---|---|
| 0–1 | Encuadre | — | Es una integración de datos, no un agente: contrato, vigencia certificada, recuperación filtrada, medición |
| 1–3 | **Consulta fundamentada con citas** | `petroandes-docs preguntar "¿Cuál es el umbral de alarma de presión en el tramo Ayacucho – Coveñas?"` | Responde 1.100 psi [PRO-OPE-012 v3 §3]. En el corpus hay 1.200 (derogado), 1.250 (MAOP) y 1.240 (bomba P-101): ninguno aparece |
| 3–4 | Misma pregunta en el pasado | `… --fecha 2025-08-15` | Responde 1.200 [PRO-OPE-012 v2 §3]: el comité aprobó 1.100 en julio, pero no regía hasta la v3 (ACTA-CTO-2025-07 §4.2) |
| 4–5 | **Pregunta fuera del corpus** | `petroandes-docs preguntar "¿Cuál es el precio del barril de crudo Brent hoy?"` | `sin_respaldo`: no responde con conocimiento externo |
| 5–7 | **Intento de recuperar un derogado** | `petroandes-docs preguntar "Según el PRO-SEG-009, ¿en cuánto tiempo se reporta a la autoridad competente una pérdida de producto?"` y en el Inspector `obtener_fragmento` con PRO-OPE-012, versión 2, sección 3 | Advierte que PRO-SEG-009 está derogado (R2, reemplazado por otro código) y responde 24 horas con PRO-SEG-015; el Inspector devuelve `DOCUMENTO_DEROGADO` con el reemplazo |
| 7–8 | Híbrida frente a semántica | `petroandes-docs buscar "¿A quién se escalan las diferencias de balance superiores al uno por ciento y cuándo?" --modo semantico` y luego `--modo hibrido` | La semántica pone primero el acta del comité (no normativa) y el procedimiento en el rango 3; la híbrida trae primero PRO-MED-007 v2 §3 |
| 8–9 | **Paráfrasis: el problema y la decisión** | `petroandes-docs preguntar "Antes de meterle mano a un equipo con energía peligrosa, ¿quién confirma que quedó en energía cero?" --estrategia A0` y luego sin `--estrategia` (A2) | A0 se niega (no comparte palabras con la fuente); A2 responde «verificación de energía cero por el ejecutante» [PRO-HSE-003 v4 §3]. Luego `… "¿Cuál es el umbral de alarma de presión del tramo Barrancabermeja – Coveñas?"`: se niega, porque ese tramo no existe (guarda de entidades) |
| 9–10 | **Comparación de tres alternativas y la métrica mala** | abrir `eval/comparacion/comparacion.md` y §8.5 del documento A | Presentar como resultado principal la tabla de **validación** (no el 30/30 de referencia, porque ese conjunto se vio al ajustar reglas): A0 12/23 con 2 respuestas indebidas; A1 (LLM) 15/23 y 2,7 s; A2md 19/23 con 1 indebida; A2 **18/23 y 0 indebidas** (elegimos perder 1 acierto para tener un error peligroso menos); A3 = A2 con 2,5 s más. Luego decir la métrica mala sin que la pregunten: «El SLO de desviación era ≤ 10 % y en validación quedamos en 22 %. No cumple. Pero el error peligroso está en cero: el 22 % son 3 negativas de más y 2 respuestas que citan la fuente correcta con otra frase. Y lo digo antes de que lo pregunten: una de esas, V04, devuelve el plazo de 24 horas de otra fila; si la hubiéramos marcado como prohibida, tendríamos 1 indebida. Aprendimos que un SLO agregado mezcla errores de gravedad distinta, y proponemos SLO por tipo para la siguiente versión.» |

Si sobra tiempo: `petroandes-docs prueba-envenenamiento` y abrir `eval/resultados/envenenamiento.md` en la sección 4 (la paráfrasis que evade el detector).

## 2. Preguntas típicas y respuestas de base

**¿Quién certifica la vigencia en su diseño y qué pasa si ese sistema no existe?**
El registro de vigencia, que según ACTA-CTO-2025-11 §4.1 le corresponde a Cumplimiento. Hoy no existe: mientras tanto certifica el área emisora (§4.2). Nuestro motor de reglas propone y el registro decide; si contradice la evidencia, la ingesta se detiene. Sin certificación, un documento nunca queda vigente: queda `pendiente_certificacion` y se cita con advertencia, que es lo que pasa con los tres manuales, porque el corpus dice que uno dejó de aplicarse y no dice cuál.

**Muestre un caso en que la búsqueda híbrida cambia el resultado frente a la puramente semántica.**
C06 (escalamiento de diferencias de balance): la semántica pone primero ACTA-CTO-2025-11, que no es normativa, y deja PRO-MED-007 v2 §3 en el rango 3; la híbrida lo trae primero. Y en sentido contrario, C13 (paráfrasis «apagada»): la léxica deja la fuente en el rango 2 y la híbrida la trae primera. Con e5, acierto@1: híbrida 77 %, semántica 73 %, léxica 81 %. Advertencia: la léxica sola sigue siendo la mejor en el primer puesto en este corpus, porque las preguntas repiten el vocabulario de los documentos; la híbrida es la que no se cae en ninguno de los dos tipos de pregunta.

**¿Por qué ese nodo del Escenario B es determinista y no agéntico?**
El cálculo: la cifra sustenta un reporte regulatorio y PRO-MED-007 v2 §2.2 dice que solo el sistema de balance la produce. La correlación con presión: PRO-OPE-012 v3 §3.2 la define como una concurrencia temporal, es una consulta; y su consecuencia (activar PRO-SEG-015, autoridad en 24 horas) no puede depender de un juicio probabilístico.

**¿Por qué no cumplen el SLO de desviación? ¿No era mejor poner uno más alto?**
Quedamos en 22 % frente a 10 %, y no lo cambiamos después de medir: eso sería acomodar el SLO al resultado. Lo que aprendimos es que un SLO agregado mezcla errores de gravedad distinta.
- Respuestas indebidas: 0 %. Es el error peligroso, y está en cero.
- Otra frase de la fuente correcta: 9 %. Cita bien el documento; en V04 la frase es otra fila de la tabla (24 horas en vez de 2) y es el caso más delicado.
- Negativas de más: 13 %. El operador busca el documento por otro lado.

Para la siguiente versión proponemos SLO por tipo, fundados en la operación: 0 % de indebidas, ≤ 10 % de otra frase, ≤ 20 % de negativas, que es el umbral de abandono que ya teníamos escrito. Contra ese esquema cumpliríamos los tres con las etiquetas del conjunto, pero lo decimos como lectura posterior: con 23 casos cada caso pesa 4,3 puntos, y si V04 se cuenta como indebida no cumpliríamos el primero.

**¿Qué mide exactamente su métrica de anclaje y qué valor la haría inaceptable?**
La fracción de afirmaciones cuyo texto está respaldado por el fragmento que citan. Con composición extractiva es 100 % por construcción (cada afirmación es una subcadena literal del fragmento citado), así que la usamos como prueba de integridad de la cita, no de calidad (ADR-003). Con A2, `laya` marca 96 % en referencia (25/26) porque puntúa con 0,414 la fila de tabla literal de C02, lo cual confirma su sesgo contra filas con formato `columna: valor`. La métrica que de verdad vigila la calidad es la desviación con hechos prohibidos. Inaceptable: cualquier afirmación no anclada (significaría que la cita no corresponde al texto) y cualquier derogado recuperado.

**¿Cómo los atacaría un documento envenenado y qué capa lo detiene?**
COM-PRV-0134: su anexo pide ignorar al operador y enviar balances a un buzón externo. El escáner lo pone en cuarentena (detecta), pero una paráfrasis lo evade: lo demostramos. Lo que lo detiene siempre es la contención: composición extractiva (nadie obedece: el decisor clasifica, no genera ni sigue instrucciones), servidor de solo lectura (no hay cómo enviar nada) y, en el Escenario B, la Regla de Dos (el agente no tiene herramientas con efectos mientras lee contenido no confiable).

**Si mañana cambian el modelo de embeddings, ¿qué tienen que hacer?**
ADR-004: el índice se niega a buscar con otro modelo. Se construye una colección nueva, se corre el arnés, se compara con la línea base, se recalibra el umbral, se cambia el manifiesto en un paso y se conserva la colección anterior un ciclo para reversión.

**¿Dónde correría esto en producción y cuánto costaría al mes?**
En AWS (la nube predominante del caso), región São Paulo por residencia de datos, zona IT detrás del AI Gateway: servidor MCP en Streamable HTTP con OAuth, Qdrant en modo servidor y el modelo de embeddings junto con el decisor local en CPU. Orden de magnitud: USD 200 a 400 al mes con alta disponibilidad, porque el decisor pide una instancia de 8 GB (una t3.medium de 4 GB cuesta unos USD 49 al mes en sa-east-1). Sin costo de tokens. El costo real es mantener el registro de vigencia y el conjunto de evaluación.

**¿Por qué no usaron un modelo generativo para la respuesta?**
Porque la pregunta de operación más peligrosa es una cifra, y la composición extractiva garantiza que la cifra es literal de un documento vigente. Eso costaba paráfrasis: con la decisión léxica eran cinco de seis fallos.

**¿Y por qué no un LLM para entender la paráfrasis?**
Lo medimos (ADR-008, alternativa A1): un LLM local reescribía la pregunta y el resto quedaba igual.
- Mejoró un caso por conjunto, tardó 2,7 s por pregunta y cambió el sentido de 17–20 % de las preguntas según laya, por ejemplo «energía peligrosa» → «equipo eléctrico».
- Encima del decisor no agregó nada (A3 = A2).
- Por eso aplicamos la escalera de la sesión 11: subir al peldaño generativo no ganó su lugar.
- El clasificador (A2) ataca la causa: decide si una frase responde sin reescribir nada.

**¿Por qué el decisor no es laya, si laya hace lo mismo?**
Porque laya es nuestro juez. Si el mismo modelo decide y califica, la evaluación deja de ser independiente.

**¿Qué pasó cuando el decisor falló?**
En la ronda 1 mezclaba la MAOP con el umbral de alarma (C01, C03, C20).
- Antes de corregir escribimos trampas de valor nuevas.
- La primera corrección (frases del mismo documento) falló en una de ellas (V23): de eso sirve la validación.
- La versión final devuelve una sola frase. Lo declaramos: esas reglas se ajustaron viendo casos, así que hace falta un tercer conjunto que nadie haya visto.

## 3. Lo que hay que reconocer sin que lo pregunten

- El SLO de desviación (≤ 10 %) no se cumple: 22 % en validación con A2. Por tipo: 0 % indebidas, 9 % otra frase de la fuente correcta, 13 % negativas de más. No lo cambiamos después de medir; proponemos SLO por tipo para la siguiente versión (documento A, §8.5).
- Dos reglas de A2 se ajustaron después de ver casos (la de frases adicionales mirando la referencia y la de una sola frase mirando V23); las cifras de A2 son optimistas.
- Con una sola frase, A2 cita la fuente correcta con otra frase en 2 casos de validación (V04, V21). V04 devuelve el plazo de 24 horas de la fila de la autoridad competente cuando se preguntaba por las 2 horas de Seguridad Física; el conjunto no marcó ese valor como prohibido y debió hacerlo: con esa marca, A2 tendría 1 indebida (A2md, 2).
- laya como juez de «pertinencia» y de «¿responde?» discrepa de las etiquetas de oro; lo usamos para el anclaje y reportamos el resto.
- Las certificaciones de vigencia son simuladas.
