#!/usr/bin/env bash
# Instala la memoria unificada (Qdrant + Ollama) y conecta Gemi, OpenClaw, Hermes y Antigravity.
# Uso:  bash memoria/instalar.sh            (desde la carpeta del repo gpt-local)
#       bash memoria/instalar.sh --simular  (solo muestra qué cambiaría en los agentes)
set -euo pipefail

ORIGEN="$(cd "$(dirname "$0")" && pwd)"
BASE="$HOME/.memoria-unificada"
EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"
SIMULAR="${1:-}"

echo "== 1/8 Archivos en $BASE"
mkdir -p "$BASE"
cp "$ORIGEN"/{memoria_unificada.py,servidor_mcp.py,gemi_memoria.py,importar.py,verificar.py,conectar_agentes.py,limpiar.py,cotizar.py,parche_telegram.py,acceso_hermes.sh,REGLAS_MEMORIA.md} "$BASE"/
[ -f "$BASE/config.env" ] || cat > "$BASE/config.env" <<EOF
QDRANT_URL=http://localhost:6333
MEMORIA_COLECCION=memoria_unificada
MEMORIA_UMBRAL=0.5
OLLAMA_URL=http://localhost:11434
EMBED_MODEL=$EMBED_MODEL
EOF

grep -q '^MEMORIA_UMBRAL' "$BASE/config.env" || echo "MEMORIA_UMBRAL=0.5" >> "$BASE/config.env"

echo "== 2/8 Entorno Python (venv propio, no toca el sistema)"
[ -d "$BASE/venv" ] || python3 -m venv "$BASE/venv"
"$BASE/venv/bin/pip" install -q --upgrade pip
"$BASE/venv/bin/pip" install -q "mcp>=1.10,<2" requests fpdf2

echo "== 3/8 Qdrant"
if curl -sf -m 3 http://localhost:6333/collections >/dev/null; then
  echo "   ✓ Qdrant ya está corriendo"
elif command -v docker >/dev/null; then
  echo "   Iniciando Qdrant en Docker (datos en ~/.qdrant_storage)…"
  mkdir -p "$HOME/.qdrant_storage"
  docker run -d --name qdrant --restart unless-stopped -p 127.0.0.1:6333:6333 \
    -v "$HOME/.qdrant_storage:/qdrant/storage" qdrant/qdrant:v1.15.4 >/dev/null
  for _ in $(seq 1 20); do curl -sf -m 2 http://localhost:6333/collections >/dev/null && break; sleep 1; done
else
  echo "   ✗ Qdrant no responde y no hay Docker. Instala Docker (sudo apt install docker.io) y vuelve a correr."
  exit 1
fi

echo "== 4/8 Modelo de embeddings en Ollama ($EMBED_MODEL)"
if ! curl -sf -m 3 http://localhost:11434/api/tags >/dev/null; then
  echo "   ✗ Ollama no responde en :11434. Inícialo (systemctl start ollama) y vuelve a correr."; exit 1
fi
ollama list | grep -q "^$EMBED_MODEL" || ollama pull "$EMBED_MODEL"

echo "== 5/8 Conectando agentes"
cd "$BASE"
if [ "$SIMULAR" = "--simular" ]; then
  "$BASE/venv/bin/python" conectar_agentes.py --simular
  exit 0
fi
"$BASE/venv/bin/python" conectar_agentes.py
"$BASE/venv/bin/python" -c "import memoria_unificada as m; m.asegurar_coleccion(); print('   ✓ colección', m.COLECCION, 'lista')"
"$BASE/venv/bin/python" importar.py --todos || echo "   (importación parcial; revisa arriba)"

echo "== 6/8 Bot de Telegram, cotizaciones y acceso directo de Hermes"
set +e
"$BASE/venv/bin/python" parche_telegram.py; rc=$?
set -e
if [ "$rc" = "2" ]; then
  systemctl --user restart gpt-local-telegram.service 2>/dev/null \
    || sudo systemctl restart gpt-local-telegram.service \
    || echo "   – reinicia el bot a mano: sudo systemctl restart gpt-local-telegram.service"
  echo "   ✓ bot de Telegram reiniciado"
fi
"$BASE/venv/bin/python" -c "import cotizar; cotizar.preparar_carpeta(); print('   ✓ plantilla de cotizaciones en', cotizar.DIR)"
bash "$BASE/acceso_hermes.sh"

echo "== 7/8 Revisión de limpieza (no borra nada)"
"$BASE/venv/bin/python" limpiar.py | tail -n 25

echo "== 8/8 Estado final"
"$BASE/venv/bin/python" verificar.py
