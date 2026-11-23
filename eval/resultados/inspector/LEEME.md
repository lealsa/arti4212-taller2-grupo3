# Verificación con MCP Inspector

Salidas reales del MCP Inspector en modo CLI contra el servidor stdio (`petroandes-mcp`) con la estrategia vigente (A2, ADR-008), capturadas el 22 de noviembre de 2026 con `herramientas/capturar_inspector.py` (en Windows: `capturar_inspector_windows.bat`). Versiones del Inspector y de Node, y commits de los modelos: `entorno.json`.

Comando base:

    npx -y @modelcontextprotocol/inspector --cli petroandes-mcp --method tools/list

| Archivo | Qué verifica |
|---|---|
| 01_tools_list.json | Las cuatro herramientas con su contrato completo: descripción para el modelo, JSON Schema de entrada y salida (con patrones y longitudes) y anotaciones de solo lectura. El Inspector no imprime ttlMs ni cacheScope; los verifica la prueba `test_listado_declara_ttl_y_alcance_de_cache` |
| 02_responder_consulta.json | Consulta fundamentada: 1.100 psi con cita PRO-OPE-012 v3 §3 |
| 03_buscar_documentos_codigo.json | Búsqueda por código de orden de trabajo (léxica dentro de la híbrida) |
| 04_obtener_fragmento_derogado.json | Error DOCUMENTO_DEROGADO con el documento que lo reemplaza |
| 04b_obtener_fragmento_vigente.json | Fragmento vigente por documento, versión y sección |
| 05_obtener_fragmento_cuarentena.json | Error FRAGMENTO_EN_CUARENTENA: el texto envenenado no se entrega |
| 06_responder_sin_respaldo.json | La respuesta no está en el corpus: estado `sin_respaldo` |
| 07_resources_list.json | Recursos: contrato, registro de vigencia y catálogo |
| 08_consultar_vigencia.json | Vigencia de RES-CREG-0112-2021 (derogada por R3) |
| 09_responder_parafrasis.json | Paráfrasis («meterle mano») que A0 rechazaba: A2 responde con PRO-HSE-003 v4 §3 |
| 10_responder_tramo_inexistente.json | Tramo que no existe (Barrancabermeja – Coveñas): `sin_respaldo` por la guarda de entidades |

La captura anterior (18 de noviembre, antes de ADR-008) quedó en `eval/resultados_2026-11-19/inspector/`.

Para la demostración en vivo con la interfaz web: `make inspector`.
