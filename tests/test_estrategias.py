"""ADR-008: flujo y guardas de las estrategias con dobles deterministas de los modelos."""
from petroandes_docs.composicion import Estrategia, componer
from petroandes_docs.decisores import DecisorFijo
from petroandes_docs.guardas import conserva_entidades, entidades
from petroandes_docs.interpretacion import InterpreteFijo

P_PARADA = "¿Después de cuánto tiempo apagada se considera que una bomba necesita arranque en frío?"


def test_entidades_tramo_codigo_y_pk():
    assert entidades("¿Umbral del tramo Ayacucho – Coveñas?") == {"ayacucho-covenas"}
    assert entidades("¿Qué válvula está en el K 061+800?") == {"k 061+800"}
    assert entidades("Según el PRO-SEG-015, ¿plazo?") == {"pro-seg-015"}
    assert entidades("¿Cuál es la tolerancia de conciliación?") == set()


def test_guarda_rechaza_reescritura_que_cambia_entidades_o_agrega_cifras():
    assert conserva_entidades("umbral del tramo Cartagena – Barranquilla", "umbral de alarma de un tramo")[0] is False
    assert conserva_entidades("¿plazo de cierre?", "plazo de cierre de 15 días")[0] is False
    assert conserva_entidades("¿bomba P-101?", "datos de la bomba P-101")[0] is True


def test_a1_reescritura_aceptada_rescata_una_parafrasis(indice):
    base = componer(indice, P_PARADA)
    interp = InterpreteFijo({P_PARADA: "¿Tras cuántas horas de parada una unidad de bombeo requiere arranque en frío?"})
    r = componer(indice, P_PARADA, estrategia=Estrategia("A1", interprete=interp, guarda=True))
    assert r.interpretacion["aceptada"]
    assert r.estado == "respondida"
    assert any("setenta y dos horas" in a.texto for a in r.afirmaciones)
    assert base.estado == "sin_respaldo"          # la línea base no la rescata


def test_a1_reescritura_descartada_si_pierde_el_tramo(indice):
    q = "¿Cuál es el umbral de alarma de presión del tramo Cartagena – Barranquilla?"
    interp = InterpreteFijo({q: "¿Cuál es el umbral de alarma de presión de un tramo del oleoducto?"})
    r = componer(indice, q, estrategia=Estrategia("A1", interprete=interp, guarda=True))
    assert r.interpretacion["aceptada"] is False
    assert r.estado == "sin_respaldo"


def test_guarda_impide_responder_con_otro_tramo(indice):
    q = "¿Cuál es el umbral de alarma de presión del tramo Barrancabermeja – Coveñas?"
    r = componer(indice, q, estrategia=Estrategia("A0G", guarda=True), umbral=0.0)
    assert r.estado == "sin_respaldo"


def test_a2_decide_por_el_puntaje_del_decisor_y_respeta_el_umbral(indice):
    dec = DecisorFijo({"setenta y dos horas": 0.9}, defecto=0.05)
    r = componer(indice, P_PARADA, estrategia=Estrategia("A2", decisor=dec, umbral=0.5, guarda=True))
    assert r.estado == "respondida" and "setenta y dos horas" in r.afirmaciones[0].texto
    r = componer(indice, P_PARADA, estrategia=Estrategia("A2", decisor=DecisorFijo({}, 0.2), umbral=0.5, guarda=True))
    assert r.estado == "sin_respaldo"


def test_estrategia_por_defecto_es_la_linea_base(indice):
    q = "¿Cuál es el umbral de alarma de presión en el tramo Ayacucho – Coveñas?"
    a, b = componer(indice, q), componer(indice, q, estrategia=Estrategia())
    assert [x.texto for x in a.afirmaciones] == [x.texto for x in b.afirmaciones]


def test_adicionales_del_mismo_documento_no_mezcla_maop_con_umbral(indice):
    q = "¿Cuál es la MAOP del tramo Ayacucho – Coveñas?"
    dec = DecisorFijo({"MAOP (psi): 1.250": 0.99, "Umbral de alarma (psi): 1.100": 0.95}, defecto=0.0)
    mezcla = componer(indice, q, estrategia=Estrategia("x", decisor=dec, umbral=0.5, guarda=True))
    limpia = componer(indice, q, estrategia=Estrategia("y", decisor=dec, umbral=0.5, guarda=True, adicionales="mismo_documento"))
    assert any("1.100" in a.texto for a in mezcla.afirmaciones)
    assert all("1.100" not in a.texto for a in limpia.afirmaciones)
    assert "1.250" in limpia.afirmaciones[0].texto


def test_modo_degradado_explicito_si_el_decisor_no_carga(indice, monkeypatch):
    from petroandes_docs import estrategias
    monkeypatch.setenv("PETROANDES_ESTRATEGIA", "A2")
    monkeypatch.setenv("PETROANDES_DECISOR", "crossencoder:/no/existe")
    est, aviso = estrategias.por_defecto(indice)
    assert est.nombre == "A0G" and est.guarda and "degradado" in aviso


def test_una_sola_frase_en_la_estrategia_elegida(indice):
    q = "¿Cuál es el límite de alarma de la temperatura de cojinetes de la bomba P-101?"
    dec = DecisorFijo({"Temperatura de cojinetes": 0.99, "Vibración global": 0.95}, defecto=0.0)
    r = componer(indice, q, estrategia=Estrategia("A2", decisor=dec, umbral=0.5, guarda=True, max_afirmaciones=1))
    assert len(r.afirmaciones) == 1 and "82" in r.afirmaciones[0].texto


def test_especificacion_con_revision_fijada():
    from petroandes_docs.revisiones import separar, resolver
    assert separar("intfloat/multilingual-e5-small@0a1b2c") == ("intfloat/multilingual-e5-small", "0a1b2c")
    assert separar("BAAI/bge-reranker-v2-m3") == ("BAAI/bge-reranker-v2-m3", None)
    # sin copia local ni red, la revisión declarada se conserva tal cual (nunca se inventa un commit)
    assert resolver("organizacion-inexistente/modelo-inexistente", "0a1b2c") == "0a1b2c"
    assert resolver("organizacion-inexistente/modelo-inexistente") == "main"
