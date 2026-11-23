import asyncio
import json

import yaml

from petroandes_docs.envenenamiento import PARAFRASIS
from petroandes_docs.indice import Indice
from petroandes_docs.recuperacion import buscar
from petroandes_docs.seguridad import en_cuarentena, escanear, redactar_salida


def test_el_anexo_envenenado_queda_en_cuarentena_y_nada_mas(indice):
    pts, _ = indice.cliente.scroll(indice.coleccion, limit=1000, with_payload=True)
    assert [p.payload["id"] for p in pts if p.payload["cuarentena"]] == ["COM-PRV-0134@v—#Anexo"]


def test_limitacion_conocida_la_parafrasis_evade_el_escaner():
    """Documenta el límite de la capa que detecta: no debe ser la única defensa."""
    assert not en_cuarentena(escanear(PARAFRASIS))


def test_redaccion_de_salida_retira_correos_y_urls():
    t, n = redactar_salida("escriba a soporte-firmware@proveedor.ejemplo o https://x.ejemplo/a")
    assert n == 2 and "@" not in t and "https" not in t


def _llamar(indice, herramienta, args):
    from mcp import Client
    from petroandes_docs.servidor_mcp import crear_servidor

    async def run():
        async with Client(crear_servidor(lambda: indice)) as c:
            if herramienta == "__list__":
                return (await c.list_tools()).tools
            return await c.call_tool(herramienta, args)
    return asyncio.run(run())


def test_todas_las_herramientas_son_de_solo_lectura(indice):
    herramientas = _llamar(indice, "__list__", None)
    assert {h.name for h in herramientas} == {"buscar_documentos", "obtener_fragmento", "responder_consulta", "consultar_vigencia"}
    for h in herramientas:
        assert h.annotations.read_only_hint and not h.annotations.open_world_hint and h.description


def test_obtener_fragmento_derogado_redirige_al_vigente(indice):
    r = _llamar(indice, "obtener_fragmento", {"codigo": "PRO-OPE-012", "version": "2", "seccion": "3"})
    assert r.is_error and "DOCUMENTO_DEROGADO" in r.content[0].text and "PRO-OPE-012 v3" in r.content[0].text


def test_obtener_fragmento_en_cuarentena_no_entrega_el_texto(indice):
    r = _llamar(indice, "obtener_fragmento", {"codigo": "COM-PRV-0134", "version": "—", "seccion": "Anexo"})
    assert r.is_error and "FRAGMENTO_EN_CUARENTENA" in r.content[0].text and "soporte-firmware" not in r.content[0].text


def test_esquema_rechaza_argumentos_fuera_de_contrato(indice):
    r = _llamar(indice, "buscar_documentos", {"consulta": "umbral", "k": 50})
    assert r.is_error


def test_seccion_inexistente_informa_las_validas(indice):
    r = _llamar(indice, "obtener_fragmento", {"codigo": "PRO-OPE-012", "version": "3", "seccion": "9"})
    assert r.is_error and "SECCION_NO_ENCONTRADA" in r.content[0].text and "secciones_validas" in r.content[0].text


def test_sincronizar_propaga_un_cambio_de_vigencia_sin_reindexar(cfg_aislado):
    ix = Indice.construir(cfg_aislado, log=lambda *_: None)
    data = yaml.safe_load(cfg_aislado.registro.read_text(encoding="utf-8"))
    for e in data["documentos"]:
        if e["codigo"] == "PRO-HSE-003":
            e.update(estado="derogado", vigente_hasta="2026-11-17", reemplazado_por="PRO-HSE-003 v5 (prueba)")
    cfg_aislado.registro.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    resumen = ix.sincronizar(log=lambda *_: None)
    assert resumen["vigencia_cambiada"] and not resumen["modificados"]
    ids = [r.id for r in buscar(ix, "bloqueo y etiquetado energía cero", k=10)]
    assert not any(i.startswith("PRO-HSE-003") for i in ids)


def test_sincronizar_detecta_un_documento_retirado(cfg_aislado):
    ix = Indice.construir(cfg_aislado, log=lambda *_: None)
    (cfg_aislado.corpus_pdf / "06_fichas" / "FIC-ACT-P101_v2.pdf").unlink()
    resumen = ix.sincronizar(log=lambda *_: None)
    assert resumen["retirados"] == ["FIC-ACT-P101@v2"]
    assert not any(r.payload["codigo"] == "FIC-ACT-P101" for r in buscar(ix, "OT-2021-03117", k=5, modo="lexico"))


def test_listado_declara_ttl_y_alcance_de_cache(indice):
    from mcp import Client
    from petroandes_docs.servidor_mcp import crear_servidor

    async def run():
        async with Client(crear_servidor(lambda: indice)) as c:
            return await c.list_tools()
    r = asyncio.run(run())
    assert r.ttl_ms == 3_600_000 and r.cache_scope == "public"


def test_contrato_declara_patron_de_version_y_longitud_de_seccion(indice):
    """El JSON Schema publicado debe llevar las restricciones que el servidor valida (contrato completo)."""
    from mcp import Client
    from petroandes_docs.servidor_mcp import crear_servidor

    async def run():
        async with Client(crear_servidor(lambda: indice)) as c:
            return await c.list_tools()
    tools = {t.name: t for t in asyncio.run(run()).tools}
    props = tools["obtener_fragmento"].input_schema["properties"]
    assert props["version"]["pattern"] == r"^(\d+|—)$"
    assert props["seccion"]["maxLength"] == 60
    vig = tools["consultar_vigencia"].input_schema["properties"]["version"]
    assert any(o.get("pattern") == r"^(\d+|—)$" for o in vig["anyOf"])


def test_llamadas_en_paralelo_abren_un_solo_indice(cfg_aislado, monkeypatch):
    import threading
    from petroandes_docs import servidor_mcp as s
    from petroandes_docs.indice import Indice
    Indice.construir(cfg_aislado, log=lambda *_: None).cliente.close()
    monkeypatch.setattr(s, "cargar", lambda: cfg_aislado)
    monkeypatch.setattr(s, "_INDICE", [])
    errores, abiertos = [], []

    def abrir():
        try:
            abiertos.append(s._indice())
        except Exception as e:  # pragma: no cover - es lo que la prueba descarta
            errores.append(e)

    hilos = [threading.Thread(target=abrir) for _ in range(4)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert not errores
    assert len({id(i) for i in abiertos}) == 1
