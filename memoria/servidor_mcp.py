"""Servidor MCP de la memoria unificada.

OpenClaw, Hermes y Antigravity lo lanzan por stdio. Cada uno pasa su nombre en
la variable MEMORIA_AGENTE para que sus recuerdos queden etiquetados.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memoria_unificada as mem  # noqa: E402

try:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Servidor
except ImportError:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Servidor

AGENTE = os.environ.get("MEMORIA_AGENTE", "desconocido").lower()
app = _Servidor("memoria")


@app.tool()
def buscar_memoria(consulta: str, limite: int = 5, solo_agente: str = "") -> str:
    """Busca en la memoria compartida de todos los agentes (Gemi, OpenClaw, Hermes,
    Antigravity). Úsala ANTES de responder sobre Victor, sus negocios, clientes,
    preferencias, proyectos o decisiones previas. `solo_agente` filtra por un agente."""
    try:
        res = mem.buscar(consulta, limite=limite, agente=solo_agente or None)
    except mem.MemoriaError as e:
        return f"Error de memoria: {e}"
    if not res:
        return "No hay recuerdos relevantes."
    return "\n".join(f"[{r['score']}] ({r['agente']}, {r['creado'][:10]}) {r['texto']}" for r in res)


@app.tool()
def guardar_memoria(texto: str, tipo: str = "hecho", etiquetas: list[str] | None = None) -> str:
    """Guarda un recuerdo duradero en la memoria compartida. Úsala cuando aprendas
    algo útil a futuro: preferencias, datos de clientes, precios, decisiones,
    tareas pendientes. Escribe una frase autocontenida (quién, qué, cuándo).
    tipo: hecho | preferencia | cliente | tarea | decision | nota"""
    try:
        pid = mem.guardar(texto, agente=AGENTE, tipo=tipo, etiquetas=etiquetas, fuente="mcp")
    except mem.MemoriaError as e:
        return f"Error de memoria: {e}"
    return f"Guardado ({AGENTE}) id={pid}"


@app.tool()
def memorias_recientes(limite: int = 10, solo_agente: str = "") -> str:
    """Lista los recuerdos más recientes de la memoria compartida."""
    try:
        res = mem.recientes(limite, agente=solo_agente or None)
    except mem.MemoriaError as e:
        return f"Error de memoria: {e}"
    return "\n".join(f"({r['agente']}, {r['creado'][:10]}) {r['texto']}" for r in res) or "Vacía."


@app.tool()
def borrar_memoria(id: str) -> str:
    """Borra un recuerdo por su id (solo si Victor lo pide o el dato es incorrecto)."""
    try:
        mem.borrar(id)
    except mem.MemoriaError as e:
        return f"Error de memoria: {e}"
    return "Borrado."


if __name__ == "__main__":
    app.run()
