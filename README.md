# UPV_EARTH_PROYECTOIII

---

## Arranque con Docker (recomendado · independiente del SO)

Toda la plataforma (backend FastAPI + frontend Next.js + Nginx) corre dentro de
contenedores, así que **no depende del sistema operativo** ni de tener Python o
Node instalados: solo necesitas Docker. Funciona igual en Windows, macOS y Linux.

### Único requisito: Docker

- **Windows / macOS**: instala [Docker Desktop](https://www.docker.com/products/docker-desktop/).
- **Linux**: instala Docker Engine + plugin Compose:
  ```bash
  sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER"   # luego cierra sesión y vuelve a entrar
  ```

### Lanzar la plataforma (un comando)

Desde la raíz del repositorio:

```bash
docker compose up -d --build
```

Cuando termine, abre **[http://localhost:8080](http://localhost:8080)**.

Eso construye y arranca tres contenedores:

| Servicio | Imagen | Rol |
|---|---|---|
| `backend`  | `python:3.11-slim` | API FastAPI + pipeline PDF→PB (SQLite, sin GPU) |
| `frontend` | `node:20-alpine`   | UI Next.js |
| `nginx`    | `nginx:1.27-alpine`| Proxy inverso, publica todo en el puerto `8080` |

La base de datos es **SQLite** (incluida en `mockup/data/seed/`) y los embeddings
están **precalculados** en el repo, por lo que el dashboard, el explorador de
papers y la búsqueda de similares funcionan nada más arrancar. No hace falta GPU.

### Comandos útiles

```bash
docker compose ps          # estado de los contenedores
docker compose logs -f     # logs en vivo de toda la pila
docker compose down        # detener y eliminar los contenedores
docker compose up -d --build   # reconstruir tras cambios de código
```

### Chatbot / LLM (opcional)

El chatbot RAG usa un modelo servido por **Ollama**. Es opcional y no arranca por
defecto (un modelo como `qwen2.5:14b` ocupa ~9 GB). El resto de la plataforma
funciona sin él (la UI muestra "Chatbot no disponible"). Para activarlo:

```bash
# 1) arranca también el contenedor de Ollama
docker compose --profile llm up -d

# 2) descarga el modelo una sola vez
docker compose exec ollama ollama pull qwen2.5:14b
```

Para usar otro modelo, exporta `OLLAMA_MODEL` antes de levantar la pila
(por ejemplo `OLLAMA_MODEL=llama3.1:8b docker compose --profile llm up -d`).

### Resolución de problemas (Docker)

| Síntoma | Causa habitual | Cómo resolver |
|---|---|---|
| `permission denied ... docker.sock` | El usuario no está en el grupo `docker` | `sudo usermod -aG docker "$USER"` y reinicia la sesión. |
| Puerto 8080 ocupado | Otro servicio usa el puerto | Cambia el mapeo en `docker-compose.yml` (`"8081:80"`). |
| El primer `up` tarda mucho | Se descargan imágenes base y dependencias | Es normal solo la primera vez; las siguientes usan caché. |
| Chatbot "no disponible" | Falta el perfil `llm` o el modelo | Arranca con `--profile llm` y `ollama pull`. |

> Si prefieres ejecutarlo **sin Docker** (instalación nativa con dos comandos
> `setup`/`launch`), consulta la sección siguiente.

---

## Arranque rápido en local sin Docker (2 comandos)

La plataforma web (FastAPI + Next.js + Ollama) se levanta en cualquier máquina
con dos comandos: **set-up** y **launch**. Los scripts detectan el SO, comprueban
las herramientas que faltan, las instalan, preparan el entorno Python/Node y dejan
todo listo para arrancar.

| Sistema operativo | Comando de set-up | Comando de launch |
|---|---|---|
| **Linux**   | `./setup.sh`   | `./launch.sh`   |
| **macOS**   | `./setup.sh`   | `./launch.sh`   |
| **Windows** | `.\setup.ps1`  | `.\launch.ps1`  |

Tras ejecutar `launch`, abre [http://localhost:3000](http://localhost:3000) en el navegador.

### Qué hace `set-up`

Es idempotente: si algo ya está instalado lo detecta y continúa. En orden:

1. **Detecta el SO** y el gestor de paquetes (`apt`/`dnf`/`pacman`/`zypper` en Linux,
   Homebrew en macOS, `winget` en Windows).
2. **Python 3.11**: comprueba la versión. Si falta, lo instala (en Ubuntu añade el
   PPA `deadsnakes` si hace falta).
3. **Node.js 20+**: comprueba la versión y lo instala desde NodeSource/Homebrew/winget.
4. **Ollama**: instala el runtime LLM y lo levanta como servicio en segundo plano.
5. **Entorno virtual de Python** (`.venv/`) y dependencias del backend
   (`mockup/backend/requirements.txt`).
6. **Dependencias del frontend** con `npm install` en `mockup/frontend/`.
7. **Variables de entorno**: copia `mockup/.env.example` a `mockup/.env` si no existe.
8. **Modelo LLM**: descarga `qwen2.5:14b` con `ollama pull` (~9 GB, una sola vez).

> El modelo Ollama se puede cambiar exportando `OLLAMA_MODEL=otro-modelo` antes
> de ejecutar `setup`.

### Qué hace `launch`

1. **Preflight**: comprueba que `setup` se ejecutó (venv y `node_modules` presentes).
2. Arranca **Ollama** si no está corriendo (puerto `11434`).
3. Arranca el **backend FastAPI** con `uvicorn` (puerto `8000`), con la BD SQLite
   local en `mockup/data/seed/upvearth_local.db` y todas las variables de
   entorno necesarias.
4. Arranca el **frontend Next.js** en modo desarrollo (puerto `3000`).
5. Espera a que los tres servicios respondan a sus *health checks* y muestra las URLs.
6. Se queda en foreground vigilando los procesos: `Ctrl+C` los detiene todos limpiamente.

Comandos auxiliares:

```bash
./launch.sh stop      # detiene todo lo arrancado por el script
./launch.sh status    # estado de los tres servicios
./launch.sh restart   # reinicia toda la pila
```

Equivalente en Windows: `.\launch.ps1 stop|status|restart`.

### Requisitos previos por SO

Los scripts intentan instalar todo, pero estos elementos los gestiona el SO
y deben existir antes del primer `setup`:

- **Linux**: `curl` y `sudo` (suelen venir preinstalados). El usuario debe poder
  ejecutar `sudo` para instalar Python, Node y Ollama.
- **macOS**: nada especial; si falta Homebrew, el script lo instala.
- **Windows 10/11**: `winget` (App Installer, gratis en Microsoft Store). Antes
  de la primera ejecución habilita la ejecución de scripts:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```

### Estructura de runtime

Logs y PIDs viven en `.runtime/` (no se commitea):

```
.runtime/
├── logs/
│   ├── ollama.log
│   ├── backend.log
│   └── frontend.log
└── pids/
    ├── ollama.pid
    ├── backend.pid
    └── frontend.pid
```

### Resolución de problemas

| Síntoma | Causa habitual | Cómo resolver |
|---|---|---|
| `setup` falla pidiendo `python3.11` | Versión no disponible en repos | Linux Ubuntu: el script añade el PPA `deadsnakes` automáticamente. Otros: instala Python 3.11 a mano y relanza. |
| `setup` se cuelga al descargar `qwen2.5:14b` | Modelo grande (~9 GB) | Espera o cancela y vuelve a lanzar; `ollama pull` reanuda. |
| `launch.sh` dice "venv ausente" | Falta ejecutar `setup` | Ejecuta `./setup.sh` antes. |
| Puerto 3000/8000 ocupado | Otro proceso usando el puerto | `./launch.sh stop` o cambia los puertos: `BACKEND_PORT=8080 FRONTEND_PORT=3001 ./launch.sh`. |
| Backend arranca pero el chatbot dice "no disponible" | Ollama no respondió o no tiene el modelo | `ollama list` para verificar; `ollama pull qwen2.5:14b` para descargar. |

### Despliegue con Docker (alternativa)

Si prefieres contenedores en lugar de instalación local, `mockup/docker-compose.yml`
levanta la pila completa (Postgres + Ollama + backend + frontend + Nginx).
Detalles en [mockup/README.md](mockup/README.md).

---

## Documentación

- Guía SSH + VS Code: [docs/guia-ssh-vscode.md](docs/guia-ssh-vscode.md)
- Entorno Python y Jupyter: [docs/entorno-python.md](docs/entorno-python.md)
- Flujo completo de extracción del corpus mixto: [docs/flujo_extraccion_1000.md](docs/flujo_extraccion_1000.md)
- Organización del repositorio (mapa de carpetas): [docs/ORGANIZACION_REPO.md](docs/ORGANIZACION_REPO.md)

## Estructura del proyecto

Distribución actual resumida:

- `data/corpus/`: CSV maestros del pipeline (`clean`, `clean_enriched`, `traceability` y evaluaciones).
- `prompts/`: activos de prompts y contexto de prompt.
- `docs/eda/`: salidas EDA (tablas, figuras y resumen) y `docs/eda/auditoria/` para control de calidad de la muestra final real.
- `muestras/`: listados y muestras seleccionadas (aleatoria y balanceada).
- `scripts/auxiliary/`: scripts auxiliares no críticos para el pipeline principal.
- raíz del proyecto: scripts nucleares de extracción y EDA para mantener compatibilidad de ejecución.

Detalle completo y actualizado en: [docs/ORGANIZACION_REPO.md](docs/ORGANIZACION_REPO.md).

## Flujo de PDFs

El flujo actual ya no es el de 30 PDFs ni el de scripts separados. El procesamiento principal está unificado en [extraccion_corpus_mixto.py](extraccion_corpus_mixto.py) y la explicación completa está en [docs/flujo_extraccion_1000.md](docs/flujo_extraccion_1000.md).

La lista de PDFs sigue generándose con `rclone lsf`, que produce el inventario plano usado por el pipeline:

```bash
mkdir -p /root/proyectoiii/muestras && \
rclone lsf upv_drive: --recursive --files-only --include "*.pdf" > /root/proyectoiii/muestras/listado_pdfs.txt && \
wc -l /root/proyectoiii/muestras/listado_pdfs.txt
```

Ese comando hace tres cosas:

- Crea la carpeta local `muestras/` si no existe.
- Lista de forma recursiva todos los archivos PDF del remoto `upv_drive:` y guarda la salida en `muestras/listado_pdfs.txt`.
- Cuenta las líneas del listado para saber cuántos PDFs se han encontrado.

En otras palabras, `listado_pdfs.txt` es el inventario plano de todos los PDFs accesibles en el remoto, y sirve como base para que el pipeline seleccione la muestra aleatoria de 1000 documentos antes de descargarla con `rclone`.

Ese flujo de 30 documentos fue útil para la fase exploratoria, pero ya quedó sustituido por el pipeline de 1000 documentos con limpieza, deduplicación y trazabilidad.

## Corpus PB

El avance adicional del corpus de Planetary Boundaries está en [corpus_PB/README.md](corpus_PB/README.md).

Ruta recomendada:

1. [corpus_PB/README.md](corpus_PB/README.md)
2. [corpus_PB/docs/corpus_pb_methodology.pdf](corpus_PB/docs/corpus_pb_methodology.pdf)
3. [corpus_PB/docs/pb_reference_readable_es.pdf](corpus_PB/docs/pb_reference_readable_es.pdf)
4. [corpus_PB/docs/pb_reference_readable_en.pdf](corpus_PB/docs/pb_reference_readable_en.pdf)
5. [corpus_PB/data/pb_reference.csv](corpus_PB/data/pb_reference.csv)

## Flujo actual del corpus

El flujo principal del proyecto para extracción de PDFs es el pipeline unificado de 1000 documentos con 3 bloques de descarga, limpieza, deduplicación y trazabilidad. La explicación detallada está en [docs/flujo_extraccion_1000.md](docs/flujo_extraccion_1000.md).

## CSV para BERT embeddings

Para la siguiente fase (BERT/embeddings), usar estos archivos:

1. **Entrada principal recomendada**: [data/corpus/master_corpus_mixto_1000_clean_enriched.csv](data/corpus/master_corpus_mixto_1000_clean_enriched.csv)
2. **Alternativa mínima**: [data/corpus/master_corpus_mixto_1000_clean.csv](data/corpus/master_corpus_mixto_1000_clean.csv)

Referencia detallada de qué columna usar y cuáles no usar para embeddings:

- [docs/bert_embeddings_inputs.md](docs/bert_embeddings_inputs.md)
