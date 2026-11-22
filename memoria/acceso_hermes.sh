#!/usr/bin/env bash
# Crea el acceso directo "Hermes Agent" (ícono propio) y lo ancla al dock de COSMIC.
# Hace respaldo de la lista de favoritos del dock antes de tocarla. Idempotente.
set -euo pipefail

APPS="$HOME/.local/share/applications"
ICONOS="$HOME/.local/share/icons"
mkdir -p "$APPS" "$ICONOS"

cat > "$ICONOS/hermes-agent.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#7c5cff"/><stop offset="1" stop-color="#3b2a99"/></linearGradient></defs>
  <rect x="6" y="6" width="116" height="116" rx="26" fill="url(#g)"/>
  <text x="64" y="66" font-family="Georgia, serif" font-size="34" font-weight="bold"
        fill="#fff" text-anchor="middle">Hermes</text>
  <text x="64" y="94" font-family="sans-serif" font-size="17" fill="#e6e0ff"
        text-anchor="middle">Agente</text>
</svg>
SVG

cat > "$APPS/hermes-agent.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Hermes Agent
Comment=Agente Hermes local (Ollama, memoria unificada)
Exec=cosmic-term -e bash -lc "hermes; exec bash"
Icon=$ICONOS/hermes-agent.svg
Terminal=false
Categories=Utility;
StartupWMClass=hermes-agent
EOF
update-desktop-database "$APPS" 2>/dev/null || true
echo "   ✓ acceso directo creado (búscalo como 'Hermes Agent')"

# Anclar al dock de COSMIC (lista de favoritos en formato RON: ["app1", "app2"])
FAV="$HOME/.config/cosmic/com.system76.CosmicAppList/v1/favorites"
if [ -f "$FAV" ]; then
  if grep -q '"hermes-agent"' "$FAV"; then
    echo "   ✓ ya estaba anclado al dock"
  else
    [ -f "$FAV.bak-hermes" ] || cp "$FAV" "$FAV.bak-hermes"
    python3 - "$FAV" <<'PY'
import sys, re
p = sys.argv[1]; s = open(p, encoding="utf-8").read().rstrip()
if s.endswith("]"):
    cuerpo = s[:-1].rstrip()
    sep = "" if cuerpo.endswith(("[", ",")) else ","
    open(p, "w", encoding="utf-8").write(cuerpo + sep + '\n    "hermes-agent",\n]\n')
    print("   ✓ anclado al dock (respaldo: favorites.bak-hermes)")
else:
    print("   – no reconocí el formato del dock; ánclalo con clic derecho > Anclar")
PY
  fi
else
  echo "   – no encontré la configuración del dock; ábrelo y usa clic derecho > Anclar al dock"
fi
