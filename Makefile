# Taller 2 — Consulta documental gobernada (PetroAndes)
# Uso típico:  make instalar && make ingestar && make evaluar && make demo
PY ?= python
# Sin Hugging Face: make <objetivo> PETROANDES_EMBEDDINGS=spacy:es_core_news_md JUEZ=lexico
PETROANDES_EMBEDDINGS ?= st:intfloat/multilingual-e5-small
JUEZ ?= laya
export PETROANDES_EMBEDDINGS

instalar:            ## Dependencias base + modelo por defecto + laya + pruebas
	$(PY) -m pip install -e ".[st,laya,dev]"

instalar-sin-hf:     ## Alternativa sin Hugging Face (modelo spaCy, juez léxico)
	$(PY) -m pip install -e ".[spacy,dev]"

ingestar:            ## Carga inicial (consolidación) desde corpus/pdf
	petroandes-docs ingestar

sincronizar:         ## Propagación de cambios de PDF o del registro de vigencia
	petroandes-docs sincronizar

evaluar:             ## Arnés de evaluación (JUEZ=laya por defecto; JUEZ=lexico sin checkpoint)
	petroandes-docs evaluar --juez $(JUEZ)

envenenamiento:      ## Prueba de envenenamiento con evidencia por capa
	petroandes-docs prueba-envenenamiento

pruebas:             ## Pruebas automáticas
	$(PY) -m pytest -q

inspector:           ## MCP Inspector (interfaz web) contra el servidor stdio
	npx -y @modelcontextprotocol/inspector petroandes-mcp

demo:                ## Las cuatro escenas de la demostración en vivo
	@echo "== 1. Consulta fundamentada con citas"; petroandes-docs preguntar "¿Cuál es el umbral de alarma de presión en el tramo Ayacucho – Coveñas?"
	@echo; echo "== 2. Pregunta que no está en el corpus"; petroandes-docs preguntar "¿Cuál es el precio del barril de crudo Brent hoy?"
	@echo; echo "== 3. Intento de recuperar un documento derogado"; petroandes-docs preguntar "Según el PRO-SEG-009, ¿en cuánto tiempo se reporta a la autoridad competente una pérdida de producto?"
	@echo; echo "== 4. Arnés de evaluación"; petroandes-docs evaluar --juez $(JUEZ) --sin-barrido

.PHONY: instalar instalar-sin-hf ingestar sincronizar evaluar envenenamiento pruebas inspector demo comparar

comparar:            ## ADR-008: compara las estrategias de decisión con el mismo juez (descarga Qwen y bge-reranker)
	petroandes-docs comparar --juez $(JUEZ)
