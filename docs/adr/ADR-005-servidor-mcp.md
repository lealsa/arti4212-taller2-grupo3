# ADR-005 · Servidor MCP: cuatro herramientas de solo lectura, recursos de contexto y transporte stdio

- **Estado:** aceptada · **Fecha:** 2026-11-17 · **Protocolo:** MCP revisión 2026-07-28 (SDK de Python `mcp` 2.3)

## Contexto

La recuperación tiene que exponerse como herramientas de un protocolo estándar con contrato completo (enunciado §3.2), y el Escenario B la va a consumir desde un agente que también lee contenido no confiable. La sesión 12 distingue tools (las decide el modelo), resources (las decide la aplicación) y prompts (los elige la persona).

## Decisión

**Herramientas** (todas `readOnlyHint=true`, `idempotentHint=true`, `openWorldHint=false`):

| Herramienta | Por qué es tool |
|---|---|
| `buscar_documentos` | El modelo decide qué buscar según lo que va encontrando |
| `obtener_fragmento` | El modelo verifica una cita concreta (Claim Check) |
| `responder_consulta` | Atajo para consumidores que no son agentes; la composición es extractiva y un clasificador local decide si una frase responde (ADR-008) |
| `consultar_vigencia` | El modelo necesita saber si puede citar un documento que le nombraron |

**Recursos** (los incluye la aplicación, no el modelo): contrato del corpus, registro de vigencia y catálogo de documentos.

**Sin prompts**: la plantilla «investigar una diferencia» pertenece al host del Escenario B, no a este servidor.

Reglas del contrato:

- Entradas validadas por JSON Schema en el servidor (longitudes, `k` entre 1 y 10, patrón de código y de fecha); lector tolerante para versión y sección enviadas como número.
- Salidas estructuradas (`outputSchema`) con la cita lista para usar y el estado de vigencia de cada fragmento.
- Errores con código estable y dato para corregir el rumbo: `DOCUMENTO_DEROGADO` trae `reemplazado_por`; `SECCION_NO_ENCONTRADA` trae `secciones_validas`; `FRAGMENTO_EN_CUARENTENA` no trae el texto.
- Indicaciones de caché de la revisión 2026-07-28: `tools/list` y `resources/list` con `ttlMs = 3.600.000` y `cacheScope = public` (cambian con la versión del servidor); `resources/read` con `ttlMs = 300.000` y `cacheScope = private` (el registro de vigencia cambia y no debe servirse viejo más de 5 minutos, coherente con la latencia de 15 minutos del contrato).
- Cada llamada queda en `data/auditoria.jsonl` con `traza_id`, argumentos, filtro aplicado, fragmentos devueltos, latencia y huella del modelo (Wire Tap).
- Transporte **stdio** por defecto: el servidor vive junto al host y no abre puertos. `--http` levanta Streamable HTTP en 127.0.0.1 para pruebas; en producción iría detrás del AI Gateway con OAuth (Escenario B, modelo de seguridad).

**Lo que deliberadamente no existe:** ninguna herramienta escribe, envía, ni lee otro sistema; no hay parámetro para ver un fragmento en cuarentena (la revisión humana es un comando de CLI, `auditar-fragmento`, fuera del protocolo); no hay herramienta que devuelva documentos derogados (la consulta histórica usa `fecha_referencia`, que devuelve lo que **regía** en esa fecha, no lo derogado hoy).

## Alternativas descartadas

- **Una sola herramienta `consultar(pregunta)`**: esconde la búsqueda y la verificación de citas; el agente no puede comprobar lo que cita.
- **Exponer el registro de vigencia como tool**: es contexto de solo lectura que decide la aplicación; se expone como resource, más `consultar_vigencia` para la pregunta puntual.
- **Parámetro `incluir_derogados`**: convierte un control en una opción que el modelo puede activar. Descartado.

## Verificación

MCP Inspector 2.16 en modo CLI, capturado el 22 de noviembre contra el servidor con la estrategia vigente (`eval/resultados/inspector/`, con `herramientas/capturar_inspector.py`), y pruebas con el cliente del SDK en memoria (`tests/test_seguridad_mcp_sincronizacion.py`). Una prueba verifica que el JSON Schema publicado lleve el patrón de versión y la longitud de sección: con pydantic 2.13 se perdían si el validador que acepta números iba antes que `Field`.
