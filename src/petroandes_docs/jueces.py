"""Jueces del arnés: laya (anclaje con `noul`, pertinencia con `choice`) y el juez léxico alterno (ADR-006)."""
from __future__ import annotations

import re

from .texto import normalizar_espacios, plegar

PREGUNTA_ANCLAJE = {
    "anclada": {
        "type": "noul",
        "instructions": ("¿El fragmento respalda por completo la afirmación, sin que la afirmación agregue datos, "
                         "cifras o conclusiones que no estén en el fragmento?"),
        "criteria": {"false": "la afirmación agrega o contradice algo del fragmento",
                     "true": "todo lo que dice la afirmación está en el fragmento"},
    }
}
PREGUNTA_PERTINENCIA = {
    "pertinencia": {
        "type": "choice",
        "instructions": "¿Qué tan pertinente es el fragmento para responder la pregunta?",
        "criteria": {"pertinente": "el fragmento contiene la respuesta a la pregunta",
                     "parcial": "el fragmento trata el tema pero no contiene la respuesta",
                     "no_pertinente": "el fragmento no trata lo que se pregunta"},
    }
}
PREGUNTA_RESPONDE = {
    "responde": {
        "type": "noul",
        "instructions": "¿La respuesta contesta lo que se pregunta (el dato, plazo, responsable o condición pedidos)?",
        "criteria": {"false": "la respuesta habla del tema pero no contesta lo que se pregunta",
                     "true": "la respuesta contiene lo que se pregunta"},
    }
}
PREGUNTA_EQUIVALENTE = {
    "equivalente": {
        "type": "noul",
        "instructions": ("¿La pregunta reescrita pide la misma información que la original, sin cambiar lugares, "
                         "equipos, cifras, documentos ni el alcance?"),
        "criteria": {"false": "la reescritura cambia o amplía lo que se pregunta",
                     "true": "la reescritura pide exactamente lo mismo"},
    }
}


class JuezLaya:
    nombre = "laya"

    def __init__(self, modelo: str = "ml", device: str | None = None):
        import laya
        self._agent = laya.load(modelo, device=device)
        self.nombre = f"laya:{modelo}"

    def anclaje(self, afirmacion: str, fragmento: str, **_) -> float:
        out = self._agent.predict({"fragmento": fragmento, "afirmacion": afirmacion}, PREGUNTA_ANCLAJE)
        return float(out["answers"]["anclada"]["noul"])

    def pertinencia(self, pregunta: str, fragmento: str, **_) -> str:
        out = self._agent.predict({"pregunta": pregunta, "fragmento": fragmento}, PREGUNTA_PERTINENCIA)
        return out["answers"]["pertinencia"]["choice"]

    def responde(self, pregunta: str, respuesta: str) -> float:
        out = self._agent.predict({"pregunta": pregunta, "respuesta": respuesta}, PREGUNTA_RESPONDE)
        return float(out["answers"]["responde"]["noul"])

    def equivalente(self, original: str, reescrita: str) -> float:
        out = self._agent.predict({"pregunta_original": original, "pregunta_reescrita": reescrita}, PREGUNTA_EQUIVALENTE)
        return float(out["answers"]["equivalente"]["noul"])


_CIFRA = re.compile(r"\d+(?:[.,]\d+)*")


class JuezLexico:
    nombre = "lexico"

    def anclaje(self, afirmacion: str, fragmento: str, **_) -> float:
        a, f = normalizar_espacios(plegar(afirmacion)), normalizar_espacios(plegar(fragmento))
        if a and a in f:
            return 1.0
        cifras = _CIFRA.findall(a)
        if cifras and not all(c in f for c in cifras):
            return 0.0
        palabras = [w for w in re.findall(r"\w+", a) if len(w) > 2]
        return sum(w in f for w in palabras) / len(palabras) if palabras else 0.0

    def pertinencia(self, pregunta: str, fragmento: str, *, frag_id: str = "", esperados: list[str] | None = None, **_) -> str:
        esperados = esperados or []
        if frag_id in esperados:
            return "pertinente"
        doc = frag_id.split("#")[0]
        if any(e.split("#")[0] == doc for e in esperados):
            return "parcial"
        return "no_pertinente"

    def responde(self, pregunta: str, respuesta: str) -> None:
        return None          # sin modelo no hay juicio de si contesta; lo mide la desviación con hechos de oro

    def equivalente(self, original: str, reescrita: str) -> None:
        return None


def crear(nombre: str):
    if nombre == "laya":
        return JuezLaya()
    if nombre == "lexico":
        return JuezLexico()
    raise ValueError(nombre)
