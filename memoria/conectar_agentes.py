"""Registra el servidor MCP 'memoria' en OpenClaw, Hermes y Antigravity
y añade las reglas de uso de memoria a sus instrucciones.

- Hace respaldo (.bak-memoria) de cada archivo antes de tocarlo.
- Es idempotente: correrlo dos veces no duplica nada.
- Uso: python conectar_agentes.py [--solo openclaw|hermes|antigravity] [--simular]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

HOME = Path.home()
BASE = HOME / ".memoria-unificada"
PY = BASE / "venv" / "bin" / "python"
SERVIDOR = BASE / "servidor_mcp.py"
REGLAS = (Path(__file__).resolve().parent / "REGLAS_MEMORIA.md")
MARCA_INI = "<!-- memoria-unificada:inicio -->"
MARCA_FIN = "<!-- memoria-unificada:fin -->"

SIMULAR = False


def entrada(agente: str) -> dict:
    return {"command": str(PY), "args": [str(SERVIDOR)], "env": {"MEMORIA_AGENTE": agente}}


def respaldo(p: Path) -> None:
    if p.exists():
        b = p.with_name(p.name + ".bak-memoria")
        if not b.exists():
            shutil.copy2(p, b)


def escribir(p: Path, texto: str) -> None:
    if p.exists() and p.read_text(encoding="utf-8") == texto:
        return  # sin cambios: no reescribir ni respaldar
    if SIMULAR:
        print(f"   [simulación] escribiría {p}")
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    respaldo(p)
    p.write_text(texto, encoding="utf-8")


def agregar_reglas(p: Path, nombre: str) -> None:
    reglas = REGLAS.read_text(encoding="utf-8").replace("{AGENTE}", nombre)
    bloque = f"\n{MARCA_INI}\n{reglas.strip()}\n{MARCA_FIN}\n"
    actual = p.read_text(encoding="utf-8") if p.exists() else ""
    if MARCA_INI in actual:
        actual = re.sub(re.escape(MARCA_INI) + r".*?" + re.escape(MARCA_FIN) + r"\n?", "",
                        actual, flags=re.S).rstrip() + "\n"
    escribir(p, actual.rstrip() + "\n" + bloque)
    print(f"   ✓ reglas de memoria en {p}")


# ------------------------------------------------------------------ Antigravity
def antigravity() -> bool:
    print("• Antigravity")
    candidatos = [HOME / ".gemini/config/mcp_config.json", HOME / ".gemini/antigravity/mcp_config.json"]
    destinos = [c for c in candidatos if c.parent.exists()] or [candidatos[0]]
    for p in destinos:
        try:
            datos = json.loads(p.read_text(encoding="utf-8")) if p.exists() and p.read_text().strip() else {}
        except json.JSONDecodeError as e:
            print(f"   ✗ {p} no es JSON válido ({e}); no lo toqué.")
            return False
        datos.setdefault("mcpServers", {})["memoria"] = entrada("antigravity")
        escribir(p, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
        print(f"   ✓ servidor 'memoria' en {p}")
    agregar_reglas(HOME / ".gemini/GEMINI.md", "antigravity")
    print("   → Reinicia Antigravity (o en Agent ▸ MCP Servers ▸ Refresh).")
    return True


# ------------------------------------------------------------------ Hermes
def hermes() -> bool:
    print("• Hermes")
    raiz = HOME / ".hermes"
    if not raiz.exists():
        print("   – No encontré ~/.hermes (¿Hermes no instalado?). Omitido.")
        return False
    p = raiz / "config.yaml"
    texto = p.read_text(encoding="utf-8") if p.exists() else ""
    e = entrada("hermes")
    bloque = (
        "  memoria:\n"
        f"    command: \"{e['command']}\"\n"
        f"    args: [\"{e['args'][0]}\"]\n"
        "    env:\n"
        "      MEMORIA_AGENTE: \"hermes\"\n"
    )
    if re.search(r"^  memoria:\s*$", texto, re.M):
        print("   ✓ ya estaba registrado en config.yaml")
    elif re.search(r"^mcp_servers:\s*\{\}\s*$", texto, re.M):
        texto = re.sub(r"^mcp_servers:\s*\{\}\s*$", "mcp_servers:\n" + bloque.rstrip(), texto, flags=re.M)
        escribir(p, texto)
        print(f"   ✓ servidor 'memoria' en {p}")
    elif re.search(r"^mcp_servers:\s*$", texto, re.M):
        texto = re.sub(r"^mcp_servers:\s*$", "mcp_servers:\n" + bloque.rstrip(), texto, count=1, flags=re.M)
        escribir(p, texto)
        print(f"   ✓ servidor 'memoria' en {p}")
    else:
        escribir(p, texto.rstrip() + "\n\nmcp_servers:\n" + bloque)
        print(f"   ✓ servidor 'memoria' en {p}")
    agregar_reglas(raiz / "SOUL.md", "hermes")
    print("   → En un chat de Hermes escribe /reload-mcp (o reinícialo).")
    return True


# ------------------------------------------------------------------ OpenClaw
def openclaw() -> bool:
    print("• OpenClaw")
    raiz = HOME / ".openclaw"
    if not raiz.exists():
        print("   – No encontré ~/.openclaw (¿OpenClaw no instalado?). Omitido.")
        return False
    p = raiz / "openclaw.json"
    try:
        datos = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except json.JSONDecodeError:
        print(f"   ✗ {p} tiene comentarios (JSON5); no lo edito automáticamente.")
        print("     Agrega dentro de \"mcp\": { \"servers\": { ... } } esta entrada:")
        print('     "memoria": ' + json.dumps(entrada("openclaw"), ensure_ascii=False))
        datos = None
    if datos is not None:
        datos.setdefault("mcp", {}).setdefault("servers", {})["memoria"] = entrada("openclaw")
        escribir(p, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
        print(f"   ✓ servidor 'memoria' en {p} (mcp.servers.memoria)")
    ws = raiz / "workspace"
    agregar_reglas((ws if ws.exists() else raiz) / "AGENTS.md", "openclaw")
    print("   → Reinicia el gateway:  openclaw gateway restart   y verifica:  openclaw mcp list")
    print("   → Su memoria propia (MEMORY.md) se copia a Qdrant con:  importar.py --openclaw")
    return True


# ------------------------------------------------------------------ Codex / GPT Local
def codex() -> bool:
    print("• Codex / GPT Local")
    raiz = HOME / ".codex"
    if not raiz.exists():
        print("   – No encontré ~/.codex. Omitido.")
        return False
    agregar_reglas(raiz / "AGENTS.md", "gpt-local")
    print("   → GPT Local recibe la memoria por el puente de Telegram (parche_telegram.py).")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", choices=["openclaw", "hermes", "antigravity", "codex"])
    ap.add_argument("--simular", action="store_true", help="muestra qué haría sin escribir")
    a = ap.parse_args()
    SIMULAR = a.simular
    for nombre, fn in (("openclaw", openclaw), ("hermes", hermes), ("antigravity", antigravity),
                       ("codex", codex)):
        if not a.solo or a.solo == nombre:
            fn()
    print("\nGemi (Telegram) no usa MCP: ver README, sección Gemi (2 líneas en su código).")
