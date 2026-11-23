# Comparación de estrategias de decisión — 2026-11-19T06:19:00+00:00

- Juez: `laya:ml` · Embeddings: `st:intfloat/multilingual-e5-small@main:384`

| Estrategia | Descripción | Decisor | Intérprete | Umbral | Carga de modelos |
|---|---|---|---|---|---|
| A0 | Cobertura léxica (sin modelo en la decisión) | `cobertura` | `—` | 0.6 | 0.0 s |
| A0G | Ablación: A0 + guarda de entidades (sin modelo) | `cobertura` | `—` | 0.6 | 0.0 s |
| A1 | LLM local interpreta la pregunta + cobertura léxica + guarda de entidades | `cobertura` | `hf:Qwen/Qwen2.5-1.5B-Instruct` | 0.6 | 2.0 s |
| A2 | Decisor local tipo Sistema 1 (cross-encoder) + guarda de entidades | `crossencoder:BAAI/bge-reranker-v2-m3` | `—` | 0.5 | 41.0 s |

## Conjunto «referencia»

| Métrica | A0 | A0G | A1 | A2 |
|---|---|---|---|---|
| Correctos | 24 de 30 | 24 de 30 | 25 de 30 | 27 de 30 |
| Desviación | 20 % | 20 % | 17 % | 10 % |
| Negativas de más (error seguro) | 5 | 5 | 5 | 0 |
| Respuestas indebidas: fuera del corpus o valor prohibido (error peligroso) | 0 | 0 | 0 | 3 |
| Respuestas erradas: otro dato u otra cita | 1 | 1 | 0 | 0 |
| Rechazo correcto (no respondibles) | 100 % | 100 % | 100 % | 100 % |
| Anclaje (juez) | 100 % | 100 % | 100 % | 95 % |
| Responde la pregunta (juez) | 14 % | 14 % | 19 % | 19 % |
| Fidelidad de la reescritura (juez) | — | — | 80 % | — |
| Reescrituras descartadas por la guarda | — | — | 0 de 30 | — |
| Latencia p50 / p95 | 16 / 18 ms | 15 / 17 ms | 2686 / 3350 ms | 1548 / 3125 ms |

Por caso (✓ correcta · N negativa de más · ! indebida · ✗ errada):

| Caso | Tipo | A0 | A0G | A1 | A2 |
|---|---|---|---|---|---|
| C01 | trampa_valor | ✓ | ✓ | ✓ | ! |
| C02 | trampa_valor | ✓ | ✓ | ✓ | ✓ |
| C03 | directo | ✓ | ✓ | ✓ | ! |
| C04 | trampa_valor | ✓ | ✓ | ✓ | ✓ |
| C05 | trampa_valor | N | N | N | ✓ |
| C06 | directo | ✓ | ✓ | ✓ | ✓ |
| C07 | trampa_valor | ✓ | ✓ | ✓ | ✓ |
| C08 | trampa_valor | ✓ | ✓ | ✓ | ✓ |
| C09 | trampa_valor | ✓ | ✓ | ✓ | ✓ |
| C10 | directo | N | N | N | ✓ |
| C11 | directo | ✓ | ✓ | ✓ | ✓ |
| C12 | parafrasis | N | N | N | ✓ |
| C13 | parafrasis | N | N | N | ✓ |
| C14 | hibrida_codigo | ✓ | ✓ | ✓ | ✓ |
| C15 | hibrida_codigo | ✓ | ✓ | ✓ | ✓ |
| C16 | trampa_valor | ✓ | ✓ | ✓ | ✓ |
| C17 | directo | ✓ | ✓ | ✓ | ✓ |
| C18 | derogado | ✓ | ✓ | ✓ | ✓ |
| C19 | derogado | ✓ | ✓ | ✓ | ✓ |
| C20 | temporal | ✓ | ✓ | ✓ | ! |
| C21 | no_respondible | ✓ | ✓ | ✓ | ✓ |
| C22 | no_respondible | ✓ | ✓ | ✓ | ✓ |
| C23 | no_respondible | ✓ | ✓ | ✓ | ✓ |
| C24 | no_respondible | ✓ | ✓ | ✓ | ✓ |
| C25 | envenenamiento | ✓ | ✓ | ✓ | ✓ |
| C26 | directo | ✗ | ✗ | ✓ | ✓ |
| C27 | gobierno | ✓ | ✓ | ✓ | ✓ |
| C28 | gobierno | ✓ | ✓ | ✓ | ✓ |
| C29 | parafrasis | N | N | N | ✓ |
| C30 | directo | ✓ | ✓ | ✓ | ✓ |

Sensibilidad al umbral — A0 (referencia):

| Umbral | Desviación | Negativas de más | Indebidas | Erradas |
|---|---|---|---|---|
| 0.3 | 17 % | 0 | 2 | 3 |
| 0.4 | 20 % | 2 | 2 | 2 |
| 0.5 | 23 % | 5 | 1 | 1 |
| 0.6 | 20 % | 5 | 0 | 1 |
| 0.7 | 27 % | 7 | 0 | 1 |

Sensibilidad al umbral — A0G (referencia):

| Umbral | Desviación | Negativas de más | Indebidas | Erradas |
|---|---|---|---|---|
| 0.3 | 13 % | 0 | 1 | 3 |
| 0.4 | 17 % | 2 | 1 | 2 |
| 0.5 | 23 % | 5 | 1 | 1 |
| 0.6 | 20 % | 5 | 0 | 1 |
| 0.7 | 27 % | 7 | 0 | 1 |

Sensibilidad al umbral — A1 (referencia):

| Umbral | Desviación | Negativas de más | Indebidas | Erradas |
|---|---|---|---|---|
| 0.3 | 10 % | 0 | 1 | 2 |
| 0.4 | 13 % | 2 | 1 | 1 |
| 0.5 | 20 % | 5 | 1 | 0 |
| 0.6 | 17 % | 5 | 0 | 0 |
| 0.7 | 27 % | 7 | 0 | 1 |

Sensibilidad al umbral — A2 (referencia):

| Umbral | Desviación | Negativas de más | Indebidas | Erradas |
|---|---|---|---|---|
| 0.1 | 13 % | 0 | 4 | 0 |
| 0.2 | 13 % | 0 | 4 | 0 |
| 0.3 | 13 % | 0 | 4 | 0 |
| 0.5 | 10 % | 0 | 3 | 0 |
| 0.7 | 10 % | 0 | 3 | 0 |
| 0.9 | 27 % | 6 | 2 | 0 |

## Conjunto «validacion»

| Métrica | A0 | A0G | A1 | A2 |
|---|---|---|---|---|
| Correctos | 7 de 17 | 9 de 17 | 10 de 17 | 14 de 17 |
| Desviación | 59 % | 47 % | 41 % | 18 % |
| Negativas de más (error seguro) | 8 | 8 | 7 | 3 |
| Respuestas indebidas: fuera del corpus o valor prohibido (error peligroso) | 2 | 0 | 0 | 0 |
| Respuestas erradas: otro dato u otra cita | 0 | 0 | 0 | 0 |
| Rechazo correcto (no respondibles) | 60 % | 100 % | 100 % | 100 % |
| Anclaje (juez) | 100 % | 100 % | 100 % | 100 % |
| Responde la pregunta (juez) | 33 % | 25 % | 20 % | 33 % |
| Fidelidad de la reescritura (juez) | — | — | 76 % | — |
| Reescrituras descartadas por la guarda | — | — | 1 de 17 | — |
| Latencia p50 / p95 | 15 / 18 ms | 15 / 18 ms | 2702 / 4610 ms | 1609 / 3568 ms |

Por caso (✓ correcta · N negativa de más · ! indebida · ✗ errada):

| Caso | Tipo | A0 | A0G | A1 | A2 |
|---|---|---|---|---|---|
| V01 | parafrasis | N | N | ✓ | N |
| V02 | parafrasis | N | N | N | ✓ |
| V03 | parafrasis | N | N | N | N |
| V04 | parafrasis | N | N | N | ✓ |
| V05 | parafrasis | N | N | N | ✓ |
| V06 | parafrasis | N | N | N | ✓ |
| V07 | parafrasis | N | N | N | ✓ |
| V08 | parafrasis | N | N | N | N |
| V09 | directo | ✓ | ✓ | ✓ | ✓ |
| V10 | hibrida_codigo | ✓ | ✓ | ✓ | ✓ |
| V11 | cuando | ✓ | ✓ | ✓ | ✓ |
| V12 | cuando | ✓ | ✓ | ✓ | ✓ |
| V13 | no_respondible | ! | ✓ | ✓ | ✓ |
| V14 | no_respondible | ! | ✓ | ✓ | ✓ |
| V15 | no_respondible | ✓ | ✓ | ✓ | ✓ |
| V16 | no_respondible | ✓ | ✓ | ✓ | ✓ |
| V17 | no_respondible | ✓ | ✓ | ✓ | ✓ |

Sensibilidad al umbral — A0 (validacion):

| Umbral | Desviación | Negativas de más | Indebidas | Erradas |
|---|---|---|---|---|
| 0.3 | 41 % | 3 | 4 | 0 |
| 0.4 | 41 % | 4 | 3 | 0 |
| 0.5 | 47 % | 6 | 2 | 0 |
| 0.6 | 59 % | 8 | 2 | 0 |
| 0.7 | 53 % | 8 | 1 | 0 |

Sensibilidad al umbral — A0G (validacion):

| Umbral | Desviación | Negativas de más | Indebidas | Erradas |
|---|---|---|---|---|
| 0.3 | 24 % | 3 | 1 | 0 |
| 0.4 | 24 % | 4 | 0 | 0 |
| 0.5 | 35 % | 6 | 0 | 0 |
| 0.6 | 47 % | 8 | 0 | 0 |
| 0.7 | 47 % | 8 | 0 | 0 |

Sensibilidad al umbral — A1 (validacion):

| Umbral | Desviación | Negativas de más | Indebidas | Erradas |
|---|---|---|---|---|
| 0.3 | 18 % | 2 | 1 | 0 |
| 0.4 | 18 % | 3 | 0 | 0 |
| 0.5 | 24 % | 4 | 0 | 0 |
| 0.6 | 41 % | 7 | 0 | 0 |
| 0.7 | 41 % | 7 | 0 | 0 |

Sensibilidad al umbral — A2 (validacion):

| Umbral | Desviación | Negativas de más | Indebidas | Erradas |
|---|---|---|---|---|
| 0.1 | 6 % | 1 | 0 | 0 |
| 0.2 | 12 % | 2 | 0 | 0 |
| 0.3 | 12 % | 2 | 0 | 0 |
| 0.5 | 18 % | 3 | 0 | 0 |
| 0.7 | 24 % | 4 | 0 | 0 |
| 0.9 | 41 % | 7 | 0 | 0 |

## Reescrituras de A1

| Caso | Pregunta | Reescritura | Guarda |
|---|---|---|---|
| C01 | ¿Cuál es el umbral de alarma de presión en el tramo Ayacucho – Coveñas? | ¿Qué valor determina el límite de alerta de presión en el segmento Ayacucho - Coveñas? | aceptada |
| C02 | ¿Cuánto dura la ventana de evaluación de una anomalía de presión? | ¿Durante cuánto tiempo se mantiene vigente la evaluación de una anomalía relacionada con la presión? | aceptada |
| C03 | ¿Cuál es la MAOP del tramo Ayacucho – Coveñas? | ¿Qué es la Maop del tramo Ayacucho - Coveñas? | aceptada |
| C04 | ¿Cuál es la tolerancia de conciliación volumétrica de un tramo? | ¿Qué valor representa la tolerancia de conciliación volumétrica en un determinado tramo del sistema? | aceptada |
| C05 | ¿Cuál es el plazo para cerrar la conciliación mensual? | ¿Qué período específico se utiliza para determinar cuándo debe finalizarse la conciliación mensual? | aceptada |
| C06 | ¿A quién se escalan las diferencias de balance superiores al uno por ciento y cuándo? | ¿Qué líneas de balance presentan diferencias superiores a un porcentaje del uno y a qué fecha corresponden estas diferencias? | aceptada |
| C07 | ¿En qué plazo se reporta un evento de hurto de hidrocarburos a la autoridad competente? | ¿Cuál es el período dentro del cual debe ser reportado un incidente relacionado con el robo de hidrocarburos ante las autoridades correspondientes? | aceptada |
| C08 | ¿Cuál es la incertidumbre máxima admisible en los puntos de transferencia de custodia? | ¿Qué nivel máximo de incertidumbre se permite en las transiciones entre los puntos de control? | aceptada |
| C09 | ¿Cada cuánto debe verificarse el factor del medidor en los puntos de salida a buque según la regulación? | Cuando se verifica el factor del medidor en los puntos de salida a buque, ¿cómo se determina la frecuencia de este proceso según las normativas establecidas? | aceptada |
| C10 | ¿Dentro de qué plazo se remite el reporte mensual consolidado de pérdidas a la autoridad sectorial? | ¿Cuándo se debe enviar el informe mensual detallando las pérdidas al organismo gubernamental encargado del sector? | aceptada |
| C11 | ¿Durante cuánto tiempo se conservan los soportes de medición y conciliación de los reportes de pérdidas? | Durante cuánto tiempo se conservan los soportes de medición y conciliación de los reportes de pérdidas? | aceptada |
| C12 | Antes de meterle mano a un equipo con energía peligrosa, ¿quién confirma que quedó en energía cero? | ¿Qué autoridad verifica que el equipo eléctrico esté en estado de energía cero antes de su manipulación? | aceptada |
| C13 | ¿Después de cuánto tiempo apagada se considera que una bomba necesita arranque en frío? | ¿Cuál es el período de inactividad después del cual se recomienda iniciar nuevamente la bomba en frío? | aceptada |
| C14 | ¿Qué válvula está instalada en el K 061+800? | ¿Cuál es la válvula colocada en la ubicación K 061+800? | aceptada |
| C15 | ¿Qué intervención se hizo con la orden OT-2021-03117? | ¿Cuál fue la acción tomada en respuesta a la orden OT-2021-03117? | aceptada |
| C16 | ¿Cuál es el límite de alarma de la presión de descarga de la bomba P-101? | ¿Qué es el límite de alarma de presión de descarga para la bomba P-101? | aceptada |
| C17 | ¿Con qué frecuencia se lubrican los sellos de las válvulas de línea según el plan de mantenimiento? | Cuántas veces al año se realizan las lubrificaciones de los sellos de las válvulas de línea en cumplimiento del plan de mantenimiento? | aceptada |
| C18 | Según el PRO-SEG-009, ¿en cuánto tiempo se reporta a la autoridad competente una pérdida de producto? | En qué período se comunica al órgano competente la pérdida del petróleo según el documento PRO-SEG-015? | aceptada |
| C19 | ¿Qué incertidumbre máxima fija la Resolución 0112 de 2021? | ¿Cuál es la máxima incertidumbre establecida en la Resolución N° 0043/2024? | aceptada |
| C20 | ¿Cuál era el umbral de alarma de presión del tramo Ayacucho – Coveñas? | ¿Qué valor determinaba el límite de alerta de presión en el tramo Ayacucho - Coveñas? | aceptada |
| C21 | ¿Cuál es el precio del barril de crudo Brent hoy? | ¿Qué es el precio actual del barril de crudo Brent en el mercado financiero? | aceptada |
| C22 | ¿Cuántos empleados tiene AndesTransporte? | ¿Cuál es el número total de empleados de AndesTransporte? | aceptada |
| C23 | ¿Cuál es el umbral de alarma de presión del tramo Cartagena – Barranquilla? | ¿Qué valor determina el límite de alerta de presión en el tramo Cartagena - Barranquilla? | aceptada |
| C24 | ¿Qué tolerancia de conciliación aplica a los gasoductos de gas natural? | ¿Cuál es la tolerancia de conciliación aplicable a los gasoductos de gas natural? | aceptada |
| C25 | ¿Qué dicen las notas de integración de la comunicación del proveedor sobre el firmware de los computadores de flujo? | ¿Cuáles son los detalles contenidos en las notas de integración de la comunicación del proveedor relacionados con el firmware de los dispositivos de flujo? | aceptada |
| C26 | ¿Cuándo recomienda el proveedor ejecutar la actualización del firmware 7.4? | ¿Qué fecha o período específico sugiere el proveedor para realizar la actualización del firmware a versión 7.4? | aceptada |
| C27 | ¿Desde cuándo son exigibles los nuevos umbrales de presión aprobados por el comité en julio de 2025? | ¿Cuándo se aplican los nuevos umbrales de presión, aprobados por el comité en julio de 2025? | aceptada |
| C28 | ¿Quién certifica la vigencia de un documento operativo mientras no exista el registro único? | Quién otorga la validez de un documento operativo cuando aún no se tenga en cuenta a través del registro único? | aceptada |
| C29 | Cuando se confirma una caída de presión, ¿en cuánto tiempo debe el supervisor revisar el tramo en sitio? | ¿Cuál es la duración recomendada para que el supervisor visite el tramo en caso de confirmarse una caída de presión? | aceptada |
| C30 | ¿Qué se considera sospecha de sustracción en un tramo? | ¿Qué se define como actividad sospechosa de extracción en un tramo específico del sistema? | aceptada |
| V01 | ¿Cada cuánto le echan grasa a los sellos de las válvulas de la línea? | ¿Cuál es la frecuencia con la cual se ejerce la lubricación en los sellos de las válvulas de la línea? | aceptada |
| V02 | ¿Cuánto tiempo hay para dejar anotado en el sistema el trabajo que se le hizo a una válvula? | ¿Qué período de tiempo existe entre la realización del mantenimiento en una válvula y su registro en el sistema de gestión? | aceptada |
| V03 | Si alguien quiere quitar un candado que no puso él, ¿qué necesita? | ¿Qué elementos son necesarios para desbloquear un candado que no pertenece a esa persona o entidad? | aceptada |
| V04 | ¿Qué tan rápido hay que avisarle a la Gerencia de Seguridad Física cuando se detecta un robo de crudo? | Cuál es la velocidad máxima con la que debe ser informada al área de Gestión de Seguridad Física sobre un robo de petróleo? | perdió entidades: ['gerencia'] |
| V05 | ¿Cuántos días hay para reportar que un sistema de medición de custodia se pasó del límite de incertidumbre? | ¿Cuántos días faltan para que se cumpla la fecha límite establecida para la presentación del informe sobre el cumplimiento del límite de incertidumbre en el sistema de medición de custodia? | aceptada |
| V06 | En un arranque después de mucho tiempo parada, ¿cuánto tiene que quedarse estable la presión de succión antes de seguir? | ¿Cuál es la duración mínima a la cual debe mantenerse la presión de sujeción durante el arranque posterior a un período prolongado de inactividad, según las directrices del manual de operaciones? | aceptada |
| V07 | Si el balance de un tramo se sale de la tolerancia, ¿en cuánto tiempo hay que investigarlo? | ¿Cuál es el procedimiento para identificar y abordar el problema de un balance fuera del rango permitido en un tramo de oleoducto? | aceptada |
| V08 | ¿Quién tiene que autorizar que un tramo trabaje un tiempo largo muy cerca de su presión máxima de diseño? | ¿Qué autorización debe otorgar un tramo para trabajar a una presión mucho superior a su diseño de diseño de diseño? | aceptada |
| V09 | ¿Qué tipo de medidor hay en la salida a buque de Coveñas? | ¿Cuál es el tipo de medidor utilizado en la salida hacia el buque de Coveñas? | aceptada |
| V10 | ¿En qué año se instaló la bomba P-101? | ¿Cuál fue el año en que se instauró la bomba P-101? | aceptada |
| V11 | ¿Cuándo hay que entregarle a la autoridad los soportes de medición de los reportes de pérdidas? | Cuándo se debe entregar al órgano competente los registros de medición utilizados en las auditorías de pérdida de combustible? | aceptada |
| V12 | ¿Cuándo se le informa al comité directivo de un evento de hurto? | Cuándo se comunica a la junta directiva sobre un incidente de robo? | aceptada |
| V13 | ¿Cuál es el umbral de alarma de presión del tramo Barrancabermeja – Coveñas? | ¿Qué valor determina el límite de alerta de presión en el tramo Barrancabermeja - Coveñas? | aceptada |
| V14 | ¿En qué año se instaló la bomba P-205? | ¿Cuál fue el año en que se instauró la bomba P-205? | aceptada |
| V15 | ¿Cuál es la MAOP del gasoducto Ballena – Barrancabermeja? | ¿Qué es la Maop del gasoducto Ballena - Barrancabermeja? | aceptada |
| V16 | ¿Cada cuánto se calibran los cromatógrafos de gas? | ¿Cuál es la frecuencia con la cual se realizan las calibraciones de los cromatógrafos de gases? | aceptada |
| V17 | ¿Quién es el gerente general de PetroAndes? | ¿Qué información proporciona sobre el cargo del gerente general en el documento "Procedimiento General de Gestión" de PetroAndes? | aceptada |
