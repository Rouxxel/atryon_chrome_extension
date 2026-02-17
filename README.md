# Atryon Chrome Extension

A Chrome extension for trying on pieces of clothing. The project includes a **backend API** that powers image-generation features via Black Forest Labs (FLUX): text-to-image, multi-image composition, and image edit with mask.

## Repository structure

| Path | Description |
|------|-------------|
| **`backend/`** | FastAPI backend: BFL FLUX endpoints, rate limiting, logging, Docker. See [backend/README.md](backend/README.md) for setup and API details. |

## Quick start

1. **Backend** (required for image generation):
   ```bash
   cd backend
   cp .env.example .env
   cp .env.example .env.local
   ```
   Edit `.env` and `.env.local` and set **`BFL_API_KEY`**. Then either:
   - Run **`start.bat`** (Windows) or **`start.sh`** (Linux/macOS), or  
   - Run **`docker-compose up --build`**.

2. **Chrome extension**: Load the extension from this repo in Chrome (developer mode) once the extension source is in place.

Full backend setup, API reference, and Docker usage: **[backend/README.md](backend/README.md)**.

## License

See [LICENSE](LICENSE).
