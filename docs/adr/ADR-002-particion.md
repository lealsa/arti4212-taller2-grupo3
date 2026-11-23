# ADR-002 · Estrategia de partición: por sección del documento, con filas de tabla autocontenidas

- **Estado:** aceptada · **Fecha:** 2026-11-17

## Contexto

La partición es un Splitter (nota RAG–EIP §3.1): su riesgo es perder el contexto que daba el documento completo. El corpus tiene secciones numeradas cortas (100 a 1.000 caracteres), artículos en las resoluciones y apartados con nombre en actas y comunicaciones, y casi todos los valores operativos están en **tablas**: umbrales por tramo, MAOP, tolerancias, plazos de reporte, válvulas, órdenes de trabajo. La extracción ingenua de una tabla del PDF parte las celdas en varias líneas (en PRO-OPE-012 v3, «Barrancabermeja –» queda en una línea y «Ayacucho» en la siguiente, lejos de su umbral).

## Alternativas

1. **Ventana fija de caracteres con solapamiento** (p. ej. 500/100). Simple, independiente del formato. Corta tablas por la mitad y separa el valor de su tramo: el fragmento sigue siendo legible, pero deja de ser verdadero.
2. **Por página.** Todas las páginas del corpus son una sola: equivale a un fragmento por documento, que mezcla secciones y diluye la recuperación.
3. **Por sección del documento, con tablas normalizadas a filas autocontenidas** (elegida).
4. **Partición semántica** (cortar donde cambia el tema según embeddings). Costosa, no determinista y depende del modelo, que es justamente la dependencia que queremos poder cambiar.

## Decisión

- Unidad de partición: la **sección** reconocida por la tipografía del PDF (título en negrita), que en el corpus coincide con los numerales (1., 2.), los artículos (Art. 1) y los apartados con nombre (Asunto, Anexo).
- Dentro de la sección, el texto se guarda como **unidades**: cláusulas (3.1, 3.2), viñetas y **filas de tabla convertidas a «columna: valor»** (`Tramo: Ayacucho – Coveñas; Umbral de alarma (psi): 1.100; Ventana de evaluación: 15 minutos`). La unidad es lo que la composición cita (ADR-003).
- Cada fragmento lleva una cabecera de contexto para indexar (título del documento, código, versión y título de sección), de modo que la fila suelta sigue diciendo de qué documento viene.
- Solo si una sección supera 2.500 caracteres se divide, y siempre por unidades completas, nunca a mitad de una.
- El tamaño máximo se declara por clase en el contrato del corpus, no como un número universal.

## Consecuencias

- Una fila de tabla recuperada sola es verdadera por sí misma; la prueba `test_filas_de_tabla_autocontenidas` lo verifica.
- La partición depende de que el PDF marque los títulos en negrita. Si un documento real no lo hace, el extractor cae al reconocimiento por patrones de texto (numeral, «Artículo N», etiquetas conocidas); esa ruta está menos probada. Es un riesgo declarado.
- Las secciones largas de documentos reales (manuales de 80 páginas) necesitarán una segunda regla por subtítulo; el contrato ya prevé el límite por clase.
