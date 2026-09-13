# Atryon Backend

Backend for the Atryon Chrome extension. FastAPI API with rate limiting, logging, **content policy**, and **Black Forest Labs (BFL)** integration for FLUX image generation: text-to-image (TTI), multi-image composition (MIC), and image edit with mask (IDWM / FLUX.1 Fill).

## Features

- **FastAPI** with Uvicorn
- **Content policy** on user prompts (keyword blocklist, sanitization) before BFL calls
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
│   │       ├── upload_files/
│   │       │   └── upload_images.py   # POST /upload/images
│   │       └── black_forest_api/      # BFL FLUX endpoints (prefix /bf_fl)
│   │           ├── submit_mic.py
│   │           ├── submit_tti.py
│   │           ├── submit_idwm.py
│   │           ├── validate_prompt.py # POST /bf_fl/validate_prompt (optional pre-check)
│   │           ├── polling_requests.py
│   │           └── download_requests.py
│   ├── core_specs/
│   │   ├── configuration/             # config_file.json
│   │   └── data/                      # general_data.json
│   └── utils/
│       ├── validators.py              # Prompt + upload validation
│       ├── bfl_helpers.py             # BFL response handling, safety_tolerance
│       └── content_metrics.py         # Lightweight policy/BFL counters
├── notes/
│   └── image_safety_scope.md          # Operator notes (v1 scope, future options)
├── logs/
├── main.py
└── README.md
```

## Quick start

### 1. Environment

From the `backend/` directory:

```bash
cp .env.example .env
cp .env.example .env.local
```

Edit `.env` and `.env.local`: set **`BFL_API_KEY`** (and optionally `BFL_BASE_URL`) for Black Forest endpoints.

### 2. Run with start scripts

**Windows:** `start.bat`  
**Linux/macOS:** `chmod +x start.sh && ./start.sh`

Choose development (Uvicorn `--reload`), production (`python main.py`), or Docker.

### 3. Run with Docker only

```bash
cd backend
cp .env.example .env
# Set BFL_API_KEY in .env
docker-compose up --build
```

- API: **http://localhost:8000**
- Docs: **http://localhost:8000/docs**

Port can be overridden with `SERVER_PORT` in `.env`.

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check (also used by the extension to wake a cold backend) |
| POST | `/upload/images` | Upload images; returns `upload_ids` for `upload:<id>` in MIC/IDWM |
| POST | `/bf_fl/validate_prompt` | Validate try-on instructions only (no BFL call) |
| POST | `/bf_fl/mic` | Multi-image composition (FLUX.2); body: `prompt`, `images[]` |
| POST | `/bf_fl/tti` | Text-to-image (FLUX.2); body: `prompt`, optional `width`, `height` |
| POST | `/bf_fl/idwm` | Image edit with mask (FLUX.1 Fill); body: `prompt`, `image`, optional `mask` |
| GET | `/bf_fl/polling_requests?polling_url=...` | Poll BFL task until `status == "Ready"` |
| GET | `/bf_fl/download_requests?url=...` | Download image from signed BFL URL |

**Try-on flow:** validate (optional) → upload → MIC submit → poll → download.

Path prefixes are configured in `config_file.json`.

## Content safety

<a id="content-safety"></a>

### Prompt validation pipeline

All BFL submit endpoints (MIC, TTI, IDWM) run user text through this pipeline **before** any Black Forest request:

1. **Sanitize** — strip control characters, normalize whitespace
2. **Keyword policy** — match against blocklists in config (with normalization / basic evasion hardening)
3. **Length** — enforce `max_prompt_length`
4. **Prefix merge** — prepend model-specific try-on / generation prefix from config
5. **BFL submit** — send payload including `safety_tolerance`

**MIC / try-on:** whitespace-only extra instructions are allowed (empty optional field). TTI and IDWM require non-empty prompts.

### Configuration (`general_data.json`)

Under `image_ai_providers.black_forest`:

| Key | Purpose |
|-----|---------|
| `content_policy_enabled` | `true` / `false` — toggle keyword checks |
| `banned_keywords` | Primary blocklist (maintain terms here only; never echo in docs or logs) |
| `banned_keywords_hate` | Optional split list (merged with primary) |
| `banned_keywords_explicit` | Optional split list (merged with primary) |
| `max_prompt_length` | Max characters for user prompt after sanitization (default 400) |

Under `file_upload`:

| Key | Purpose |
|-----|---------|
| `allowed_upload_content_types` | JPEG, PNG, WebP |
| `min_upload_bytes` / `max_upload_bytes` | Per-file size limits |
| `min_image_dimension` / `max_image_dimension` | Per-side pixel bounds (default 64–4096) |
| `max_files_per_upload` | Max files per upload request |

Under `flux2` / `flux1_fill`:

| Key | Purpose |
|-----|---------|
| `safety_tolerance` | BFL moderation strictness (default `2`) |
| `safety_tolerance_min` / `safety_tolerance_max` | Clamp range (default 0–6, per [BFL docs](https://docs.bfl.ai/)) |

To disable keyword filtering in development, set `content_policy_enabled` to `false`. Update blocklists only in `general_data.json`; do not commit example slurs in documentation or comments.

### Client responses and logging

| Situation | HTTP | Client `detail` |
|-----------|------|-----------------|
| Keyword policy match | 400 | `Prompt not allowed.` |
| Empty prompt (TTI/IDWM) | 400 | `Prompt must not be empty.` |
| Prompt too long | 400 | `Prompt exceeds the maximum allowed length.` |
| BFL submit/poll moderation failure | 502 / 400 | `Request could not be completed.` |

Policy blocks are logged with `reason=content_policy_keyword`, endpoint name, and a **SHA-256 hash** of the normalized prompt — not the raw text. BFL failures log `polling_url` and task id when available; provider response bodies stay server-side.

### Black Forest `safety_tolerance`

All submit payloads include `safety_tolerance` from config:

- **MIC / TTI:** `flux2.safety_tolerance`
- **IDWM:** `flux1_fill.safety_tolerance`

This is the last line of defense when a request reaches BFL. Poll failures (`Error`, `Content Moderated`, etc.) return a generic client error after logging.

### Image uploads (v1)

Uploads are validated (MIME, magic bytes, size, dimensions) but **not** scanned for hate symbols, nudity, or other image content. Abuse via images may still reach BFL; rate limits and provider safety partially mitigate this. See `notes/image_safety_scope.md` for operator scope notes and future options.

### Metrics

In-process counters are logged on each event (`content_policy_keyword`, `bfl_submit_success`, `bfl_submit_reject`, `bfl_poll_reject`, etc.) for lightweight monitoring via log aggregation.

## Rate limits (try-on bundle)

Per-minute limits in `config_file.json` for a typical extension flow:

| Endpoint | Default limit |
|----------|----------------|
| `POST /upload/images` | 10 |
| `POST /bf_fl/validate_prompt` | 10 |
| `POST /bf_fl/mic` | 6 |
| `GET /bf_fl/polling_requests` | 30 |
| `GET /bf_fl/download_requests` | 30 |

## Configuration files

- **`src/core_specs/configuration/config_file.json`** — Endpoints, rate limits, logging, network.
- **`src/core_specs/data/general_data.json`** — Upload limits, content policy, BFL models, prompt prefixes, safety settings.

Environment (`.env` / `.env.local`):

- **`BFL_API_KEY`** — Required for all BFL endpoints.
- **`BFL_BASE_URL`** — Optional; default `https://api.bfl.ai/v1`.

## Docker

- **Dockerfile**: Multi-stage, Python 3.12-slim, non-root user, health check on `GET /`.
- **docker-compose**: Uses `.env`; mounts `./logs` for persistence.

## Requirements

- Python 3.12+
- Docker & Docker Compose (optional)

## License

For use with the Atryon Chrome extension project.
