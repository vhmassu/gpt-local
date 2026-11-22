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
def guardar_cliente(nombre: str, empresa: str = "", telefono: str = "", correo: str = "",
                    equipo: str = "", precio: str = "", notas: str = "") -> str:
    """Guarda o actualiza la ficha de un cliente de MBA Saltillo / Más Bienes Raíces
    (qué rentó o compró, a qué precio, contacto). Úsala cada vez que se cierre o cotice algo."""
    try:
        pid = mem.guardar_cliente(nombre, empresa, telefono, correo, equipo, precio,
                                  notas=notas, agente=AGENTE)
    except mem.MemoriaError as e:
        return f"Error de memoria: {e}"
    return f"Cliente guardado ({AGENTE}) id={pid}"


@app.tool()
def buscar_cliente(consulta: str, limite: int = 5) -> str:
    """Busca fichas de clientes por nombre, empresa o equipo (historial de rentas y precios)."""
    try:
        res = mem.buscar_cliente(consulta, limite)
    except mem.MemoriaError as e:
        return f"Error de memoria: {e}"
    return "\n".join(f"({r['creado'][:10]}) {r['texto']}" for r in res) or "Sin clientes que coincidan."


@app.tool()
def generar_cotizacion(datos_json: str) -> str:
    """Genera una cotización PDF de MBA Saltillo en MXN con IVA desglosado y registra al cliente.
    datos_json ejemplo:
    {"cliente": {"nombre": "Juan Pérez", "empresa": "Grupo X", "telefono": ""},
     "partidas": [{"clave": "GS-1930", "cantidad": 1, "periodo": "semana", "duracion": 2,
                   "precio_unitario": 4500}],
     "flete": 1500, "notas": "Entrega en Ramos Arizpe", "vigencia_dias": 15}
    periodo: día | semana | mes | pieza | servicio. precio_unitario es por periodo, sin IVA;
    si se omite se usa ~/Cotizaciones/precios.json. Nunca inventes precios: si falta, pregunta."""
    import json
    import cotizar
    try:
        return cotizar.texto_resumen(cotizar.generar(json.loads(datos_json)))
    except json.JSONDecodeError as e:
        return f"datos_json no es JSON válido: {e}"
    except cotizar.CotizacionError as e:
        return f"No se pudo cotizar: {e}"
    except ImportError:
        return "Falta la librería fpdf2: corre ~/.memoria-unificada/venv/bin/pip install fpdf2"


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
