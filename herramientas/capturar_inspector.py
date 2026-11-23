"""Captura la verificación del servidor MCP con el MCP Inspector en modo CLI.

Uso, con el índice construido: python herramientas/capturar_inspector.py
Deja las salidas y entorno.json (versiones y commits) en eval/resultados/inspector/.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "eval" / "resultados" / "inspector"
INSPECTOR = "@modelcontextprotocol/inspector"

LLAMADAS = [
    ("01_tools_list", ["--method", "tools/list"]),
    ("02_responder_consulta", ["--method", "tools/call", "--tool-name", "responder_consulta",
                               "--tool-arg", "pregunta=¿Cuál es el umbral de alarma de presión en el tramo Ayacucho – Coveñas?"]),
    ("03_buscar_documentos_codigo", ["--method", "tools/call", "--tool-name", "buscar_documentos",
                                     "--tool-arg", "consulta=orden OT-2021-03117"]),
    ("04_obtener_fragmento_derogado", ["--method", "tools/call", "--tool-name", "obtener_fragmento",
                                       "--tool-arg", "codigo=PRO-OPE-012", "--tool-arg", "version=2", "--tool-arg", "seccion=3"]),
    ("04b_obtener_fragmento_vigente", ["--method", "tools/call", "--tool-name", "obtener_fragmento",
                                       "--tool-arg", "codigo=PRO-OPE-012", "--tool-arg", "version=3", "--tool-arg", "seccion=3"]),
    ("05_obtener_fragmento_cuarentena", ["--method", "tools/call", "--tool-name", "obtener_fragmento",
                                         "--tool-arg", "codigo=COM-PRV-0134", "--tool-arg", "version=—", "--tool-arg", "seccion=Anexo"]),
    ("06_responder_sin_respaldo", ["--method", "tools/call", "--tool-name", "responder_consulta",
                                   "--tool-arg", "pregunta=¿Cuál es el precio del barril de crudo Brent hoy?"]),
    ("07_resources_list", ["--method", "resources/list"]),
    ("08_consultar_vigencia", ["--method", "tools/call", "--tool-name", "consultar_vigencia",
                               "--tool-arg", "codigo=RES-CREG-0112-2021"]),
    ("09_responder_parafrasis", ["--method", "tools/call", "--tool-name", "responder_consulta",
                                 "--tool-arg", "pregunta=Antes de meterle mano a un equipo con energía peligrosa, ¿quién confirma que quedó en energía cero?"]),
    ("10_responder_tramo_inexistente", ["--method", "tools/call", "--tool-name", "responder_consulta",
                                        "--tool-arg", "pregunta=¿Cuál es el umbral de alarma de presión del tramo Barrancabermeja – Coveñas?"]),
]

ENTORNO_SERVIDOR = ["PYTHONUTF8=1", "PYTHONIOENCODING=utf-8", "PETROANDES_ESTRATEGIA=A2", "HF_HUB_OFFLINE=1",
                    f"PETROANDES_RAIZ={RAIZ}"]


def _ejecutable(nombre: str) -> str:
    ruta = shutil.which(nombre)
    if not ruta:
        sys.exit(f"No se encontró «{nombre}» en el PATH. Instale Node.js (incluye npx) y vuelva a correr.")
    return ruta


def _servidor() -> str:
    carpeta = Path(sys.executable).parent
    for nombre in ("petroandes-mcp.exe", "petroandes-mcp"):
        if (carpeta / nombre).exists():
            return str(carpeta / nombre)
    return _ejecutable("petroandes-mcp")


def _texto(cmd: list[str], timeout: int = 120) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return (r.stdout or r.stderr).strip()


def main() -> None:
    npx, npm, node = _ejecutable("npx"), _ejecutable("npm"), _ejecutable("node")
    servidor = _servidor()
    SALIDA.mkdir(parents=True, exist_ok=True)
    env_flags = [x for kv in ENTORNO_SERVIDOR for x in ("-e", kv)]
    fallos = []
    for nombre, args in LLAMADAS:
        cmd = [npx, "-y", INSPECTOR, "--cli", *env_flags, servidor, *args]
        print(f"[inspector] {nombre} …", flush=True)
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        destino = SALIDA / f"{nombre}.json"
        try:
            datos = json.loads(r.stdout)
            destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except json.JSONDecodeError:
            fallos.append(nombre)
            destino.with_suffix(".error.txt").write_text(
                f"codigo={r.returncode}\n--- stdout\n{r.stdout}\n--- stderr\n{r.stderr}\n", encoding="utf-8")
            print(f"[inspector] {nombre}: la salida no es JSON (ver {destino.with_suffix('.error.txt').name})", flush=True)

    from petroandes_docs.revisiones import resolver
    manifiesto = json.loads((RAIZ / "data" / "manifiesto.json").read_text(encoding="utf-8"))
    entorno = {
        "capturado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "inspector": _texto([npm, "view", INSPECTOR, "version"]),
        "node": _texto([node, "--version"]),
        "servidor": "petroandes-mcp (stdio)",
        "estrategia": "A2",
        "huella_embeddings": manifiesto.get("embeddings", {}).get("huella"),
        "coleccion": manifiesto.get("coleccion"),
        "revisiones": {m: resolver(m) for m in ("intfloat/multilingual-e5-small", "BAAI/bge-reranker-v2-m3",
                                                   "convaiinnovations/laya")},
        "llamadas_fallidas": fallos,
    }
    (SALIDA / "entorno.json").write_text(json.dumps(entorno, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(entorno, ensure_ascii=False, indent=2), flush=True)
    if fallos:
        sys.exit(1)


if __name__ == "__main__":
    main()
