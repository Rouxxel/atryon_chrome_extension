# Atryon Chrome Extension

Chrome extension for **virtual try-on**: pick a garment (from the page or by drag-and-drop), add your photo, and get an AI-generated try-on result. The extension uses a **backend API** that runs FLUX (Black Forest Labs) for multi-image composition.

[VIDEO DEMO](https://youtu.be/chbujM2-rrA)


## Repository structure

| Path | Description |
|------|-------------|
| **`chr_exten/`** | Chrome extension (Manifest V3): side panel UI, content script for “select from page,” try-on flow, result and download. See [chr_exten/README.md](chr_exten/README.md). |
| **`backend/`** | FastAPI backend: image upload, BFL FLUX endpoints (MIC, TTI, IDWM), polling, download proxy, rate limiting, Docker. See [backend/README.md](backend/README.md). |

## Quick start

### 1. Backend (required for try-on)

From the repo root:

```bash
cd backend
cp .env.example .env
cp .env.example .env.local
```

Edit `.env` and `.env.local` and set **`BFL_API_KEY`**. Then run:

- **Windows:** `start.bat`
- **Linux/macOS:** `chmod +x start.sh && ./start.sh`
- Or with Docker: `docker-compose up --build`

API runs at **http://localhost:8000** (port configurable in `.env`).

### 2. Chrome extension

1. Open **chrome://extensions/** and enable **Developer mode**.
2. Click **Load unpacked** and select the **`chr_exten`** folder.
3. Click the extension icon to open the **side panel**.
4. Add a garment (drag-and-drop or “Drop above” to pick from the page), upload your photo, then click **Try on**. Use **Download image** to save the result.

By default the extension uses the hosted backend; to use your local backend, set `atryonBackendUrl` in extension storage (see [chr_exten/README.md](chr_exten/README.md#backend-url)).

## Docs

- **Extension:** [chr_exten/README.md](chr_exten/README.md) — flow, backend URL, loading in Chrome, file layout.
- **Backend:** [backend/README.md](backend/README.md) — setup, API paths, config, Docker.

## License

See [LICENSE](LICENSE) if present.
