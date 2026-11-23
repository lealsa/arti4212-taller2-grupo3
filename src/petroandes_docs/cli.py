"""Línea de comandos: petroandes-docs <comando>."""
from __future__ import annotations

import argparse
import json
import sys
import warnings

warnings.filterwarnings("ignore", message=".*Payload indexes have no effect in the local Qdrant.*")


def _cfg():
    from .config import cargar
    return cargar()


def cmd_ingestar(a):
    from .indice import Indice
    Indice.construir(_cfg())


def cmd_sincronizar(a):
    from .indice import Indice
    r = Indice.abrir(_cfg()).sincronizar()
    if not any(r.values()):
        print("Sin cambios: el índice refleja el corpus y el registro de vigencia.")


from .estrategias import DECISOR_POR_DEFECTO, INTERPRETE_POR_DEFECTO, NOMBRES  # noqa: E402


def cmd_preguntar(a):
    import os
    from .composicion import componer
    from .indice import Indice
    from .estrategias import fabrica, por_defecto
    ix = Indice.abrir(_cfg())
    aviso = None
    if a.estrategia:
        est = fabrica(a.estrategia, ix, os.environ.get("PETROANDES_INTERPRETE", INTERPRETE_POR_DEFECTO),
                      os.environ.get("PETROANDES_DECISOR", DECISOR_POR_DEFECTO), a.umbral_decisor)()
    else:
        est, aviso = por_defecto(ix)
    r = componer(ix, a.pregunta, modo=a.modo, fecha_referencia=a.fecha, estrategia=est)
    if aviso:
        r.advertencias.insert(0, aviso)
    print(json.dumps(r.a_dict(), ensure_ascii=False, indent=1) if a.json else r.markdown())


def cmd_buscar(a):
    from .indice import Indice
    from .recuperacion import buscar
    for r in buscar(Indice.abrir(_cfg()), a.consulta, k=a.k, modo=a.modo, fecha_referencia=a.fecha, filtro=a.filtro):
        p = r.payload
        print(f"{r.rango:>2}. {p['id']:<32} {p['estado_vigencia']:<24} {'CUARENTENA ' if p['cuarentena'] else ''}{p['titulo_seccion']}")


def cmd_vigencia(a):
    from .indice import Indice
    for d in Indice.abrir(_cfg()).documentos():
        rp = f" → {d['reemplazado_por']}" if d["reemplazado_por"] else ""
        print(f"{d['codigo']:<20} v{d['version']:<3} {d['estado_vigencia']:<24} {d['certificado_por']}{rp}")


def cmd_auditar(a):
    """Revisión humana de un fragmento en cuarentena. No existe equivalente en el servidor MCP."""
    from .indice import Indice
    p = Indice.abrir(_cfg()).fragmento(a.codigo, a.version, a.seccion)
    if p is None:
        sys.exit("No existe ese fragmento.")
    print(f"Fragmento {p['id']} · cuarentena={p['cuarentena']} · motivo={p['motivo_cuarentena']}")
    print("<<<DATO_NO_CONFIABLE")
    print(p["texto"])
    print("DATO_NO_CONFIABLE>>>")


def cmd_evaluar(a):
    from pathlib import Path
    from . import jueces
    from .evaluacion import ejecutar
    from .indice import Indice
    from .estrategias import fabrica, por_defecto
    ix = Indice.abrir(_cfg())
    est = fabrica(a.estrategia, ix)() if a.estrategia else por_defecto(ix)[0]
    inf = ejecutar(ix, Path(a.casos), jueces.crear(a.juez), Path(a.salida), barrido=not a.sin_barrido, estrategia=est)
    m = inf["metricas"]
    print(f"Estrategia {inf['estrategia']} · juez {inf['juez']} · {m['correctos']}/{m['casos']} correctos · desviación {m['tasa_desviacion']:.0%} · "
          f"acierto@5 híbrido {m['recuperacion']['hibrido']['acierto@5']:.0%} · anclaje {m['anclaje']:.0%} · "
          f"derogados recuperados {m['violaciones_vigencia']}")
    print(f"Reporte: {a.salida}/reporte.md")


def cmd_comparar(a):
    from pathlib import Path
    from . import jueces
    from .comparacion import ejecutar
    from .indice import Indice
    ix = Indice.abrir(_cfg())
    conjuntos = {Path(c).stem.replace("casos_", ""): Path(c) for c in a.casos}
    from .estrategias import fabrica
    fabricas = {n: fabrica(n, ix, a.interprete, a.decisor, a.umbral_decisor) for n in a.estrategias.split(",")}
    juez = None if a.juez == "ninguno" else jueces.crear(a.juez)
    inf = ejecutar(ix, conjuntos, fabricas, juez, Path(a.salida))
    for n, b in inf["estrategias"].items():
        partes = [f"{cj}: {x['metricas']['correctos']}/{x['metricas']['casos']} (indebidas {x['metricas']['indebidas']})"
                  for cj, x in b["conjuntos"].items()]
        print(f"{n} · " + " · ".join(partes))
    print(f"Reporte: {a.salida}/comparacion.md")


def cmd_envenenamiento(a):
    from pathlib import Path
    from .envenenamiento import ejecutar
    print(ejecutar(_cfg(), Path(a.salida)))


def cmd_servidor(a):
    from .servidor_mcp import main
    main(["--http"] if a.http else [])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="petroandes-docs", description="Consulta documental gobernada — PetroAndes")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ingestar", help="Carga inicial (consolidación): construye el índice desde corpus/pdf")
    s.set_defaults(f=cmd_ingestar)
    s = sub.add_parser("sincronizar", help="Propagación: aplica cambios de PDF y del registro de vigencia")
    s.set_defaults(f=cmd_sincronizar)
    s = sub.add_parser("preguntar", help="Respuesta con citas o negativa honesta")
    s.add_argument("pregunta")
    s.add_argument("--modo", default="hibrido", choices=["hibrido", "semantico", "lexico"])
    s.add_argument("--fecha", help="AAAA-MM-DD: responder según lo que regía en esa fecha")
    s.add_argument("--json", action="store_true")
    s.add_argument("--estrategia", choices=NOMBRES, help="ADR-008; sin valor: PETROANDES_ESTRATEGIA o A2")
    s.add_argument("--umbral-decisor", type=float, default=0.5)
    s.set_defaults(f=cmd_preguntar)
    s = sub.add_parser("buscar", help="Fragmentos recuperados")
    s.add_argument("consulta")
    s.add_argument("-k", type=int, default=5)
    s.add_argument("--modo", default="hibrido", choices=["hibrido", "semantico", "lexico"])
    s.add_argument("--fecha")
    s.add_argument("--filtro", default="previo", choices=["previo", "posterior", "ninguno"])
    s.set_defaults(f=cmd_buscar)
    s = sub.add_parser("vigencia", help="Estado de vigencia de cada documento indexado")
    s.set_defaults(f=cmd_vigencia)
    s = sub.add_parser("auditar-fragmento", help="(Humano) ver el texto de un fragmento, incluso en cuarentena")
    s.add_argument("codigo"); s.add_argument("version"); s.add_argument("seccion")
    s.set_defaults(f=cmd_auditar)
    s = sub.add_parser("evaluar", help="Arnés de evaluación sobre los casos de referencia")
    s.add_argument("--juez", default="laya", choices=["laya", "lexico"])
    s.add_argument("--casos", default="eval/casos_referencia.yaml")
    s.add_argument("--salida", default="eval/resultados")
    s.add_argument("--sin-barrido", action="store_true")
    s.add_argument("--estrategia", choices=NOMBRES, help="ADR-008; sin valor: PETROANDES_ESTRATEGIA o A2")
    s.set_defaults(f=cmd_evaluar)
    s = sub.add_parser("comparar", help="ADR-008: compara las estrategias A0, A1 y A2 con el mismo juez")
    s.add_argument("--casos", nargs="+", default=["eval/casos_referencia.yaml", "eval/casos_validacion.yaml"])
    s.add_argument("--estrategias", default=",".join(NOMBRES))
    s.add_argument("--juez", default="laya", choices=["laya", "lexico", "ninguno"])
    s.add_argument("--interprete", default=INTERPRETE_POR_DEFECTO, help="hf:<modelo> | ollama:<modelo>")
    s.add_argument("--decisor", default=DECISOR_POR_DEFECTO, help="crossencoder:<modelo>")
    s.add_argument("--umbral-decisor", type=float, default=0.5)
    s.add_argument("--salida", default="eval/comparacion")
    s.set_defaults(f=cmd_comparar)
    s = sub.add_parser("prueba-envenenamiento", help="Recupera el documento envenenado y evidencia qué capa lo detiene")
    s.add_argument("--salida", default="eval/resultados")
    s.set_defaults(f=cmd_envenenamiento)
    s = sub.add_parser("servidor", help="Servidor MCP (stdio por defecto)")
    s.add_argument("--http", action="store_true")
    s.set_defaults(f=cmd_servidor)
    a = ap.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
