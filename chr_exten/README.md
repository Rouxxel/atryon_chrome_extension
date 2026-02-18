# Atryon Chrome Extension

Manifest V3 extension: **Virtual try-on** using the Atryon backend (upload → MIC → poll → download).

## Stack

- **Manifest V3**
- **Vanilla HTML + CSS + JS**
- **Chrome APIs:** `content_scripts`, `runtime`, `tabs`, `storage`

## Flow

1. User clicks extension icon → popup opens.
2. **Clothing:** Click "Select clothing", then click an image on the page (e.g. product photo). That image URL is sent to the backend as the first input.
3. **Your photo:** Click "Upload your photo" and choose an image. It is uploaded to the backend and referenced as `upload:<id>`.
4. Optionally add extra instructions in the text box.
5. Click **Try on** → extension: uploads user image → calls MIC with `[garmentUrl, "upload:id"]` → polls until Ready → downloads result and shows it in the popup.

## Backend URL

Default: `https://atryon-chrome-extension.onrender.com`

To use a different backend (e.g. local):

1. Open DevTools on the popup (right‑click popup → Inspect).
2. In Console: `chrome.storage.local.set({ atryonBackendUrl: 'http://localhost:8000' })`
3. Reload the popup and try again.

## Load in Chrome

1. Open `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the `chr_exten` folder

## Files

- `manifest.json` – MV3, permissions, popup, content script, background
- `popup.html` / `popup.css` / `popup.js` – popup UI and try-on flow
- `content.js` – runs on all pages; handles "Select clothing" and sends image URL to popup
- `background.js` – service worker (minimal)
