"""Conector de memoria unificada para Gemi (agente Python con Telegram).

Gemi no usa MCP, así que importa esto directamente. Uso en el bot:

    from gemi_memoria import con_memoria, recordar_turno

    prompt = con_memoria(texto_usuario)          # antes de llamar al modelo
    respuesta = modelo(prompt)
    recordar_turno(texto_usuario, respuesta)     # después de responder

Si Qdrant u Ollama no están disponibles, Gemi sigue funcionando sin memoria.

Desde otro programa (p. ej. el puente de Telegram, que usa otro Python):
    venv/bin/python gemi_memoria.py --recordar-turno "texto del usuario" --agente telegram
"""
from __future__ import annotations

import logging
import os
import re
import sys
import threading
from pathlib import Path

os.environ.setdefault("MEMORIA_AGENTE", "gemi")
sys.path.insert(0, str(Path(os.environ.get("MEMORIA_DIR", Path(__file__).resolve().parent))))
import memoria_unificada as mem  # noqa: E402

log = logging.getLogger("gemi_memoria")

# Frases que indican que vale la pena guardar algo (mismas que el filtro de calidad).
_DISPARADORES = mem._PALABRAS_UTILES


def con_memoria(texto_usuario: str, limite: int = 5) -> str:
    """Devuelve el mensaje del usuario con el contexto de memoria antepuesto."""
    try:
        ctx = mem.formatear_contexto(mem.buscar(texto_usuario, limite=limite))
    except Exception as e:  # nunca romper a Gemi por la memoria
        log.warning("Memoria no disponible: %s", e)
        return texto_usuario
    if not ctx:
        return texto_usuario
    return f"{ctx}\n\n(Usa la memoria solo si es relevante.)\n\nMensaje de Victor: {texto_usuario}"


def recordar(texto: str, tipo: str = "hecho", agente: str = "gemi", fuente: str = "gemi") -> bool:
    try:
        mem.guardar(texto, agente=agente, tipo=tipo, fuente=fuente)
        return True
    except Exception as e:
        log.warning("No se guardó en memoria: %s", e)
        return False


def nota_de_turno(texto_usuario: str, canal: str = "Telegram") -> str | None:
    """Devuelve la nota a guardar, o None si el mensaje no trae datos duraderos."""
    t = (texto_usuario or "").strip()
    if len(t) < 12 or t.startswith("/") or not _DISPARADORES.search(t):
        return None
    nota = f"Victor dijo ({canal}): {t[:800]}"
    return None if mem.es_basura(nota) else nota


def recordar_turno(texto_usuario: str, respuesta: str = "", agente: str = "gemi",
                   canal: str = "Telegram", en_segundo_plano: bool = True) -> None:
    """Guarda lo que Victor dijo si parece un dato duradero."""
    nota = nota_de_turno(texto_usuario, canal)
    if not nota:
        return
    if en_segundo_plano:
        threading.Thread(target=recordar, args=(nota, "hecho", agente, canal.lower()),
                         daemon=True).start()
    else:
        recordar(nota, "hecho", agente, canal.lower())


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--recordar-turno"] and len(a) >= 2:
        agente = a[a.index("--agente") + 1] if "--agente" in a else "gemi"
        recordar_turno(a[1], agente=agente, en_segundo_plano=False)
    else:
        print(con_memoria(" ".join(a) or "¿Qué sabes de mis negocios?"))
