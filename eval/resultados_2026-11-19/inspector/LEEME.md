# Verificación con MCP Inspector

Salidas reales del MCP Inspector en modo CLI contra el servidor stdio (`petroandes-mcp`), capturadas el 2026-11-17.

Comando base:

    npx -y @modelcontextprotocol/inspector --cli petroandes-mcp --method tools/list

| Archivo | Qué verifica |
|---|---|
| 01_tools_list.json | Las cuatro herramientas con su contrato completo: descripción para el modelo, JSON Schema de entrada y salida y anotaciones de solo lectura. El Inspector no imprime ttlMs ni cacheScope; los verifica la prueba `test_listado_declara_ttl_y_alcance_de_cache` |
| 02_responder_consulta.json | Consulta fundamentada con cita PRO-OPE-012 v3 §3 |
| 03_buscar_documentos_codigo.json | Búsqueda por código de orden de trabajo (léxica dentro de la híbrida) |
| 04_obtener_fragmento_derogado.json | Error DOCUMENTO_DEROGADO con el documento que lo reemplaza |
| 04b_obtener_fragmento_vigente.json | Fragmento vigente por documento, versión y sección |
| 05_obtener_fragmento_cuarentena.json | Error FRAGMENTO_EN_CUARENTENA: el texto envenenado no se entrega |
| 06_responder_sin_respaldo.json | Negativa honesta: la respuesta no está en el corpus |
| 07_resources_list.json | Recursos: contrato, registro de vigencia y catálogo |
| 08_consultar_vigencia.json | Vigencia de RES-CREG-0112-2021 (derogada por R3) |

Para la demostración en vivo con la interfaz web: `make inspector`.
