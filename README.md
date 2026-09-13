# Atryon Chrome Extension

Chrome extension for **virtual try-on**: pick a garment (from the page or by drag-and-drop), add your photo, and get an AI-generated try-on result. The extension uses a **backend API** that runs FLUX (Black Forest Labs) for multi-image composition.

[VIDEO DEMO](https://youtu.be/chbujM2-rrA)


## Repository structure

| Path | Description |
|------|-------------|
| **`chr_exten/`** | Chrome extension (Manifest V3): side panel UI, content script for “select from page,” try-on flow, result and download. See [chr_exten/README.md](chr_exten/README.md). |
| **`backend/`** | FastAPI backend: image upload, content policy, BFL FLUX endpoints (MIC, TTI, IDWM), polling, download proxy, rate limiting, Docker. See [backend/README.md](backend/README.md). |

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
4. Add a garment (drag-and-drop or “Drag and drop above” to pick from the page), upload your photo, optionally add try-on instructions, then click **Try on**. Use **Download image** to save the result.

By default the extension uses the hosted backend; to use your local backend, set `atryonBackendUrl` in extension storage (see [chr_exten/README.md](chr_exten/README.md#backend-url)).

## Content safety

Atryon is a **virtual try-on** tool, not a general image generator.

- **Extra instructions** in the side panel are optional and scoped to clothing fit, pose, and lighting.
- The **backend** validates prompts (keyword policy, length, sanitization) **before** calling Black Forest Labs, so blocked text does not spend API tokens.
- The keyword filter applies to **text only**; uploaded images are not scanned for hate symbols or nudity in v1 (see [backend/README.md#content-safety](backend/README.md#content-safety)).
- Black Forest **`safety_tolerance`** remains a provider-side backstop when a request reaches their API.

Operators maintain blocklists in `backend/src/core_specs/data/general_data.json` (`banned_keywords` and optional split lists). Do not put example slurs in public documentation.

### Known gaps (v1)

The validation system is layered but **not comprehensive**. Be aware of these limits:

| Gap | What it means |
|-----|----------------|
| **Text-only keyword filter** | Only the optional instructions field (and TTI/IDWM prompts) are checked. Abuse in images is not caught by keywords. |
| **No image content scanning** | Garment and selfie uploads are validated for type, size, and dimensions — not for hate symbols, nudity, or other visual policy violations. |
| **Keyword evasion** | Obfuscation, misspellings, coded language, non-English text, or terms not on the blocklist may slip through until BFL rejects them (if at all). |
| **BFL may still be called** | If text passes the keyword filter, a Black Forest request is submitted; provider moderation runs afterward and may still fail (generic error to the client). Some API cost can occur before rejection. |
| **Extension checks are UX only** | The side panel can pre-validate instructions for faster feedback, but anyone calling the API directly must still hit the same backend rules on MIC/TTI/IDWM. |
| **Rate limits throttle, not judge** | Per-minute limits reduce abuse volume; they do not detect harmful content. |
| **No external moderation API** | There is no third-party text or vision classifier in v1 (e.g. OpenAI moderation, Perspective). |

For operator detail and future mitigation options, see [backend/notes/image_safety_scope.md](backend/notes/image_safety_scope.md) and [backend/README.md#content-safety](backend/README.md#content-safety).

## Docs

- **Extension:** [chr_exten/README.md](chr_exten/README.md) — flow, backend URL, content safety (client), loading in Chrome.
- **Backend:** [backend/README.md](backend/README.md) — setup, API paths, content policy, config, Docker.

## License

See [LICENSE](LICENSE) if present.
