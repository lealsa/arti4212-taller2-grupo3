"""Intérprete de la pregunta con un LLM local (alternativa A1 de ADR-008): solo reescribe la pregunta."""
from __future__ import annotations

import json
import re
import urllib.request

PROMPT_SISTEMA = (
    "Eres un componente de un buscador de documentos técnicos de una empresa que transporta "
    "hidrocarburos por oleoducto (manuales, procedimientos, resoluciones, actas y fichas de equipos). "
    "Tu única tarea es reescribir la pregunta de un operador con el vocabulario formal y técnico que "
    "usarían esos documentos, para que el buscador la encuentre.\n"
    "Reglas:\n"
    "1. Conserva exactamente los códigos, números, nombres de tramos, lugares, equipos y dependencias.\n"
    "2. No agregues datos, cifras, nombres ni supuestos que no estén en la pregunta.\n"
    "3. No respondas la pregunta.\n"
    "4. Devuelve solo la pregunta reescrita, en una sola línea, en español."
)


def _limpiar(t: str) -> str:
    t = t.strip().splitlines()[0] if t.strip() else ""
    t = re.sub(r"^(pregunta reescrita|reescritura|respuesta)\s*:\s*", "", t, flags=re.IGNORECASE)
    return t.strip().strip('"«»').strip()


class InterpreteHF:
    def __init__(self, modelo: str = "Qwen/Qwen2.5-1.5B-Instruct", max_tokens: int = 64):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        self._torch = torch
        self._tok = AutoTokenizer.from_pretrained(modelo)
        self._m = AutoModelForCausalLM.from_pretrained(modelo)
        self._m.eval()
        self.max_tokens = max_tokens
        self.nombre = f"hf:{modelo}"
        self._cache: dict[str, str] = {}

    def reescribir(self, pregunta: str) -> str:
        if pregunta in self._cache:
            return self._cache[pregunta]
        mensajes = [{"role": "system", "content": PROMPT_SISTEMA}, {"role": "user", "content": pregunta}]
        enc = self._tok.apply_chat_template(mensajes, add_generation_prompt=True, return_tensors="pt", return_dict=True)
        with self._torch.no_grad():
            out = self._m.generate(**enc, max_new_tokens=self.max_tokens, do_sample=False,
                                   pad_token_id=self._tok.eos_token_id)
        texto = _limpiar(self._tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True))
        self._cache[pregunta] = texto
        return texto


class InterpreteOllama:
    def __init__(self, modelo: str, url: str = "http://127.0.0.1:11434"):
        self.modelo, self.url, self.nombre = modelo, url.rstrip("/"), f"ollama:{modelo}"
        self._cache: dict[str, str] = {}

    def reescribir(self, pregunta: str) -> str:
        if pregunta in self._cache:
            return self._cache[pregunta]
        cuerpo = json.dumps({"model": self.modelo, "system": PROMPT_SISTEMA, "prompt": pregunta, "stream": False,
                             "options": {"temperature": 0, "seed": 0, "num_predict": 64}}).encode()
        req = urllib.request.Request(f"{self.url}/api/generate", data=cuerpo, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            texto = _limpiar(json.loads(r.read())["response"])
        self._cache[pregunta] = texto
        return texto


class InterpreteFijo:
    """Para pruebas: reescrituras dadas de antemano."""
    def __init__(self, mapa: dict[str, str]):
        self.mapa, self.nombre = mapa, "fijo"

    def reescribir(self, pregunta: str) -> str:
        return self.mapa.get(pregunta, pregunta)


def crear(spec: str | None):
    if not spec or spec == "ninguno":
        return None
    proveedor, _, modelo = spec.partition(":")
    if proveedor == "hf":
        return InterpreteHF(modelo or "Qwen/Qwen2.5-1.5B-Instruct")
    if proveedor == "ollama":
        return InterpreteOllama(modelo)
    raise ValueError(f"Intérprete desconocido: {spec}")
