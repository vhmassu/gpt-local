"""Copia las memorias que cada agente ya tenía por su cuenta a la memoria unificada.

    python importar.py --todos            # todo lo que encuentre
    python importar.py --openclaw         # ~/.openclaw/workspace/MEMORY.md y memory/*.md
    python importar.py --hermes           # ~/.hermes/memories/*.md
    python importar.py --codex            # ~/.codex/memories*/ (Markdown) y memorias JSON/JSONL
    python importar.py --gemi RUTA.json   # historial de Gemi (lista de {role, content})
    python importar.py --archivo X.md --agente nombre

No duplica: el mismo texto del mismo agente se sobrescribe.
Descarta textos sin datos útiles (dictados confusos, frases muy cortas).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import memoria_unificada as mem

HOME = Path.home()


def trozos_markdown(texto: str, maximo: int = 800, agrupar: bool = True) -> list[str]:
    """Divide por viñetas/párrafos, agrupando hasta ~800 caracteres (o uno por viñeta)."""
    bloques = [b.strip() for b in re.split(r"\n\s*\n|\n(?=[-*•] )|\n(?=#+ )", texto) if b.strip()]
    salida, actual = [], ""
    for b in bloques:
        b = re.sub(r"^[-*•]\s+", "", b)
        if len(b) < 15 or b.startswith("<!-- memoria-unificada"):
            continue
        if not agrupar:
            if not b.startswith("#"):
                salida.append(b[:maximo].strip())
            continue
        if len(actual) + len(b) > maximo and actual:
            salida.append(actual.strip())
            actual = ""
        actual += b + "\n"
    if actual.strip():
        salida.append(actual.strip())
    return salida


def _guardar(texto: str, agente: str, fuente: str) -> bool:
    try:
        mem.guardar(texto, agente=agente, tipo="importado", fuente=fuente)
        return True
    except mem.MemoriaError as e:
        if "sin datos útiles" in str(e) or "vacío" in str(e):
            return False
        raise


def importar_archivo(p: Path, agente: str, maximo: int = 800, agrupar: bool = True) -> int:
    n = descartados = 0
    for t in trozos_markdown(p.read_text(encoding="utf-8", errors="ignore"), maximo, agrupar):
        if _guardar(t, agente, str(p)):
            n += 1
        else:
            descartados += 1
    print(f"  {p}: {n} recuerdos" + (f" ({descartados} descartados)" if descartados else ""))
    return n


def _textos_json(dato) -> list[str]:
    if isinstance(dato, str):
        return [dato]
    if isinstance(dato, dict):
        for k in ("memory", "text", "texto", "content", "summary", "value", "data"):
            if isinstance(dato.get(k), str):
                return [dato[k]]
        return [t for v in dato.values() for t in _textos_json(v)] if any(
            isinstance(v, (list, dict)) for v in dato.values()) else []
    if isinstance(dato, list):
        return [t for v in dato for t in _textos_json(v)]
    return []


def codex(raiz: Path | None = None) -> int:
    """Memorias de Codex: Markdown (una viñeta = un recuerdo) y JSON/JSONL si los hay."""
    home = raiz or (HOME / ".codex")
    carpetas = [home / "memories_v2", home / "memories", home / "memory"]
    archivos = [f for c in carpetas if c.exists() for f in sorted(c.rglob("*"))
                if f.is_file() and f.suffix.lower() in (".md", ".json", ".jsonl")]
    if not archivos:
        print(f"  No encontré memorias de Codex en {home}/memories*/. "
              f"Búscalas con:  find {home} -iname '*memor*'  y usa --archivo")
        return 0
    total = 0
    for f in archivos:
        if f.suffix.lower() == ".md":
            total += importar_archivo(f, "codex", maximo=600, agrupar=False)
            continue
        textos: list[str] = []
        try:
            if f.suffix.lower() == ".jsonl":
                for linea in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if linea.strip():
                        textos += _textos_json(json.loads(linea))
            else:
                textos = _textos_json(json.loads(f.read_text(encoding="utf-8", errors="ignore")))
        except json.JSONDecodeError:
            print(f"  {f}: no es JSON válido, omitido")
            continue
        n = sum(_guardar(t.strip()[:800], "codex", str(f)) for t in textos if t and t.strip())
        print(f"  {f}: {n} recuerdos")
        total += n
    return total


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
            n += _guardar(f"Victor dijo: {c[:800]}", "gemi", str(ruta))
    print(f"  {ruta}: {n} recuerdos")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--openclaw", action="store_true")
    ap.add_argument("--hermes", action="store_true")
    ap.add_argument("--codex", action="store_true")
    ap.add_argument("--gemi", type=Path)
    ap.add_argument("--archivo", type=Path)
    ap.add_argument("--agente")
    a = ap.parse_args()
    total = 0
    if a.todos or a.openclaw:
        total += openclaw()
    if a.todos or a.hermes:
        total += hermes()
    if a.todos or a.codex:
        total += codex()
    if a.gemi:
        total += gemi(a.gemi)
    elif a.todos:
        for c in (HOME / "gemma-agent/historial_conversacion.json", HOME / "gemi/historial_conversacion.json"):
            if c.exists():
                total += gemi(c)
    if a.archivo:
        total += importar_archivo(a.archivo, (a.agente or "manual").lower())
    print(f"Total importado: {total}")
