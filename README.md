# PetroAndes · Consulta documental gobernada (Taller 2, ARTI 4212)

Servicio que responde preguntas de operación sobre el corpus documental de PetroAndes y AndesTransporte **citando documento, versión y sección**, que **nunca cita material derogado** y que **declara cuando la respuesta no está en el corpus**. Expone la recuperación como herramientas de un servidor MCP y trae un arnés de evaluación con 30 casos de referencia y 23 de validación. La decisión de responder la toma un clasificador local que no genera texto, elegido tras comparar tres alternativas (ADR-008).

Grupo 3 · Arquitectura de Integración (ARTI 4212) · Universidad de los Andes · noviembre de 2026.  
**Integrantes:** Camila Andrea Morales Ortega · Santiago Andrés Leal Omaña · Miguel Ángel Mendieta Hernández · Santiago Baquero Villa.

| Entregable | Dónde |
|---|---|
| Código: ingesta, recuperación, servidor MCP, arnés | `src/petroandes_docs/` |
| Casos de referencia y de validación | `eval/casos_referencia.yaml`, `eval/casos_validacion.yaml` |
| Resultados de la evaluación y prueba de envenenamiento | `eval/resultados/reporte.md`, `eval/resultados/envenenamiento.md` |
| Comparación de las tres alternativas de decisión (ADR-008) | `eval/comparacion/comparacion.md` (y rondas 1 y 2) |
| Verificación con MCP Inspector | `eval/resultados/inspector/` |
| Documento de arquitectura del Escenario A | `docs/A_arquitectura_escenario_A.md` |
| ADR (8) | `docs/adr/` |
| Documento de diseño del Escenario B (BPMN, grafo, matriz, seguridad, gobierno) | `docs/B_diseno_escenario_B.md`, `docs/escenario_b/` |
| Análisis crítico | `docs/C_analisis_critico.md` |
| Guion de la demostración y preguntas de sustentación | `docs/D_demo_y_sustentacion.md` |
| Contrato del corpus y registro de vigencia | `config/` |

## Cómo correrlo en otra máquina

### Requisitos

- Python 3.10 a 3.13 (probado con 3.13 en Windows 11 y Linux).
- Unos 5 GB libres para los modelos de Hugging Face, que se descargan la primera vez: e5-small (0,5 GB), `bge-reranker-v2-m3` (2,3 GB) y el checkpoint de laya. `comparar` baja además `Qwen2.5-1.5B-Instruct` (3 GB).
- Acceso a internet en la primera ejecución. Después todo corre sin red (`HF_HUB_OFFLINE=1`).
- Node.js 18 o superior (incluye `npx`), solo para el MCP Inspector.
- No hace falta GPU ni un servidor de Qdrant: Qdrant corre embebido en `data/`.

**El entorno virtual va fuera de carpetas sincronizadas.** Si el repositorio está en Google Drive, OneDrive o Dropbox, cree el entorno en otra ruta: son unos 40.000 archivos que el cliente intentaría subir. Los ejemplos lo crean en el directorio personal.

### Linux y macOS

```bash
cd petroandes-consulta-documental
python3 -m venv ~/.venvs/petroandes
source ~/.venvs/petroandes/bin/activate
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu   # opcional en Linux: evita bajar la versión CUDA
pip install -e ".[st,laya,dev]"

# antes: copiar el corpus del enunciado en corpus/pdf y corpus/md (ver «Corpus»)
petroandes-docs ingestar
petroandes-docs evaluar --juez laya
petroandes-docs prueba-envenenamiento
python -m pytest -q
```

Con `make`: `make instalar ingestar evaluar envenenamiento pruebas` (con el entorno ya activado).

### Windows (PowerShell)

```powershell
cd petroandes-consulta-documental
py -3 -m venv $env:LOCALAPPDATA\petroandes-venv
& $env:LOCALAPPDATA\petroandes-venv\Scripts\Activate.ps1   # si lo bloquea: Set-ExecutionPolicy -Scope Process Bypass
$env:PYTHONUTF8 = "1"
python -m pip install --upgrade pip
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e ".[st,laya,dev]"

petroandes-docs ingestar
petroandes-docs evaluar --juez laya
petroandes-docs prueba-envenenamiento
python -m pytest -q
```

### Windows con doble clic

Los `.bat` de la raíz hacen lo mismo y dejan un registro de texto junto al `.bat`. Usan el entorno de `%LOCALAPPDATA%\petroandes-venv`; para otra ruta, defina `PETROANDES_VENV` antes de ejecutarlos.

| Archivo | Qué hace | Registro |
|---|---|---|
| `correr_windows.bat` | Crea el entorno, instala, ingesta, evalúa con laya y corre la prueba de envenenamiento | `windows_log.txt` |
| `correr_pruebas_windows.bat` | Corre las 51 pruebas | `pruebas_log.txt` |
| `correr_comparacion_windows.bat` | Comparación de ADR-008 (unos 13 minutos en CPU) | `windows_log_comparacion.txt` |
| `capturar_inspector_windows.bat` | Captura la verificación con el MCP Inspector | `inspector_log.txt` |
| `actualizar_evidencias_windows.bat` | Respalda `eval/resultados/`, reingesta, evalúa, corre la prueba de envenenamiento y captura el Inspector | `evidencias_log.txt` |

`correr_windows.bat` va primero: los demás usan el entorno y el índice que deja.

### Reproducir las mismas cifras

Las cifras del informe salieron con estos commits de los modelos. Para fijarlos, defina las variables antes de `ingestar`:

```bash
export PETROANDES_EMBEDDINGS=st:intfloat/multilingual-e5-small@614241f622f53c4eeff9890bdc4f31cfecc418b3
export PETROANDES_DECISOR=crossencoder:BAAI/bge-reranker-v2-m3@953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e
# PowerShell: $env:PETROANDES_EMBEDDINGS = "st:...@614241f..."   ·   cmd: set PETROANDES_EMBEDDINGS=st:...@614241f...
```

laya no admite fijar revisión y se carga desde `main`; si su checkpoint cambia, el anclaje y la pertinencia pueden variar algo, no la tasa de desviación, que se calcula sin juez.

Con esos commits deben salir 30 de 30 en referencia, 18 de 23 en validación, 0 derogados recuperados y 51 pruebas aprobadas. `eval/resultados/reporte.md` registra la huella del índice con la que se obtuvieron. La latencia depende de la CPU.

### Modo liviano, sin Hugging Face

Para pruebas rápidas o integración continua, sin descargar modelos: el modelo alterno de spaCy y el juez léxico. Las cifras del informe se midieron con e5 y laya.

```bash
pip install -e ".[spacy,dev]"
export PETROANDES_EMBEDDINGS=spacy:es_core_news_md     # PowerShell: $env:PETROANDES_EMBEDDINGS = "spacy:es_core_news_md"
export PETROANDES_ESTRATEGIA=A0G                       # el decisor A2 también viene de Hugging Face
petroandes-docs ingestar
petroandes-docs evaluar --juez lexico
```

Sin variable, A2 intenta cargar el decisor y, si no puede, opera en A0G y lo avisa.

### Problemas frecuentes

- **«El índice se construyó con … y la configuración pide …»**: cambió `PETROANDES_EMBEDDINGS` o el commit del modelo. Corra `petroandes-docs ingestar` de nuevo (ADR-004).
- **`UnicodeEncodeError` en la consola de Windows**: defina `PYTHONUTF8=1` (los `.bat` ya lo hacen).
- **El Inspector no arranca**: compruebe `npx --version`. La primera vez `npx` descarga `@modelcontextprotocol/inspector`.

## Corpus

El corpus (19 documentos sintéticos publicados con el enunciado del curso) **no se incluye en este repositorio público**. Antes de `ingestar` o de correr las pruebas, copie los PDF del enunciado en `corpus/pdf/` y los Markdown en `corpus/md/`, con las subcarpetas que lista `corpus/LEEME.md`. **La ingesta procesa los PDF**; las pruebas también los necesitan.

La prueba de envenenamiento usa `herramientas/regenerar_pdf.py` para armar, en una carpeta temporal, un PDF con la maquetación del corpus y la paráfrasis del ataque.

## Uso

```bash
petroandes-docs ingestar                    # carga inicial (consolidación)
petroandes-docs vigencia                    # estado de vigencia de cada documento
petroandes-docs preguntar "¿Cuál es el umbral de alarma de presión en el tramo Ayacucho – Coveñas?"
petroandes-docs preguntar "¿Cuál era el umbral de alarma en Ayacucho – Coveñas?" --fecha 2025-08-15
petroandes-docs preguntar "Antes de meterle mano a un equipo con energía peligrosa, ¿quién confirma que quedó en energía cero?" --estrategia A0   # compare sin --estrategia (A2)
petroandes-docs buscar "¿A quién se escalan las diferencias de balance superiores al uno por ciento?" --modo semantico   # compare con --modo hibrido
petroandes-docs sincronizar                 # propagación: cambios de PDF o del registro de vigencia
petroandes-docs evaluar --juez laya         # o --juez lexico si no hay checkpoint; --estrategia A0|A0G|A1|A2|A3
petroandes-docs comparar --juez laya        # ADR-008: compara A0, A0G, A1, A2r1, A2md, A2 y A3 en referencia y validación
petroandes-docs prueba-envenenamiento
petroandes-docs auditar-fragmento COM-PRV-0134 — Anexo   # revisión humana de un fragmento en cuarentena
python -m pytest -q                         # 51 pruebas
```

`make demo` corre las cuatro escenas de la demostración en vivo.

## Servidor MCP

```bash
petroandes-mcp                              # stdio
petroandes-mcp --http                       # Streamable HTTP en 127.0.0.1:8765
npx -y @modelcontextprotocol/inspector petroandes-mcp      # Inspector (interfaz web)
```

Configuración para un host MCP (Claude Desktop, por ejemplo):

```json
{"mcpServers": {"petroandes-docs": {"command": "petroandes-mcp",
  "env": {"PETROANDES_RAIZ": "/ruta/al/repositorio", "PETROANDES_EMBEDDINGS": "st:intfloat/multilingual-e5-small"}}}}
```

Herramientas (todas de solo lectura): `buscar_documentos`, `obtener_fragmento`, `responder_consulta`, `consultar_vigencia`. Recursos: `petroandes://corpus/contrato`, `petroandes://corpus/registro-vigencia`, `petroandes://corpus/documentos`.

## Configuración

| Variable | Por defecto | Qué hace |
|---|---|---|
| `PETROANDES_EMBEDDINGS` | `st:intfloat/multilingual-e5-small` | Modelo de embeddings (`st:<modelo>[@commit]` o `spacy:<modelo>`); la huella del índice guarda el commit cargado |
| `PETROANDES_ESTRATEGIA` | `A2` | Estrategia de decisión (ADR-008): A0, A0G, A1, A2, A3; si el decisor no carga, degrada a A0G |
| `PETROANDES_DECISOR` | `crossencoder:BAAI/bge-reranker-v2-m3` | Clasificador que decide si una frase responde; admite `@commit` |
| `PETROANDES_UMBRAL_COBERTURA` | `0.6` | Umbral de cobertura léxica para responder o negarse en A0 y A0G (ADR-003) |
| `PETROANDES_RAIZ` | carpeta del repositorio | Raíz para resolver `config/`, `corpus/` y `data/` |
| `PETROANDES_DATOS` | `data/` | Índice, manifiesto y auditoría |
| `QDRANT_URL` | (vacío: Qdrant embebido) | Qdrant en modo servidor |

Si se cambia el modelo de embeddings, el índice se niega a buscar hasta reindexar (ADR-004).

## Resultados (prototipo)

Con los PDF originales, `multilingual-e5-small`, la estrategia A2 (ADR-008) y el juez laya:

- referencia: 30 de 30 (conjunto usado durante el ajuste de reglas de ADR-008);
- validación (23 casos nuevos): **18 de 23**, desviación **22 %**, que no cumple el SLO agregado de ≤ 10 % (desglose por gravedad: 0 % respuestas indebidas, 9 % otra frase de la fuente correcta, 13 % negativas de más);
- 0 respuestas fuera del corpus o con un valor prohibido en los 53 casos;
- 0 fragmentos derogados recuperados (sin filtro serían 31);
- latencia p50 de 1,5–1,7 s por respuesta en CPU (1.539 ms en la comparación; 1.566 y 1.649 ms en las dos corridas de evaluación de referencia; 1.446 ms en validación).

La evaluación se corrió dos veces (19 y 22 de noviembre) con las mismas cifras; la corrida anterior queda en `eval/resultados_2026-11-19/`.

Las cifras de A2 son optimistas: dos reglas se ajustaron viendo casos (ADR-008, «Sesgos»).

| Corrida | Dónde |
|---|---|
| Antes de ADR-008 (decisión léxica): 24 de 30 | `eval/resultados_A0_e5_laya/` |
| Modelo alterno de spaCy con juez léxico: 25 de 30 | `eval/resultados_spacy_lexico/` |

## Estructura

```
config/            contrato del corpus y registro de vigencia
corpus/            pdf/ y md/ (19 documentos del enunciado; no incluidos)
src/petroandes_docs/
  extraccion.py    PDF → modelo canónico (Normalizer)
  vigencia.py      reglas R1–R5 y conciliación con el registro
  particion.py     secciones y metadatos (Splitter + Content Enricher)
  seguridad.py     escáner de instrucciones embebidas y redacción de salida
  embeddings.py    modelo versionado con huella
  lexico.py        BM25 como vector disperso
  indice.py        Qdrant: carga inicial y sincronización
  recuperacion.py  búsqueda híbrida con el filtro dentro de la consulta
  guardas.py       guarda de entidades (tramos, códigos, equipos)
  decisores.py     quién puntúa si una frase responde: cobertura léxica o decisor local
  interpretacion.py LLM local que reinterpreta la pregunta (A1, medida y descartada)
  estrategias.py   catálogo A0…A3, la elegida (A2) y el modo degradado
  composicion.py   respuesta extractiva con citas o negativa
  comparacion.py   comparación de estrategias con el mismo juez (ADR-008)
  servidor_mcp.py  servidor MCP
  evaluacion.py    arnés (Control Bus) · jueces.py: laya y léxico
  envenenamiento.py prueba de envenenamiento
eval/              casos y resultados
docs/              documentos A, B, C, D, ADR y escenario_b/
herramientas/      regenerar_pdf.py, generar_bpmn.py, capturar_inspector.py
tests/             pruebas
```

## Declaración de uso de IA generativa

El grupo trabajó con el ciclo AI-DLC (AI-Driven Development Life Cycle). Un asistente de IA (Claude, de Anthropic) propuso planes, código, pruebas y borradores de los documentos. El grupo definió los requisitos a partir del enunciado, eligió entre las alternativas propuestas, aprobó cada etapa antes de continuar y revisó el resultado. Las pruebas, la evaluación y la captura del MCP Inspector se corrieron en el computador del grupo. Las decisiones de los ADR, las cifras y su interpretación fueron revisadas y aprobadas por el grupo, que las sustenta.

Los documentos del corpus son sintéticos, de uso académico, sobre empresas y entidades ficticias.
