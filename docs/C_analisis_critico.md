# Análisis crítico: cuándo conviene el enfoque agéntico en la conciliación volumétrica

**Taller 2 · ARTI 4212 · Grupo 3 · noviembre de 2026**

**Integrantes:** Camila Andrea Morales Ortega · Santiago Andrés Leal Omaña · Miguel Ángel Mendieta Hernández · Santiago Baquero Villa

## La pregunta de fondo

La conciliación volumétrica de PetroAndes parece candidata natural para un agente: hay datos de varios sistemas, normas que consultar, un borrador que redactar y un aprobador humano. Nuestra conclusión es que el agente se justifica en una sola parte del proceso: la investigación de causas cuando la diferencia supera la tolerancia. Todo lo demás es integración determinista; meterle un modelo lo haría más caro, más lento y menos auditable sin hacerlo más útil.

Aplicamos el criterio de la sesión 11: si se puede dibujar el flujo completo antes de ejecutarlo, no se necesita un agente. El cálculo, la clasificación contra la tolerancia, el escalamiento, la correlación con anomalías de presión, el registro del acta y el envío al regulador ya están definidos en PRO-MED-007 v2, PRO-OPE-012 v3 y RES-ANH-0471. La investigación no: si la diferencia coincide con una orden de trabajo abierta en una válvula del tramo, el siguiente paso es leer sus observaciones; si coincide con una verificación de medidor, revisar su factor; si no coincide con nada, consultar el inventario de línea y las purgas. El camino depende de cada hallazgo. Ese es el peldaño de agente en la escalera de autonomía, y es el único.

## Una función que decidimos no agentizar: la correlación entre presión y balance

Era tentador dejar al agente «evaluar si hay indicios de hurto». Lo descartamos por cuatro razones:

1. **La regla ya existe y es exacta.** PRO-OPE-012 v3 §3.2 define la sospecha de sustracción como la concurrencia, en la misma ventana horaria, de una anomalía de presión y una diferencia de balance superior a la tolerancia vigente. Es una unión temporal entre dos flujos publicados en la DMZ; se resuelve con una consulta sobre los dos flujos.
2. **Las consecuencias son desproporcionadas.** Una sospecha activa PRO-SEG-015, con reporte a Seguridad Física y Operaciones en 2 horas y a la autoridad competente en 24. Un falso positivo moviliza a la autoridad; un falso negativo deja un hurto sin reportar. Ninguno puede depender de que un modelo probabilístico evalúe distinto en dos ejecuciones.
3. **Es condición de entrada al agente, no su tarea.** Si hay sospecha, el caso sale de la conciliación y pasa a Seguridad Física: lo que corresponde es preservar la evidencia (PRO-SEG-015 §5), no que el agente la interprete.
4. **Es auditable.** Ante el regulador, «la regla 3.2 se cumplió a las 14:05 con estos dos eventos» es una explicación válida; «el modelo estimó probable un hurto» no lo es.

Por las mismas razones no agentizamos el cálculo de la diferencia (el modelo no hace aritmética regulatoria; la cifra oficial la produce el sistema de balance y el agente solo la lee) ni el envío al regulador (no existe como herramienta: lo ejecuta Cumplimiento).

## Lo que nos enseñó el Escenario A sobre esta decisión

Construimos el servicio documental con composición extractiva, sin agente ni generador, y lo medimos. Tres hallazgos informan el Escenario B:

- **El control determinista funcionó donde importaba.** Cero documentos derogados recuperados (sin filtro entrarían 31 en 19 casos). Ninguna respuesta en los 53 casos contuvo un valor derogado, incluidas las trampas de cifras cercanas (1.100, 1.200, 1.240 y 1.250 psi); solo una (V04) devolvió el plazo de otra fila de la tabla correcta. Eso lo garantiza un predicado dentro de la consulta a Qdrant.
- **El costo de no tener modelo fue la rigidez ante paráfrasis, y lo resolvimos sin subir al peldaño generativo.** Cinco de los seis fallos iniciales fueron negativas de más: tres ante jerga operativa («meterle mano», «apagada», «revisar en sitio») y dos porque la palabra de la pregunta no era la del documento («cerrar» frente a «cierre»). Comparamos tres alternativas (ADR-008):
  - Ganó un clasificador local (`bge-reranker-v2-m3`) que puntúa si una frase responde sin generar texto: rescató esas cinco negativas de referencia.
  - Descartamos el LLM local que reescribía la pregunta: alteró el sentido del 17–20 % de las consultas y no aportó nada encima del clasificador.
  - En el Escenario B aplicamos la misma regla: modelo para explorar texto, nunca para tocar las cifras.
- **El escáner de inyección se evadió; la contención aguantó.** Una paráfrasis del anexo envenenado evadió el escáner léxico y llegó a la respuesta como texto citado. Nada la ejecutó, porque la composición es extractiva y las herramientas son de solo lectura, pero un consumidor con herramientas de escritura sí podría obedecerla. Por eso el Escenario B aplica la Regla de Dos: mientras el agente lee texto no confiable, no tiene herramientas con efectos externos; toda escritura ocurre en nodos deterministas tras la aprobación humana.

## Cuándo convendría más autonomía, y cuándo menos

Más autonomía tendría sentido si el volumen de casos superara la capacidad de revisión en tres días hábiles; aun así, primero mejoraríamos la tarjeta de decisión antes que eliminar la aprobación humana sobre un acta con efecto regulatorio. Menos autonomía convendría si el piloto en sombra muestra que el agente sigue casi siempre las mismas tres consultas: en ese caso bastaría un *workflow aumentado* fijo, evitando el costo de evaluar trayectorias abiertas.

## Límites que reconocemos

- En los 23 casos nuevos de validación, la estrategia elegida (A2) arroja 22 % de desviación (18/23) y **no cumple el SLO agregado de ≤ 10 %**. Sin embargo, el desglose muestra 0 % de respuestas indebidas (el error peligroso), 9 % con otra frase de la fuente correcta (2 casos; en uno, V04, la frase es el plazo de otra fila y, con una etiqueta más estricta, contaría como indebida) y 13 % de negativas de más (3 casos). En la ronda final sacrificamos un acierto (de 19/23 a 18/23) para tener una respuesta indebida menos. Esto nos enseñó que un SLO agregado mezcla errores de gravedad incompatible; para la siguiente versión proponemos SLO por tipo (0 % indebidas, ≤ 10 % otra frase, ≤ 20 % negativas). Dos reglas de A2 se ajustaron viendo casos de ambos conjuntos, por lo que falta un tercer conjunto ciego construido con las áreas emisoras.
- Las certificaciones de vigencia del prototipo son simuladas: mientras no exista el registro único que ordena ACTA-CTO-2025-11, persiste la incertidumbre organizacional sobre qué manual rige.
- El mayor riesgo del Escenario B es humano: que la aprobación se vuelva un sello de goma. Por eso fijamos un tiempo medio de aprobación < 15 segundos como criterio de intervención.
