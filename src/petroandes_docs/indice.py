"""Índice en Qdrant: carga inicial y sincronización, con vectores densos y BM25 en una sola colección.

El manifiesto (data/manifiesto.json) guarda la huella del modelo, el SHA-256 de cada PDF y las
versiones del contrato y del registro de vigencia con que se indexó.
"""
from __future__ import annotations

import hashlib
import json
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path

import yaml
from qdrant_client import QdrantClient, models

from . import embeddings as emb_mod
from .config import Config
from .extraccion import extraer_pdf, sha256
from .lexico import ModeloLexico
from .modelos import Fragmento
from .particion import fragmentar, texto_para_indexar
from .vigencia import cargar_contrato, cargar_registro, conciliar

warnings.filterwarnings("ignore", message=".*Payload indexes have no effect in the local Qdrant.*")

CAMPOS_INDEXADOS = {
    "estado_vigencia": models.PayloadSchemaType.KEYWORD, "codigo": models.PayloadSchemaType.KEYWORD,
    "clase": models.PayloadSchemaType.KEYWORD, "version": models.PayloadSchemaType.KEYWORD,
    "vigente_desde": models.PayloadSchemaType.INTEGER, "vigente_hasta": models.PayloadSchemaType.INTEGER,
    "cuarentena": models.PayloadSchemaType.BOOL,
}


class ModeloIncompatible(Exception):
    """El modelo de embeddings configurado no es el que produjo los vectores del índice."""


def _id_punto(frag_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"petroandes:{frag_id}"))


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cliente(cfg: Config) -> QdrantClient:
    if cfg.qdrant_url:
        return QdrantClient(url=cfg.qdrant_url)
    cfg.qdrant_path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(cfg.qdrant_path))


class Indice:
    def __init__(self, cfg: Config, cliente: QdrantClient, manifiesto: dict, embedder, lexico: ModeloLexico):
        self.cfg, self.cliente, self.manifiesto, self.embedder, self.lexico = cfg, cliente, manifiesto, embedder, lexico
        self._registro_cache = None

    @property
    def coleccion(self) -> str:
        return self.manifiesto["coleccion"]

    @classmethod
    def abrir(cls, cfg: Config, cliente: QdrantClient | None = None) -> "Indice":
        if not cfg.manifiesto.exists():
            raise FileNotFoundError("No hay índice: ejecute `petroandes-docs ingestar` primero.")
        man = json.loads(cfg.manifiesto.read_text(encoding="utf-8"))
        e = man["embeddings"]
        if cfg.embeddings != e["especificacion"]:
            raise ModeloIncompatible(
                f"El índice se construyó con «{e['especificacion']}» y la configuración pide «{cfg.embeddings}». "
                "Vectores de modelos distintos no son comparables: reindexe con `petroandes-docs ingestar`.")
        embedder = emb_mod.crear(e["especificacion"], e.get("estado"))
        if embedder.huella != e["huella"]:
            raise ModeloIncompatible(f"Huella del modelo cargado ({embedder.huella}) distinta de la del índice ({e['huella']}).")
        return cls(cfg, cliente or _cliente(cfg), man, embedder, ModeloLexico.desde_dict(man["lexico"]))

    @classmethod
    def construir(cls, cfg: Config, cliente: QdrantClient | None = None, log=print) -> "Indice":
        contrato = cargar_contrato(cfg.contrato)
        registro = cargar_registro(cfg.registro)
        pdfs = sorted(cfg.corpus_pdf.rglob("*.pdf"))
        if not pdfs:
            raise FileNotFoundError(f"No hay PDF en {cfg.corpus_pdf}")
        docs = [extraer_pdf(p) for p in pdfs]
        log(f"Extraídos {len(docs)} documentos de {cfg.corpus_pdf}")
        vigencias, avisos = conciliar(docs, contrato, registro)
        for a in avisos:
            log(f"AVISO de gobierno: {a}")
        fragmentos: list[Fragmento] = []
        for d in docs:
            fragmentos.extend(fragmentar(d, vigencias[d.clave], contrato))
        textos = [texto_para_indexar(f) for f in fragmentos]
        lexico = ModeloLexico.ajustar(textos)
        embedder = emb_mod.crear(cfg.embeddings)
        if hasattr(embedder, "ajustar_idf"):
            embedder.ajustar_idf(textos)
        coleccion = "corpus_petroandes__" + hashlib.sha256(embedder.huella.encode()).hexdigest()[:10]
        cliente = cliente or _cliente(cfg)
        if cliente.collection_exists(coleccion):
            cliente.delete_collection(coleccion)
        cliente.create_collection(
            coleccion,
            vectors_config={"denso": models.VectorParams(size=embedder.dimension, distance=models.Distance.COSINE)},
            sparse_vectors_config={"lexico": models.SparseVectorParams()},
        )
        for campo, tipo in CAMPOS_INDEXADOS.items():
            cliente.create_payload_index(coleccion, campo, tipo)
        densos = embedder.documentos(textos)
        puntos = []
        for f, t, v in zip(fragmentos, textos, densos):
            idx, val = lexico.vector_documento(t)
            puntos.append(models.PointStruct(id=_id_punto(f.id), payload=f.payload(),
                                             vector={"denso": v, "lexico": models.SparseVector(indices=idx, values=val)}))
        cliente.upsert(coleccion, points=puntos, wait=True)
        n_cuar = sum(f.cuarentena for f in fragmentos)
        log(f"Indexados {len(fragmentos)} fragmentos en «{coleccion}» con {embedder.huella}; {n_cuar} en cuarentena.")
        contrato_v = contrato.get("version_contrato")
        registro_v = yaml.safe_load(cfg.registro.read_text(encoding="utf-8")).get("version_registro")
        man = {
            "version_manifiesto": 1, "creado": _ahora(), "actualizado": _ahora(), "coleccion": coleccion,
            "embeddings": {"especificacion": cfg.embeddings, "huella": embedder.huella, "estado": emb_mod.estado_de(embedder)},
            "lexico": lexico.a_dict(), "contrato_version": contrato_v, "registro_version": registro_v,
            "documentos": {d.clave: {"archivo": str(Path(d.archivo).relative_to(cfg.raiz)) if Path(d.archivo).is_relative_to(cfg.raiz) else d.archivo,
                                     "sha256": d.sha256, "estado": vigencias[d.clave].estado,
                                     "fragmentos": [f.id for f in fragmentos if f.codigo == d.codigo and f.version == d.version]}
                           for d in docs},
            "avisos_gobierno": avisos,
        }
        cfg.datos.mkdir(parents=True, exist_ok=True)
        cfg.manifiesto.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
        return cls(cfg, cliente, man, embedder, lexico)

    def sincronizar(self, log=print) -> dict:
        """Detecta PDF nuevos, modificados o retirados y cambios del registro de vigencia.

        - Cambio solo de vigencia: actualiza el payload de los fragmentos (sin recalcular vectores).
        - Documento nuevo o modificado: re-extrae, re-fragmenta y re-embebe solo ese documento.
        - Documento retirado del corpus: borra sus fragmentos.
        Devuelve un resumen de lo que cambió.
        """
        cfg = self.cfg
        contrato = cargar_contrato(cfg.contrato)
        registro = cargar_registro(cfg.registro)
        actuales = {str(p): sha256(p) for p in sorted(cfg.corpus_pdf.rglob("*.pdf"))}
        docs = [extraer_pdf(Path(p)) for p in actuales]
        vigencias, avisos = conciliar(docs, contrato, registro)
        previos = self.manifiesto["documentos"]
        resumen = {"nuevos": [], "modificados": [], "retirados": [], "vigencia_cambiada": []}
        claves = set()
        for d in docs:
            claves.add(d.clave)
            prev = previos.get(d.clave)
            v = vigencias[d.clave]
            if prev is None or prev["sha256"] != d.sha256:
                if prev is not None:
                    self._borrar_documento(d.codigo, d.version)
                frags = fragmentar(d, v, contrato)
                textos = [texto_para_indexar(f) for f in frags]
                densos = self.embedder.documentos(textos)
                puntos = []
                for f, t, dv in zip(frags, textos, densos):
                    idx, val = self.lexico.vector_documento(t)
                    puntos.append(models.PointStruct(id=_id_punto(f.id), payload=f.payload(), vector={
                        "denso": dv, "lexico": models.SparseVector(indices=idx, values=val)}))
                self.cliente.upsert(self.coleccion, wait=True, points=puntos)
                resumen["nuevos" if prev is None else "modificados"].append(d.clave)
                previos[d.clave] = {"archivo": d.archivo, "sha256": d.sha256, "estado": v.estado,
                                    "fragmentos": [f.id for f in frags]}
            elif prev["estado"] != v.estado:
                self.cliente.set_payload(self.coleccion, wait=True, payload={
                    "estado_vigencia": v.estado, "regla_vigencia": v.regla, "certificado_por": v.certificado_por,
                    "reemplazado_por": v.reemplazado_por, "advertencia_vigencia": v.advertencia,
                    "vigente_hasta": int(v.vigente_hasta.replace("-", "")) if v.vigente_hasta else None},
                    points=self._filtro_documento(d.codigo, d.version))
                resumen["vigencia_cambiada"].append(f"{d.clave}: {prev['estado']} → {v.estado}")
                prev["estado"] = v.estado
        for clave in list(previos):
            if clave not in claves:
                cod, ver = clave.split("@v")
                self._borrar_documento(cod, ver)
                del previos[clave]
                resumen["retirados"].append(clave)
        self.manifiesto["actualizado"] = _ahora()
        self.manifiesto["registro_version"] = yaml.safe_load(cfg.registro.read_text(encoding="utf-8")).get("version_registro")
        self.manifiesto["avisos_gobierno"] = avisos
        cfg.manifiesto.write_text(json.dumps(self.manifiesto, ensure_ascii=False, indent=1), encoding="utf-8")
        self._registro_cache = None
        for k, v in resumen.items():
            if v:
                log(f"{k}: {v}")
        return resumen

    def _filtro_documento(self, codigo: str, version: str) -> models.Filter:
        return models.Filter(must=[models.FieldCondition(key="codigo", match=models.MatchValue(value=codigo)),
                                   models.FieldCondition(key="version", match=models.MatchValue(value=version))])

    def _borrar_documento(self, codigo: str, version: str) -> None:
        self.cliente.delete(self.coleccion, points_selector=models.FilterSelector(filter=self._filtro_documento(codigo, version)), wait=True)

    def registro(self) -> dict:
        if self._registro_cache is None:
            self._registro_cache = cargar_registro(self.cfg.registro)
        return self._registro_cache

    def fragmento(self, codigo: str, version: str, seccion: str) -> dict | None:
        pts, _ = self.cliente.scroll(self.coleccion, limit=50, with_payload=True, scroll_filter=models.Filter(must=[
            models.FieldCondition(key="codigo", match=models.MatchValue(value=codigo)),
            models.FieldCondition(key="version", match=models.MatchValue(value=version))]))
        for p in pts:
            if p.payload["seccion"].lower() == seccion.lower() or p.payload["seccion"].lower().replace("art. ", "") == seccion.lower().replace("art. ", "").replace("artículo ", ""):
                return p.payload
        return None

    def secciones_de(self, codigo: str, version: str) -> list[str]:
        pts, _ = self.cliente.scroll(self.coleccion, limit=50, with_payload=["seccion"],
                                     scroll_filter=self._filtro_documento(codigo, version))
        return [p.payload["seccion"] for p in pts]

    def documentos(self) -> list[dict]:
        reg = self.registro()
        salida = []
        for clave, d in self.manifiesto["documentos"].items():
            v = reg.get(clave)
            cod, ver = clave.split("@v")
            salida.append({"codigo": cod, "version": ver, "estado_vigencia": d["estado"],
                           "reemplazado_por": v.reemplazado_por if v else None,
                           "certificado_por": v.certificado_por if v else "sin certificar",
                           "fragmentos": len(d["fragmentos"])})
        return sorted(salida, key=lambda x: (x["codigo"], x["version"]))
