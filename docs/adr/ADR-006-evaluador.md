# ADR-006 · Evaluador: laya como referencia y un juez léxico alterno para entornos sin el checkpoint

- **Estado:** aceptada · **Fecha:** 2026-11-17

## Contexto

El enunciado propone laya (NandhaKishorM/laya, Apache-2.0), con el checkpoint multilingüe: el anclaje como proposición booleana (`noul`) y la pertinencia del fragmento como elección (`choice`). Admite otro evaluador si se justifica en un ADR. laya descarga su checkpoint de Hugging Face la primera vez (`convaiinnovations/laya`, subcarpeta `multilingual`); en integración continua o en una máquina sin red ese checkpoint no está disponible.

## Decisión

El arnés (`petroandes_docs.evaluacion`) acepta dos jueces con la misma interfaz:

1. **`laya` (por defecto):** `laya.load("ml")`, el alias del checkpoint multilingüe.
   - Anclaje: `noul` con la pregunta «¿El fragmento respalda por completo la afirmación, sin que la afirmación agregue datos, cifras o conclusiones que no estén en el fragmento?»; estado `{fragmento, afirmacion}`; anclada si P(true) ≥ 0,5.
   - Pertinencia: `choice` con `pertinente | parcial | no_pertinente` sobre cada uno de los 5 primeros fragmentos.
2. **`lexico` (alterno):** anclaje por contención textual normalizada más verificación de que toda cifra de la afirmación aparece en el fragmento; pertinencia por etiqueta de oro del caso.

La **tasa de desviación no depende del juez**: se calcula con los hechos esperados y prohibidos de cada caso, que es más estricto que cualquier juez para cifras.

## Justificación del alterno

- Con composición extractiva (ADR-003), el anclaje es por construcción contención textual; un juez léxico mide exactamente esa propiedad y no puede «alucinar» un juicio.
- La pertinencia por etiqueta de oro es más estricta que un juez (solo cuenta la sección esperada), así que tiende a subestimar: un fragmento útil que no es el esperado cuenta como no pertinente. Su techo es bajo por definición: con una sola fuente esperada y k = 5, la pertinencia máxima es 20 %.
- No reemplaza a laya: es lo que permite correr el arnés en CI o en una máquina sin red, y comparar ambos jueces cuando los dos están disponibles.

## Cómo correr la referencia

```bash
pip install -e ".[laya]"
petroandes-docs evaluar --juez laya      # descarga el checkpoint multilingüe la primera vez
```

## Consecuencias

- `eval/resultados/reporte.md` es la corrida vigente (estrategia A2) con laya (`laya:ml`) y e5; `eval/resultados_A0_e5_laya/` es la corrida antes de ADR-008 y `eval/resultados_spacy_lexico/` es la corrida con el juez léxico. Por construcción (contención literal), el anclaje es 100 % en todas; laya marca 100 % en A0 y en validación, y 96 % (25/26) en A2 sobre referencia porque puntúa con 0,414 la fila de tabla literal de C02.
- Resultado del riesgo que habíamos anotado: laya puntúa bajo las filas de tabla literales («Tramo: …; Umbral …»: 0,54 en C01 y C02 con A0, y 0,414 en C02 al devolver una sola frase en A2), aunque son copia exacta del fragmento. Su pertinencia (`choice`) discrepa de las etiquetas de oro: marca «no pertinente» la fuente esperada en 11 de 27 casos. Se usa laya para el anclaje y se reporta su pertinencia sin usarla para decidir; calibrarla con ejemplos del corpus queda como trabajo futuro.
- ADR-008 agrega dos preguntas a laya: «¿la respuesta contesta lo que se pregunta?» (`noul`) y «¿la reescritura pide lo mismo que la original?» (`noul`, solo para la alternativa A1).
  - La primera también discrepa de las etiquetas de oro (puntúa bajo filas de tabla correctas), así que se reporta sin usarla para decidir.
  - La segunda detectó cambios de sentido reales (C12, C09, V17), pero dejó pasar al menos uno (C08).
- laya no se usa como decisor (ADR-008): si decide y juzga el mismo modelo, la evaluación deja de ser independiente.
