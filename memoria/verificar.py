"""Revisa el estado de la memoria unificada y de cada agente. Imprime la tabla:

    Agente | Conectado | Recuerdos en Qdrant | Detalle
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import memoria_unificada as mem

HOME = Path.home()


def leer(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def estado_openclaw() -> tuple[bool, str]:
    p = HOME / ".openclaw/openclaw.json"
    if not p.exists():
        return False, "no encontré ~/.openclaw/openclaw.json"
    t = leer(p)
    ok = '"memoria"' in t and "servidor_mcp.py" in t
    plugin = ""
    if re.search(r'"memory-(core|lancedb)"', t):
        plugin = " · aún tiene su plugin de memoria propio activo"
    return ok, ("mcp.servers.memoria registrado" if ok else "falta mcp.servers.memoria") + plugin


def estado_hermes() -> tuple[bool, str]:
    p = HOME / ".hermes/config.yaml"
    if not p.exists():
        return False, "no encontré ~/.hermes/config.yaml"
    ok = bool(re.search(r"^  memoria:\s*$", leer(p), re.M)) and "servidor_mcp.py" in leer(p)
    return ok, "mcp_servers.memoria registrado" if ok else "falta mcp_servers.memoria"


def estado_antigravity() -> tuple[bool, str]:
    for p in (HOME / ".gemini/config/mcp_config.json", HOME / ".gemini/antigravity/mcp_config.json"):
        if p.exists():
            try:
                if "memoria" in json.loads(leer(p) or "{}").get("mcpServers", {}):
                    return True, f"registrado en {p.relative_to(HOME)}"
            except json.JSONDecodeError:
                return False, f"{p} no es JSON válido"
    return False, "falta 'memoria' en ~/.gemini/config/mcp_config.json"


def estado_gemi() -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["grep", "-rlE", "gemi_memoria|memoria_unificada", "--include=*.py",
             str(HOME / "gemma-agent"), str(HOME / "gemi"), str(HOME / "agentes")],
            capture_output=True, text=True, timeout=20)
        archivos = [a for a in r.stdout.split() if "memoria-unificada" not in a]
    except Exception:
        archivos = []
    if archivos:
        return True, "importa gemi_memoria en " + ", ".join(Path(a).name for a in archivos[:3])
    return False, "su código aún no importa gemi_memoria (ver README §Gemi)"


def main() -> None:
    print(f"Qdrant: {mem.QDRANT_URL} · colección: {mem.COLECCION} · embeddings: {mem.EMBED_MODEL}")
    try:
        cols = mem.colecciones()
        print(f"Colecciones existentes: {', '.join(cols) or '(ninguna)'}")
        qdrant_ok = True
    except mem.MemoriaError as e:
        print(f"✗ {e}")
        qdrant_ok = False
    try:
        dim = len(mem.embedding("prueba"))
        print(f"✓ Ollama responde ({dim} dimensiones)")
    except mem.MemoriaError as e:
        print(f"✗ {e}")
    if qdrant_ok and mem.info_coleccion() is not None:
        print(f"Total recuerdos: {mem.contar()}")

    filas = [("Gemi (Telegram)", "gemi", estado_gemi), ("OpenClaw", "openclaw", estado_openclaw),
             ("Hermes", "hermes", estado_hermes), ("Antigravity", "antigravity", estado_antigravity)]
    print("\n| Agente | Memoria unificada (Qdrant) | Recuerdos | Detalle |")
    print("|---|---|---|---|")
    for nombre, clave, fn in filas:
        ok, detalle = fn()
        n = mem.contar(clave) if qdrant_ok else "?"
        print(f"| {nombre} | {'✅ Conectado' if ok else '❌ Falta'} | {n} | {detalle} |")


if __name__ == "__main__":
    main()
