import re

import pytest

from petroandes_docs.composicion import componer
from petroandes_docs.recuperacion import buscar

CONSULTAS = [
    "umbral de alarma de presión Ayacucho Coveñas",
    "tolerancia de conciliación volumétrica",
    "plazo de reporte a la autoridad competente por pérdida de producto",
    "incertidumbre máxima admisible transferencia de custodia",
    "PRO-OPE-012 versión 2",
]


@pytest.mark.parametrize("modo", ["hibrido", "semantico", "lexico"])
@pytest.mark.parametrize("consulta", CONSULTAS)
def test_nunca_recupera_derogados_por_defecto(indice, consulta, modo):
    for r in buscar(indice, consulta, k=10, modo=modo):
        assert r.payload["estado_vigencia"] != "derogado", r.id


def test_sin_filtro_si_aparecen_derogados(indice):
    ids = [r.id for r in buscar(indice, "umbral de alarma de presión Ayacucho Coveñas", k=10, filtro="ninguno")]
    assert "PRO-OPE-012@v2#3" in ids


def test_fecha_de_referencia_devuelve_lo_que_regia(indice):
    ids = [r.id for r in buscar(indice, "umbral de alarma de presión Ayacucho Coveñas", k=5, fecha_referencia="2025-08-15")]
    assert "PRO-OPE-012@v2#3" in ids and "PRO-OPE-012@v3#3" not in ids


def test_hibrida_encuentra_codigos_que_la_semantica_pierde(indice):
    lex = [r.id for r in buscar(indice, "orden OT-2021-03117", k=3, modo="lexico")]
    hib = [r.id for r in buscar(indice, "orden OT-2021-03117", k=3, modo="hibrido")]
    assert lex[0] == "FIC-ACT-P101@v2#3" and "FIC-ACT-P101@v2#3" in hib


def test_toda_afirmacion_tiene_cita_documento_version_seccion(indice):
    r = componer(indice, "¿Cuál es la tolerancia de conciliación volumétrica de un tramo?")
    assert r.estado == "respondida" and r.afirmaciones
    for a in r.afirmaciones:
        assert re.match(r"^[A-Z]+-[A-Z]+-[A-Z0-9-]+( v\d+)? §.+$", a.cita)
    assert "0,5 %" in " ".join(a.texto for a in r.afirmaciones)


def test_negativa_honesta_fuera_del_corpus(indice):
    assert componer(indice, "¿Cuál es el precio del barril de crudo Brent hoy?").estado == "sin_respaldo"


def test_pregunta_por_derogado_advierte_y_responde_con_el_vigente(indice):
    r = componer(indice, "Según el PRO-SEG-009, ¿en cuánto tiempo se reporta a la autoridad competente una pérdida de producto?")
    assert any("derogado" in w for w in r.advertencias)
    assert all(a.codigo != "PRO-SEG-009" for a in r.afirmaciones)
    assert "24 horas" in " ".join(a.texto for a in r.afirmaciones)
