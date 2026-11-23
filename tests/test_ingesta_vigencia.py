from pathlib import Path

import pytest
import yaml

from petroandes_docs.extraccion import extraer_pdf
from petroandes_docs.vigencia import ConflictoVigencia, cargar_contrato, cargar_registro, conciliar, proponer


@pytest.fixture(scope="module")
def docs(cfg):
    return [extraer_pdf(p) for p in sorted(cfg.corpus_pdf.rglob("*.pdf"))]


def test_extrae_los_19_documentos_con_cabecera(docs):
    assert len(docs) == 19
    for d in docs:
        assert d.codigo and d.fecha_emision and d.tipo and d.secciones, d.archivo


def test_filas_de_tabla_autocontenidas(docs):
    d = next(d for d in docs if d.clave == "PRO-OPE-012@v3")
    s3 = next(s for s in d.secciones if s.id == "3")
    fila = next(u for u in s3.unidades if u.startswith("Tramo: Ayacucho"))
    assert "Umbral de alarma (psi): 1.100" in fila and "Ventana de evaluación: 15 minutos" in fila


def test_reglas_proponen_los_cuatro_derogados(docs, cfg):
    prop = proponer(docs, cargar_contrato(cfg.contrato))
    derogados = {k: p.regla for k, p in prop.items() if p.estado == "derogado"}
    assert derogados == {"PRO-MED-007@v1": "R1", "PRO-OPE-012@v2": "R1", "PRO-SEG-009@v1": "R2", "RES-CREG-0112-2021@v—": "R3"}


def test_manuales_quedan_pendientes_de_certificacion(docs, cfg):
    final, _ = conciliar(docs, cargar_contrato(cfg.contrato), cargar_registro(cfg.registro))
    assert {k for k, v in final.items() if v.estado == "pendiente_certificacion"} == {"MAN-OPE-001@v3", "MAN-OPE-004@v2", "MAN-MTO-002@v1"}


def test_registro_que_contradice_la_evidencia_detiene_la_ingesta(docs, cfg, tmp_path):
    data = yaml.safe_load(cfg.registro.read_text(encoding="utf-8"))
    for e in data["documentos"]:
        if e["codigo"] == "PRO-OPE-012" and str(e["version"]) == "2":
            e["estado"] = "vigente"
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConflictoVigencia):
        conciliar(docs, cargar_contrato(cfg.contrato), cargar_registro(p))


def test_documento_sin_registro_nunca_queda_vigente(docs, cfg, tmp_path):
    data = yaml.safe_load(cfg.registro.read_text(encoding="utf-8"))
    data["documentos"] = [e for e in data["documentos"] if e["codigo"] != "PRO-HSE-003"]
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    final, avisos = conciliar(docs, cargar_contrato(cfg.contrato), cargar_registro(p))
    assert final["PRO-HSE-003@v4"].estado == "pendiente_certificacion"
    assert any("PRO-HSE-003" in a for a in avisos)
