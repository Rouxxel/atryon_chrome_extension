# Atryon Backend

Backend for the Atryon Chrome extension. FastAPI API with rate limiting, logging, and **Black Forest Labs (BFL)** integration for FLUX image generation: text-to-image (TTI), multi-image composition (MIC), and image edit with mask (IDWM / FLUX.1 Fill).

## Features

- **FastAPI** with Uvicorn
- **Black Forest API**: FLUX.2 (TTI, MIC) and FLUX.1 Fill (inpainting) via configurable endpoints
- **Rate limiting** (SlowAPI), **logging** (file + console), **JSON config** (`config_file.json` + `general_data.json`)
- **Docker**: multi-stage Dockerfile, docker-compose, non-root user, health check
- **Start scripts**: `start.bat` (Windows) and `start.sh` (Linux/macOS) for venv, deps, and run modes

## API documentations
- https://docs.bfl.ai/flux_2/flux2_image_editing
- https://docs.bfl.ai/flux_2/flux2_text_to_image
- https://docs.bfl.ai/flux_tools/flux_1_fill

## Project structure

```
backend/
├── src/
│   ├── api_endpoints/
│   │   ├── root_endpoint.py           # Health check /
│   │   └── routers/
│   │       ├── upload_files/          # Reusable file upload (MIC, IDWM, etc.)
│   │       │   └── upload_images.py   # POST /upload/images
│   │       └── black_forest_api/      # BFL FLUX endpoints (prefix /bf_fl)
│   │           ├── submit_mic.py      # POST /bf_fl/mic
│   │           ├── submit_tti.py      # POST /bf_fl/tti
│   │           ├── submit_idwm.py     # POST /bf_fl/idwm
│   │           ├── polling_requests.py
│   │           └── download_requests.py
│   ├── core_specs/
│   │   ├── configuration/             # config_file.json, config_loader
│   │   └── data/                      # general_data.json, data_loader
│   └── utils/
├── logs/                              # Created at runtime
├── main.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example                       # Copy to .env and .env.local
├── start.bat                          # Windows quick start
├── start.sh                           # Linux/macOS quick start
└── README.md
```

## Quick start

### 1. Environment

From the `backend/` directory:

```bash
cp .env.example .env
cp .env.example .env.local
```

Edit `.env` and `.env.local`: set **`BFL_API_KEY`** (and optionally `BFL_BASE_URL`) for Black Forest endpoints. Other keys (e.g. encryption, DB) are used if you enable those features.

### 2. Run with start scripts

**Windows (PowerShell or CMD):**

```cmd
start.bat
```

**Linux/macOS:**

```bash
chmod +x start.sh
./start.sh
```

The script will create `venv` if needed, install dependencies, create `.env`/`.env.local` from `.env.example` if missing, then prompt:

1. **Development** – Uvicorn with `--reload`
2. **Production** – `python main.py`
3. **Docker** – `docker-compose up --build`

### 3. Run with Docker only

```bash
cd backend
cp .env.example .env
# Edit .env and set BFL_API_KEY (required for BFL endpoints)
docker-compose up --build
```

- API: **http://localhost:8000**
- Docs: **http://localhost:8000/docs**
- ReDoc: **http://localhost:8000/redoc**

Port can be overridden with `SERVER_PORT` in `.env` (e.g. `SERVER_PORT=8080`).

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/upload/images` | Upload one or more images; returns `upload_ids` for use as `upload:<id>` in MIC/IDWM |
| POST | `/bf_fl/mic` | Multi-image composition (FLUX.2); body: `prompt`, `images[]` |
| POST | `/bf_fl/tti` | Text-to-image (FLUX.2); body: `prompt`, optional `width`, `height` |
| POST | `/bf_fl/idwm` | Image edit with mask (FLUX.1 Fill); body: `prompt`, `image`, optional `mask` |
| GET | `/bf_fl/polling_requests?polling_url=...` | Poll BFL task; response includes `result.sample` (image URL) |
| GET | `/bf_fl/download_requests?url=...` | Download image from signed URL |

Flow: **submit** → **poll** until `status == "Ready"` → use **`result['sample']`** or **download** endpoint to get the image. Path prefixes are configured in `config_file.json`.

## Configuration

- **`src/core_specs/configuration/config_file.json`** – Backend config: endpoints, rate limits, logging, network.
- **`src/core_specs/data/general_data.json`** – Data and provider config: `file_upload` (limits, TTL), BFL `flux2` and `flux1_fill` (models, defaults, prompt prefixes).

Environment (`.env` / `.env.local`):

- **`BFL_API_KEY`** – Required for all BFL endpoints.
- **`BFL_BASE_URL`** – Optional; default `https://api.bfl.ai/v1`.

## Docker

- **Dockerfile**: Multi-stage, Python 3.12-slim, non-root user, health check on `GET /`.
- **docker-compose**: Builds and runs the API; uses `.env`; mounts `./logs` for persistence.
- Create **`.env`** from **`.env.example`** and set **`BFL_API_KEY`** before `docker-compose up`.

Optional services (Redis, Postgres) are commented in `docker-compose.yml`; uncomment and set env vars if needed.

## Requirements

- Python 3.12+
- Docker & Docker Compose (optional)

## License

For use with the Atryon Chrome extension project.
