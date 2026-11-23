# ADR-004 · Modelo de embeddings como dependencia versionada, con procedimiento de reindexación

- **Estado:** aceptada · **Fecha:** 2026-11-17

## Contexto

Vectores producidos por modelos distintos no son comparables (cambiar el modelo de embeddings obliga a migrar el índice). El corpus está en español, con terminología técnica, cifras y códigos. Además, las pruebas automáticas y la integración continua necesitan un modo que no descargue modelos de Hugging Face.

## Alternativas consideradas

| Modelo | Idioma | Dimensión | Cómo se obtiene | Observación |
|---|---|---|---|---|
| `intfloat/multilingual-e5-small` | Multilingüe, entrenado para recuperación | 384 | Hugging Face | **Por defecto en producción**: pequeño, corre en CPU, prefijos `query:`/`passage:` |
| `paraphrase-multilingual-MiniLM-L12-v2` | Multilingüe, de paráfrasis | 384 | Hugging Face | Alternativa equivalente |
| API de embeddings de un proveedor | Multilingüe | 1.024–3.072 | Servicio externo | Saca el texto del corpus fuera de PetroAndes; costo por uso; descartado por residencia de datos |
| `es_core_news_md` de spaCy, promedio ponderado por IDF | Español | 300 | PyPI / GitHub | **Alterno sin Hugging Face**: vectores de palabra, no de frase; débil con paráfrasis |

## Decisión

1. El modelo se declara como **especificación** (`PETROANDES_EMBEDDINGS`, p. ej. `st:intfloat/multilingual-e5-small`) y el índice guarda su **huella**: proveedor, modelo, revisión, dimensión y, para el alterno, el hash de la tabla IDF congelada. La revisión es el **commit** del modelo que se cargó, no la rama: huella real del índice vigente, `st:intfloat/multilingual-e5-small@614241f622f53c4eeff9890bdc4f31cfecc418b3:384`; del alterno, `spacy:es_core_news_md@3.8.0:300:idf-010c0c930053`.
2. La colección de Qdrant lleva en el nombre el hash de la huella: `corpus_petroandes__85f8fe1f65` para e5 con el commit fijado; el alterno de spaCy usa otra colección.
3. Al abrir el índice, si la especificación configurada o la huella del modelo cargado no coinciden con las del manifiesto, **el sistema se niega a buscar** (`ModeloIncompatible`). No hay degradación silenciosa.
4. La especificación admite fijar el commit (`st:intfloat/multilingual-e5-small@614241f…`); sin él, la huella registra el commit de la copia local, y si el repositorio del modelo cambia, el índice deja de coincidir y se niega a buscar. Lo mismo vale para el decisor de ADR-008 (`PETROANDES_DECISOR=crossencoder:BAAI/bge-reranker-v2-m3@<commit>`).
5. Hasta el 19 de noviembre la huella guardaba la rama (`@main`), que no basta para una dependencia versionada: una rama se mueve. Se corrigió el 22 de noviembre y se reindexó. Los resultados de referencia se midieron con e5; los del alterno de spaCy se conservan como línea base.

## Procedimiento de reindexación (si mañana cambia el modelo)

1. Registrar el nuevo modelo (nombre, revisión, licencia) en el catálogo de dependencias y abrir el cambio.
2. Construir una **colección nueva** con el nuevo modelo (`petroandes-docs ingestar` con la nueva especificación). La colección anterior sigue sirviendo.
3. Correr el arnés de evaluación contra la colección nueva y compararlo con la línea base: acierto@5, desviación, rechazo correcto y derogados recuperados. Recalibrar el umbral de cobertura si hace falta.
4. Si cumple los SLO, cambiar el manifiesto (o el alias de colección en el servidor Qdrant) en un solo paso; si no, descartar la colección nueva.
5. Conservar la colección anterior durante un ciclo de corte (un mes) para reversión; luego borrarla.

Costo con el corpus actual: segundos. Con un corpus real de decenas de miles de páginas, horas de cómputo en CPU: por eso se hace en paralelo y no en caliente.

## Consecuencias

- Un cambio de modelo no puede pasar inadvertido ni mezclar vectores.
- El alterno de spaCy hace que la parte semántica sea débil (acierto@5 semántico 62 %); con e5 sube a 100 %. Las negativas ante paráfrasis no cambiaron entre modelos: dependen de la cobertura léxica de la composición, no de los embeddings.
