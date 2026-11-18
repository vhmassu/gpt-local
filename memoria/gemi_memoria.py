"""Conector de memoria unificada para Gemi (agente Python con Telegram).

Gemi no usa MCP, así que importa esto directamente. Uso en el bot:

    from gemi_memoria import con_memoria, recordar_turno

    prompt = con_memoria(texto_usuario)          # antes de llamar al modelo
    respuesta = modelo(prompt)
    recordar_turno(texto_usuario, respuesta)     # después de responder

Si Qdrant u Ollama no están disponibles, Gemi sigue funcionando sin memoria.
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

# Frases que indican que vale la pena guardar algo.
_DISPARADORES = re.compile(
    r"\b(recuerda|acuérdate|no olvides|anota|guarda|mi (nombre|correo|tel[eé]fono)|"
    r"prefiero|siempre|nunca|cliente|cotiza|precio|cita|pendiente)\b", re.I)


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


def recordar(texto: str, tipo: str = "hecho") -> None:
    try:
        mem.guardar(texto, agente="gemi", tipo=tipo, fuente="telegram")
    except Exception as e:
        log.warning("No se guardó en memoria: %s", e)


def recordar_turno(texto_usuario: str, respuesta: str = "") -> None:
    """Guarda en segundo plano lo que Victor dijo si parece un dato duradero."""
    if len(texto_usuario) < 12 or not _DISPARADORES.search(texto_usuario):
        return
    nota = f"Victor dijo (Telegram): {texto_usuario.strip()}"
    threading.Thread(target=recordar, args=(nota,), daemon=True).start()


if __name__ == "__main__":
    print(con_memoria(" ".join(sys.argv[1:]) or "¿Qué sabes de mis negocios?"))
