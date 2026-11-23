"""Modelo canónico del corpus: documentos, secciones y fragmentos con sus metadatos de gobierno."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

EstadoVigencia = Literal["vigente", "derogado", "pendiente_certificacion", "no_normativo"]
ClaseDocumento = Literal["manual", "procedimiento", "normativa", "acta", "comunicacion_proveedor", "ficha_activo"]


@dataclass
class Seccion:
    id: str                 # "3", "Art. 2", "Anexo"
    titulo: str             # "3. Criterios de detección"
    texto: str              # texto normalizado (tablas como filas «columna: valor»)
    pagina: int = 1
    unidades: list[str] = field(default_factory=list)  # cláusulas, viñetas y filas de tabla


@dataclass
class DocumentoExtraido:
    codigo: str
    version: str            # "3" o "—"
    titulo: str
    emisor: str
    fecha_emision: str      # AAAA-MM-DD
    tipo: str               # como lo declara la cabecera
    area_emisora: str
    activo: str
    reemplaza_a: str        # "—" si no aplica
    archivo: str
    sha256: str
    secciones: list[Seccion] = field(default_factory=list)

    @property
    def clave(self) -> str:
        return f"{self.codigo}@v{self.version}"


@dataclass
class Vigencia:
    codigo: str
    version: str
    estado: EstadoVigencia
    vigente_desde: str
    vigente_hasta: Optional[str]
    regla: str
    evidencia: list[str]
    certificado_por: str
    fecha_certificacion: Optional[str]
    reemplazado_por: Optional[str] = None
    modo_certificacion: str = "simulada-prototipo"
    advertencia: Optional[str] = None


@dataclass
class Fragmento:
    """Unidad que se indexa: una sección de un documento, con sus metadatos de gobierno."""
    id: str                 # PRO-OPE-012@v3#3
    codigo: str
    version: str
    titulo_documento: str
    clase: ClaseDocumento
    naturaleza: Literal["normativo", "no_normativo"]
    origen: Literal["interno", "externo"]
    area_emisora: str
    emisor: str
    fecha_emision: str
    seccion: str
    titulo_seccion: str
    texto: str
    unidades: list[str]
    pagina: int
    archivo: str
    sha256_documento: str
    sha256_fragmento: str
    estado_vigencia: EstadoVigencia
    vigente_desde: int      # AAAAMMDD, para filtrar por rango
    vigente_hasta: Optional[int]
    regla_vigencia: str
    certificado_por: str
    reemplazado_por: Optional[str]
    cuarentena: bool = False
    motivo_cuarentena: Optional[str] = None
    advertencia_vigencia: Optional[str] = None

    def payload(self) -> dict:
        return asdict(self)

    @property
    def cita(self) -> str:
        v = f" v{self.version}" if self.version not in ("—", "") else ""
        return f"{self.codigo}{v} §{self.seccion}"
