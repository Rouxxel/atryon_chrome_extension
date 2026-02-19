# Atryon Chrome Extension

Manifest V3 extension: **virtual try-on** using the Atryon backend (upload → MIC → poll → download). The UI runs as a **side panel** so it stays open while you browse.

## Stack

- **Manifest V3**
- **Vanilla HTML, CSS, and JavaScript**
- **Chrome APIs:** `content_scripts`, `runtime`, `tabs`, `storage`, `sidePanel`

## User flow

1. Click the extension icon → **side panel** opens and stays open when you interact with the page.

2. **Clothing**
   - **Drag and drop** an image onto the clothing placeholder (default shirt), or
   - Click **"Drop above"** to pick an image from the current page (overlay appears; click a product image).
   - The chosen image is used as the garment. Use the **×** on the placeholder to clear and pick another.

3. **Your photo**
   - Click **"Upload your photo"** and select an image. It is uploaded to the backend and used as the person image.
   - Use the **×** on the selfie placeholder to clear and choose a different photo.

4. Optionally add **extra instructions** in the text area.

5. Click **Try on** → extension uploads images, calls the backend MIC endpoint with `[garment, "upload:<id>"]`, polls until ready, then shows the result in the panel.

6. **Result**
   - The generated image is shown with consistent margins and fit (no stretching).
   - Use **"Download image"** to save the result locally (e.g. `atryon-result.png`).

Close the panel with Chrome’s side panel close control.

## Backend URL

Default: `https://atryon-chrome-extension.onrender.com`

To use another backend (e.g. local):

1. Open DevTools on the side panel (right‑click the panel → Inspect).
2. In the console: `chrome.storage.local.set({ atryonBackendUrl: 'http://localhost:8000' })`
3. Reload the extension or panel and try again.

## Load in Chrome

1. Open `chrome://extensions/`
2. Turn on **Developer mode**
3. Click **Load unpacked**
4. Select the **`chr_exten`** folder

## Files

| File | Purpose |
|------|---------|
| `manifest.json` | MV3, permissions, side panel entry (`popup.html`), content script, background |
| `popup.html` / `popup.css` / `popup.js` | Side panel UI: garment/selfie placeholders, drop zone, try-on flow, result and download |
| `content.js` | Injected on all pages; handles “select from page” overlay and sends image URL to the panel |
| `background.js` | Service worker; ensures the extension icon opens the side panel |
| `assets/` | Logo and default placeholders (tshirt, guy) |

For full backend setup and API details, see **[../backend/README.md](../backend/README.md)**.
