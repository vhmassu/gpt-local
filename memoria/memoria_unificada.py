"""Memoria unificada para todos los agentes locales (Qdrant + Ollama).

Una sola colección en Qdrant; cada recuerdo lleva el nombre del agente que lo
guardó, así cualquier agente puede buscar en lo que saben los demás.

Configuración (variables de entorno o ~/.memoria-unificada/config.env):
  QDRANT_URL          http://localhost:6333
  QDRANT_API_KEY      (opcional)
  MEMORIA_COLECCION   memoria_unificada
  OLLAMA_URL          http://localhost:11434
  EMBED_MODEL         nomic-embed-text
  MEMORIA_AGENTE      nombre del agente que escribe (gemi, openclaw, hermes, antigravity)

Solo depende de `requests`.
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

CONFIG_PATH = Path.home() / ".memoria-unificada" / "config.env"
NAMESPACE = uuid.UUID("6f1c2a52-3d4e-4b8a-9a51-6d656d6f7269")
AGENTES = ("gemi", "openclaw", "hermes", "antigravity")


def _cargar_config() -> None:
    if not CONFIG_PATH.exists():
        return
    for linea in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_cargar_config()


def _cfg(nombre: str, defecto: str = "") -> str:
    return os.environ.get(nombre, defecto)


QDRANT_URL = _cfg("QDRANT_URL", "http://localhost:6333").rstrip("/")
QDRANT_API_KEY = _cfg("QDRANT_API_KEY")
COLECCION = _cfg("MEMORIA_COLECCION", "memoria_unificada")
OLLAMA_URL = _cfg("OLLAMA_URL", "http://localhost:11434").rstrip("/")
EMBED_MODEL = _cfg("EMBED_MODEL", "nomic-embed-text")
TIMEOUT = 30


class MemoriaError(RuntimeError):
    pass


# ---------------------------------------------------------------- HTTP / Qdrant
def _qdrant(metodo: str, ruta: str, **kw):
    headers = {"api-key": QDRANT_API_KEY} if QDRANT_API_KEY else {}
    try:
        r = requests.request(metodo, f"{QDRANT_URL}{ruta}", headers=headers, timeout=TIMEOUT, **kw)
    except requests.RequestException as e:
        raise MemoriaError(f"No pude conectar con Qdrant en {QDRANT_URL}: {e}") from e
    if r.status_code == 404:
        return None
    if not r.ok:
        raise MemoriaError(f"Qdrant {metodo} {ruta} -> {r.status_code}: {r.text[:300]}")
    return r.json().get("result")


def embedding(texto: str) -> list[float]:
    """Vector del texto usando Ollama (local, gratis)."""
    try:
        r = requests.post(f"{OLLAMA_URL}/api/embed",
                          json={"model": EMBED_MODEL, "input": texto}, timeout=TIMEOUT)
        if r.status_code == 404:  # Ollama viejo
            r = requests.post(f"{OLLAMA_URL}/api/embeddings",
                              json={"model": EMBED_MODEL, "prompt": texto}, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()["embedding"]
        r.raise_for_status()
        return r.json()["embeddings"][0]
    except requests.RequestException as e:
        raise MemoriaError(
            f"No pude generar el embedding con Ollama ({OLLAMA_URL}, modelo {EMBED_MODEL}). "
            f"¿Está corriendo Ollama y descargado el modelo? Detalle: {e}") from e


def colecciones() -> list[str]:
    res = _qdrant("GET", "/collections") or {}
    return [c["name"] for c in res.get("collections", [])]


def info_coleccion(nombre: str = COLECCION):
    return _qdrant("GET", f"/collections/{nombre}")


def _dimension_coleccion(info) -> int | None:
    vectores = info["config"]["params"]["vectors"]
    if isinstance(vectores, dict) and "size" in vectores:
        return vectores["size"]
    return None  # vectores con nombre: no soportado


_lista = False


def asegurar_coleccion() -> None:
    """Crea la colección si no existe y valida que la dimensión coincida."""
    global _lista
    if _lista:
        return
    dim = len(embedding("prueba de dimensión"))
    info = info_coleccion()
    if info is None:
        _qdrant("PUT", f"/collections/{COLECCION}",
                json={"vectors": {"size": dim, "distance": "Cosine"}})
        for campo in ("agente", "tipo"):
            _qdrant("PUT", f"/collections/{COLECCION}/index",
                    json={"field_name": campo, "field_schema": "keyword"})
    else:
        actual = _dimension_coleccion(info)
        if actual is None:
            raise MemoriaError(f"La colección '{COLECCION}' usa vectores con nombre; usa otra colección.")
        if actual != dim:
            raise MemoriaError(
                f"La colección '{COLECCION}' tiene vectores de {actual} dimensiones, pero el modelo "
                f"'{EMBED_MODEL}' genera {dim}. Usa el mismo modelo con el que se creó o cambia "
                f"MEMORIA_COLECCION en {CONFIG_PATH}.")
    _lista = True


# ---------------------------------------------------------------- API pública
def _texto_de(payload: dict) -> str:
    # Compatible con colecciones creadas por mem0 / otros agentes.
    for k in ("texto", "data", "memory", "text", "content", "page_content"):
        if payload.get(k):
            return str(payload[k])
    return ""


def guardar(texto: str, agente: str | None = None, tipo: str = "hecho",
            etiquetas: list[str] | None = None, fuente: str = "") -> str:
    """Guarda un recuerdo. Mismo texto + mismo agente = no se duplica."""
    texto = (texto or "").strip()
    if not texto:
        raise MemoriaError("Texto vacío.")
    agente = (agente or _cfg("MEMORIA_AGENTE", "desconocido")).lower()
    asegurar_coleccion()
    pid = str(uuid.uuid5(NAMESPACE, f"{agente}|{texto}"))
    ahora = datetime.now(timezone.utc).isoformat()
    payload = {
        "texto": texto, "data": texto,            # 'data' = compatibilidad mem0
        "agente": agente, "agent_id": agente,
        "tipo": tipo, "etiquetas": etiquetas or [], "fuente": fuente,
        "creado": ahora, "created_at": ahora, "ts": time.time(),
        "hash": hashlib.md5(texto.encode()).hexdigest(),
    }
    _qdrant("PUT", f"/collections/{COLECCION}/points?wait=true",
            json={"points": [{"id": pid, "vector": embedding(texto), "payload": payload}]})
    return pid


def buscar(consulta: str, limite: int = 5, agente: str | None = None,
           umbral: float = 0.35) -> list[dict]:
    """Búsqueda semántica en la memoria de TODOS los agentes (o de uno)."""
    asegurar_coleccion()
    cuerpo = {"vector": embedding(consulta), "limit": limite, "with_payload": True,
              "score_threshold": umbral}
    if agente:
        cuerpo["filter"] = {"should": [
            {"key": "agente", "match": {"value": agente.lower()}},
            {"key": "agent_id", "match": {"value": agente.lower()}}]}
    res = _qdrant("POST", f"/collections/{COLECCION}/points/search", json=cuerpo) or []
    return [{"texto": _texto_de(p["payload"]),
             "agente": p["payload"].get("agente") or p["payload"].get("agent_id") or "?",
             "tipo": p["payload"].get("tipo", ""),
             "creado": p["payload"].get("creado") or p["payload"].get("created_at", ""),
             "score": round(p["score"], 3), "id": p["id"]} for p in res]


def recientes(limite: int = 10, agente: str | None = None) -> list[dict]:
    cuerpo: dict = {"limit": 200, "with_payload": True, "with_vector": False}
    if agente:
        cuerpo["filter"] = {"must": [{"key": "agente", "match": {"value": agente.lower()}}]}
    res = _qdrant("POST", f"/collections/{COLECCION}/points/scroll", json=cuerpo) or {}
    puntos = sorted(res.get("points", []), key=lambda p: p["payload"].get("ts", 0), reverse=True)
    return [{"texto": _texto_de(p["payload"]), "agente": p["payload"].get("agente", "?"),
             "creado": p["payload"].get("creado", "")} for p in puntos[:limite]]


def borrar(punto_id: str) -> None:
    _qdrant("POST", f"/collections/{COLECCION}/points/delete?wait=true",
            json={"points": [punto_id]})


def contar(agente: str | None = None) -> int:
    if info_coleccion() is None:
        return 0
    cuerpo: dict = {"exact": True}
    if agente:
        cuerpo["filter"] = {"should": [
            {"key": "agente", "match": {"value": agente}},
            {"key": "agent_id", "match": {"value": agente}}]}
    return (_qdrant("POST", f"/collections/{COLECCION}/points/count", json=cuerpo) or {}).get("count", 0)


def formatear_contexto(resultados: list[dict]) -> str:
    if not resultados:
        return ""
    lineas = [f"- ({r['agente']}) {r['texto']}" for r in resultados]
    return "Memoria compartida relevante:\n" + "\n".join(lineas)


if __name__ == "__main__":  # prueba rápida: python memoria_unificada.py "consulta"
    import sys
    q = " ".join(sys.argv[1:]) or "MBA Saltillo"
    print(formatear_contexto(buscar(q)) or "Sin resultados.")
