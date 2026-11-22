# Memoria unificada (Qdrant) para los agentes locales

Una sola memoria para **Gemi (Telegram), OpenClaw, Hermes y Antigravity**.
Todo local, gratis y de código abierto: Qdrant guarda los recuerdos, Ollama (`nomic-embed-text`) genera los vectores.

```
 Gemi ──(import Python)──┐
 OpenClaw ──(MCP stdio)──┤
 Hermes ────(MCP stdio)──┼──► servidor_mcp.py / memoria_unificada.py ──► Qdrant :6333  (colección memoria_unificada)
 Antigravity (MCP stdio)─┘                         └──► Ollama :11434 (nomic-embed-text)
```

Cada recuerdo lleva `agente` = quién lo guardó, así cualquiera busca en lo que saben los demás.
El mismo texto del mismo agente no se duplica.

## Instalación (la corres tú)

```bash
cd ~/gpt-local && git pull
bash memoria/instalar.sh --simular   # opcional: ver qué cambiaría
bash memoria/instalar.sh
```

El script:
1. Copia los archivos a `~/.memoria-unificada/` y crea `config.env`.
2. Crea un venv propio con `mcp` y `requests`.
3. Usa Qdrant si ya corre en `:6333`; si no, lo levanta en Docker (`qdrant/qdrant:v1.15.4`, datos en `~/.qdrant_storage`).
4. Descarga `nomic-embed-text` en Ollama si falta.
5. Registra el servidor MCP `memoria` en OpenClaw, Hermes y Antigravity (con respaldo `.bak-memoria`) y añade las reglas de uso (`REGLAS_MEMORIA.md`) a sus instrucciones.
6. Importa la memoria que cada agente ya tenía y muestra la tabla de estado.

> Si ya tienes una colección en Qdrant creada con otro modelo de embeddings, el script lo detecta y avisa.
> Cambia `MEMORIA_COLECCION` o `EMBED_MODEL` en `~/.memoria-unificada/config.env`.

## Qué toca en cada agente

| Agente | Archivo | Qué se agrega |
|---|---|---|
| OpenClaw | `~/.openclaw/openclaw.json` | `mcp.servers.memoria` · reglas en `~/.openclaw/workspace/AGENTS.md` |
| Hermes | `~/.hermes/config.yaml` | `mcp_servers.memoria` · reglas en `~/.hermes/SOUL.md` |
| Antigravity | `~/.gemini/config/mcp_config.json` (o `~/.gemini/antigravity/…`) | `mcpServers.memoria` · reglas en `~/.gemini/GEMINI.md` |
| Gemi | su código Python | 2 líneas (abajo) |

Después:
- **OpenClaw:** `openclaw gateway restart` y `openclaw mcp list`. Su memoria propia (`MEMORY.md`, `memory/*.md`) se importa a Qdrant. Para que deje de usarla del todo, pon `plugins.slots.memory` en `"none"` en `openclaw.json` (opcional).
- **Hermes:** en un chat escribe `/reload-mcp`.
- **Antigravity:** reinícialo o refresca *MCP Servers*.

## Gemi (Telegram)

Gemi no usa MCP; importa el conector directamente. En el archivo del bot (donde recibe el mensaje y llama al modelo):

```python
import sys; sys.path.insert(0, "/home/TU_USUARIO/.memoria-unificada")
from gemi_memoria import con_memoria, recordar_turno

texto_para_modelo = con_memoria(texto_usuario)   # antes de llamar al modelo
# ... respuesta = modelo(texto_para_modelo) ...
recordar_turno(texto_usuario, respuesta)         # después de responder
```

Si Qdrant u Ollama no responden, Gemi sigue funcionando sin memoria. Corre Gemi con el venv
`~/.memoria-unificada/venv/bin/python` o instala `requests` en su propio entorno.

## Bot de Telegram (GPT Local)

`parche_telegram.py` conecta `telegram_puente.py` a la memoria (lo corre el instalador, con respaldo):
- **Lee:** antes de mandar tu mensaje a GPT Local, le antepone los recuerdos relevantes.
- **Guarda:** si tu mensaje trae datos duraderos ("recuerda…", precios, clientes), lo guarda como agente `telegram`.

## Cotizaciones MBA Saltillo

`cotizar.py` genera PDF en `~/Cotizaciones/` (MXN, IVA 16 % desglosado, folio automático) y registra al cliente.
- Llena tus tarifas (sin IVA) en `~/Cotizaciones/precios.json` y tus datos en `~/Cotizaciones/empresa.json`.
- Si falta una tarifa, **no inventa**: la pide.
- Los agentes con MCP usan la herramienta `generar_cotizacion`; por línea de comandos:
  `~/.memoria-unificada/venv/bin/python ~/.memoria-unificada/cotizar.py datos.json`

## Limpieza

`limpiar.py` lista dictados confusos y duplicados (no toca fichas de clientes). Solo borra con `--aplicar`
y guarda copia de lo borrado. El filtro de relevancia se ajusta con `MEMORIA_UMBRAL` en `config.env`.

## Acceso directo de Hermes

`acceso_hermes.sh` crea "Hermes Agent" con ícono propio y lo ancla al dock de COSMIC (respaldo de favoritos).

## Telegram exclusivo para Hermes (opcional)

1. En Telegram, habla con @BotFather → `/newbot` → guarda el token (**bot nuevo**, no el de GPT Local).
2. `hermes setup gateway` → marca **Telegram** → pega el token y tu ID de chat.
3. `hermes gateway install` para que arranque solo. Ollama libera el modelo tras 5 min sin uso.

## Herramientas MCP disponibles

| Herramienta | Uso |
|---|---|
| `buscar_memoria(consulta, limite, solo_agente)` | Búsqueda semántica en la memoria de todos |
| `guardar_memoria(texto, tipo, etiquetas)` | Guarda un dato duradero |
| `memorias_recientes(limite, solo_agente)` | Lo último guardado |
| `guardar_cliente(nombre, empresa, telefono, correo, equipo, precio, notas)` | Ficha de cliente |
| `buscar_cliente(consulta)` | Historial de un cliente |
| `generar_cotizacion(datos_json)` | PDF de cotización MXN con IVA |
| `borrar_memoria(id)` | Elimina un recuerdo incorrecto |

## Comandos útiles

```bash
P=~/.memoria-unificada/venv/bin/python; cd ~/.memoria-unificada
$P verificar.py                       # tabla de estado por agente
$P memoria_unificada.py "Plaza Alameda"   # buscar desde terminal
$P importar.py --todos                # reimportar memorias propias (incluye Codex)
$P limpiar.py                         # ver basura/duplicados (agrega --aplicar para borrar)
$P conectar_agentes.py --solo hermes  # reconectar un solo agente
```

## Fuentes

- OpenClaw, MCP en `mcp.servers`: <https://docs.openclaw.ai/tools/mcp.md> · <https://docs.openclaw.ai/gateway/config-extensions>
- Hermes, `mcp_servers` en `~/.hermes/config.yaml`: <https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp>
- Antigravity, `mcp_config.json`: <https://antigravity.google/docs/mcp>
- Qdrant API: <https://api.qdrant.tech/api-reference>
- Ollama embeddings: <https://github.com/ollama/ollama/blob/main/docs/api.md#generate-embeddings>
