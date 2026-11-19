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

## Herramientas MCP disponibles

| Herramienta | Uso |
|---|---|
| `buscar_memoria(consulta, limite, solo_agente)` | Búsqueda semántica en la memoria de todos |
| `guardar_memoria(texto, tipo, etiquetas)` | Guarda un dato duradero |
| `memorias_recientes(limite, solo_agente)` | Lo último guardado |
| `borrar_memoria(id)` | Elimina un recuerdo incorrecto |

## Comandos útiles

```bash
P=~/.memoria-unificada/venv/bin/python; cd ~/.memoria-unificada
$P verificar.py                       # tabla de estado por agente
$P memoria_unificada.py "Plaza Alameda"   # buscar desde terminal
$P importar.py --todos                # reimportar memorias propias de los agentes
$P conectar_agentes.py --solo hermes  # reconectar un solo agente
```

## Fuentes

- OpenClaw, MCP en `mcp.servers`: <https://docs.openclaw.ai/tools/mcp.md> · <https://docs.openclaw.ai/gateway/config-extensions>
- Hermes, `mcp_servers` en `~/.hermes/config.yaml`: <https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp>
- Antigravity, `mcp_config.json`: <https://antigravity.google/docs/mcp>
- Qdrant API: <https://api.qdrant.tech/api-reference>
- Ollama embeddings: <https://github.com/ollama/ollama/blob/main/docs/api.md#generate-embeddings>
