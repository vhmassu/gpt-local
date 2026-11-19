"""Copia las memorias que cada agente ya tenía por su cuenta a la memoria unificada.

    python importar.py --todos            # todo lo que encuentre
    python importar.py --openclaw         # ~/.openclaw/workspace/MEMORY.md y memory/*.md
    python importar.py --hermes           # ~/.hermes/memories/*.md
    python importar.py --gemi RUTA.json   # historial de Gemi (lista de {role, content})
    python importar.py --archivo X.md --agente nombre

No duplica: el mismo texto del mismo agente se sobrescribe.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import memoria_unificada as mem

HOME = Path.home()


def trozos_markdown(texto: str, maximo: int = 800) -> list[str]:
    """Divide por viñetas/párrafos, agrupando hasta ~800 caracteres."""
    bloques = [b.strip() for b in re.split(r"\n\s*\n|\n(?=[-*•] )|\n(?=#+ )", texto) if b.strip()]
    salida, actual = [], ""
    for b in bloques:
        b = re.sub(r"^[-*•]\s+", "", b)
        if len(b) < 15 or b.startswith("<!-- memoria-unificada"):
            continue
        if len(actual) + len(b) > maximo and actual:
            salida.append(actual.strip())
            actual = ""
        actual += b + "\n"
    if actual.strip():
        salida.append(actual.strip())
    return salida


def importar_archivo(p: Path, agente: str) -> int:
    n = 0
    for t in trozos_markdown(p.read_text(encoding="utf-8", errors="ignore")):
        mem.guardar(t, agente=agente, tipo="importado", fuente=str(p))
        n += 1
    print(f"  {p}: {n} recuerdos")
    return n


def openclaw() -> int:
    ws = HOME / ".openclaw" / "workspace"
    archivos = [ws / "MEMORY.md", ws / "USER.md", *sorted((ws / "memory").glob("*.md"))]
    return sum(importar_archivo(a, "openclaw") for a in archivos if a.exists())


def hermes() -> int:
    d = HOME / ".hermes" / "memories"
    return sum(importar_archivo(a, "hermes") for a in sorted(d.glob("*.md"))) if d.exists() else 0


def gemi(ruta: Path) -> int:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    n = 0
    for m in datos:
        c = (m.get("content") or "").strip() if isinstance(m, dict) else ""
        if m.get("role") == "user" and len(c) >= 25 and not c.startswith("/"):
            mem.guardar(f"Victor dijo: {c[:800]}", agente="gemi", tipo="importado", fuente=str(ruta))
            n += 1
    print(f"  {ruta}: {n} recuerdos")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--openclaw", action="store_true")
    ap.add_argument("--hermes", action="store_true")
    ap.add_argument("--gemi", type=Path)
    ap.add_argument("--archivo", type=Path)
    ap.add_argument("--agente")
    a = ap.parse_args()
    total = 0
    if a.todos or a.openclaw:
        total += openclaw()
    if a.todos or a.hermes:
        total += hermes()
    if a.gemi:
        total += gemi(a.gemi)
    elif a.todos:
        for c in (HOME / "gemma-agent/historial_conversacion.json", HOME / "gemi/historial_conversacion.json"):
            if c.exists():
                total += gemi(c)
    if a.archivo:
        total += importar_archivo(a.archivo, (a.agente or "manual").lower())
    print(f"Total importado: {total}")
