# ADR-001 · Motor vectorial dedicado (Qdrant) frente a extensión vectorial de un motor existente

- **Estado:** aceptada · **Fecha:** 2026-11-17 · **Decide:** equipo de arquitectura (Grupo 3)
- **Contexto en el curso:** sesión 10, «Motor dedicado o extensión de la base existente».

## Contexto

El índice tiene que guardar, por fragmento, un vector denso, un vector léxico (BM25) y unos veinte metadatos de gobierno, y tiene que aplicar el filtro de vigencia **dentro** de la búsqueda, no después. El corpus de hoy es pequeño (19 documentos, 92 fragmentos), pero el caso de PetroAndes habla de décadas de material documental y de cinco cadenas de valor. El enunciado limita la elección a una base vectorial de código abierto (Chroma o Qdrant).

## Alternativas

| Criterio | Qdrant (dedicado) | Chroma (dedicado, embebido) | pgvector sobre PostgreSQL (extensión) |
|---|---|---|---|
| Filtro por metadatos durante la búsqueda | Sí: el filtro se evalúa dentro del índice HNSW (filtrable) y en cada `prefetch` | Sí, con `where`; sin índices de payload tipados | Sí, con `WHERE`; el planificador puede filtrar antes o después según estadísticas |
| Búsqueda híbrida en una sola consulta | Sí: vector denso + vector disperso con fusión RRF nativa (`query_points` con `prefetch`) | No nativa: hay que fusionar fuera | Posible con `tsvector` + SQL de fusión escrito a mano |
| Rangos de fechas (vigencia temporal) | Sí, `Range` sobre enteros | Limitado | Sí |
| Modo embebido para el prototipo | Sí (`QdrantClient(path=…)`), mismo API que el servidor | Sí | No: requiere un servidor PostgreSQL |
| Operación en producción | Una pieza más que administrar | Una pieza más, menos madura en HA | Hereda respaldos, seguridad y HA del PostgreSQL que ya exista |
| Gobierno de permisos | Claves de API por colección; hay que integrarlo | Mínimo | Hereda roles y RLS del motor |

## Decisión

**Qdrant**, en modo embebido para el prototipo y en modo servidor (`QDRANT_URL`) en producción, con una colección por versión de modelo de embeddings (ver ADR-004).

La razón decisiva no es la escala sino la **posición del filtro**: Qdrant aplica el mismo `Filter` de vigencia a la búsqueda densa y a la léxica, y fusiona ambas en una sola llamada. Con eso el control del Message Filter queda en un solo lugar del código (`recuperacion.filtro_vigencia`) y es imposible que una de las dos búsquedas lo olvide.

## Consecuencias

- Positivas: filtro e hibridez en el motor; mismo código del prototipo a producción; payload con índices tipados.
- Negativas: una pieza de infraestructura nueva para el equipo de plataforma, con sus respaldos y su modelo de permisos. Si PetroAndes ya opera PostgreSQL con alta disponibilidad y el volumen se queda en miles de documentos, **pgvector sería una alternativa razonable**: el veredicto de la sesión 10 es de contexto.
- Revisión: si el corpus de producción se queda por debajo de ~100.000 fragmentos y el equipo no puede operar otra base de datos, reabrir esta decisión a favor de pgvector.
