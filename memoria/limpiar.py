"""Limpia la memoria unificada: dictados de voz sin sentido y duplicados.

    python limpiar.py            # SOLO muestra qué borraría (no toca nada)
    python limpiar.py --aplicar  # borra lo listado (guarda copia en limpieza-AAAAMMDD.jsonl)

Nunca borra fichas de clientes (tipo 'cliente').
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import memoria_unificada as mem


def _normal(t: str) -> str:
    return " ".join(re.findall(r"\w+", t.lower()))


def candidatos() -> list[dict]:
    vistos: dict[str, str] = {}
    malos = []
    for p in mem.todos():
        if p["payload"].get("tipo") == "cliente":
            continue
        texto = p["texto"]
        clave = _normal(texto)
        if not texto or mem.es_basura(texto):
            malos.append({**p, "motivo": "sin datos útiles"})
        elif clave in vistos:
            malos.append({**p, "motivo": "duplicado"})
        else:
            vistos[clave] = p["id"]
    return malos


def main() -> None:
    aplicar = "--aplicar" in sys.argv
    malos = candidatos()
    total = mem.contar()
    print(f"Recuerdos totales: {total} · a borrar: {len(malos)}\n")
    for m in malos[:200]:
        print(f"  [{m['motivo']}] ({m['payload'].get('agente', '?')}) {m['texto'][:110]}")
    if len(malos) > 200:
        print(f"  … y {len(malos) - 200} más")
    if not malos:
        print("La memoria ya está limpia.")
        return
    if not aplicar:
        print("\nNo se borró nada. Si la lista está bien, corre:  limpiar.py --aplicar")
        return
    copia = Path(__file__).resolve().parent / f"limpieza-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    with copia.open("w", encoding="utf-8") as f:
        for m in malos:
            f.write(json.dumps({"id": m["id"], "payload": m["payload"]}, ensure_ascii=False) + "\n")
    for m in malos:
        mem.borrar(m["id"])
    print(f"\n✓ Borrados {len(malos)}. Copia de lo borrado en {copia}")


if __name__ == "__main__":
    main()
