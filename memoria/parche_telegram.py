"""Conecta el puente de Telegram (telegram_puente.py de GPT Local) a la memoria unificada.

- LEER: antes de mandar tu mensaje a GPT Local, antepone los recuerdos relevantes.
- GUARDAR: si tu mensaje trae datos duraderos (precio, cliente, "recuerda…"), lo guarda
  en segundo plano como agente "telegram".

Respaldo automático, idempotente. Si la memoria falla, el bot sigue igual.
    python parche_telegram.py [--ruta /ruta/a/telegram_puente.py]
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

HOME = Path.home()
TAREA = " tid=local('task',{'prompt':text,'session_id':session()})['id']\n"
TAREA_P = " tid=local('task',{'prompt':prompt,'session_id':session()})['id']\n"

LEER = (" prompt=text\n"
        " try:\n"
        "  h=pathlib.Path.home()/'.memoria-unificada'\n"
        "  ctx=subprocess.run([str(h/'venv/bin/python'),str(h/'memoria_unificada.py'),text],capture_output=True,text=True,timeout=15).stdout.strip()\n"
        "  if ctx.startswith('Memoria compartida'):prompt=ctx+'\\n\\n(Usa la memoria solo si es relevante.)\\n\\nMensaje de Víctor: '+text\n"
        " except Exception:pass\n")

GUARDAR = (" try:  # memoria-unificada:guardar\n"
           "  h=pathlib.Path.home()/'.memoria-unificada'\n"
           "  subprocess.Popen([str(h/'venv/bin/python'),str(h/'gemi_memoria.py'),'--recordar-turno',text,'--agente','telegram'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)\n"
           " except Exception:pass\n")


def encontrar() -> Path | None:
    if "--ruta" in sys.argv:
        return Path(sys.argv[sys.argv.index("--ruta") + 1]).expanduser()
    hallados = sorted((HOME / ".codex/.chatgpt-projects").glob("*/scripts/telegram_puente.py"))
    return hallados[0] if hallados else None


def main() -> int:
    f = encontrar()
    if not f or not f.exists():
        print("   – no encontré telegram_puente.py; omitido")
        return 0
    s = f.read_text(encoding="utf-8")
    nuevo = s
    if ".memoria-unificada" not in nuevo:          # lectura
        if nuevo.count(TAREA) != 1:
            print(f"   ✗ {f}: no encontré la línea esperada; no cambié nada")
            return 1
        nuevo = nuevo.replace(TAREA, LEER + TAREA_P)
    if "memoria-unificada:guardar" not in nuevo:    # guardado
        if nuevo.count(TAREA_P) != 1:
            print(f"   ✗ {f}: no encontré dónde agregar el guardado; dejé solo la lectura")
        else:
            nuevo = nuevo.replace(TAREA_P, GUARDAR + TAREA_P)
    if nuevo == s:
        print("   ✓ puente de Telegram ya conectado (lee y guarda)")
        return 0
    shutil.copy2(f, f.with_name(f.name + ".bak-memoria-" + time.strftime("%Y%m%d%H%M%S")))
    f.write_text(nuevo, encoding="utf-8")
    print(f"   ✓ puente de Telegram conectado (lee y guarda) · respaldo junto a {f.name}")
    return 2  # 2 = hay que reiniciar el servicio


if __name__ == "__main__":
    sys.exit(main())
