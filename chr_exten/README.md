# Atryon Chrome Extension

Manifest V3 extension: **virtual try-on** using the Atryon backend. The UI runs as a **side panel** so it stays open while you browse.

**Typical flow:** validate instructions (optional) → upload → MIC → poll → download.

## Stack

- **Manifest V3**
- **Vanilla HTML, CSS, and JavaScript**
- **Chrome APIs:** `content_scripts`, `runtime`, `tabs`, `storage`, `sidePanel`

## User flow

1. Click the extension icon → **side panel** opens and stays open when you interact with the page.

2. **Clothing**
   - **Drag and drop** an image onto the clothing placeholder (default shirt), or
   - Click **"Drag and drop above"** to pick an image from the current page (overlay appears; click a product image).
   - Use **×** on the placeholder to clear and pick another.

3. **Your photo**
   - Click **"Upload your photo"** and select an image (sent to the backend at try-on time).
   - Use **×** on the selfie placeholder to clear and choose a different photo.

4. **Extra try-on instructions (optional)**
   - Scoped to clothing try-on only: pose, lighting, fit (not general image generation).
   - Leave empty for default try-on behavior; the extension sends an empty string (not a placeholder space).
   - Max **400** characters (`maxlength` on the textarea).
   - Disallowed text shows **"Those instructions aren't allowed."** or **"Request could not be completed…"** in the status area.

5. Click **Try on**
   - Instructions are validated via `POST /bf_fl/validate_prompt` (fast fail, no upload yet).
   - Then: upload images → MIC → poll until ready → show result.

6. **Result**
   - Generated image shown in the panel; **Download image** saves locally (e.g. `atryon-result.png`).

**Wake backend:** click the **Atryon** logo or title in the header to send `GET /` to the backend (helps cold starts on hosted deployments). No UI feedback.

Close the panel with Chrome’s side panel close control.

## Content safety (extension)

- The extension does **not** ship the keyword blocklist; all enforcement is on the **backend**.
- Client-side checks (trim, max length, optional `validate_prompt` call) are **UX only** — bypassing the extension still hits server policy on MIC.
- Do not duplicate `banned_keywords` in extension JavaScript.

Full policy, config, and operator notes: **[backend/README.md#content-safety](../backend/README.md#content-safety)**.

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
| `manifest.json` | MV3, permissions, side panel (`popup.html`), content script, background |
| `popup.html` | Side panel layout: garment/selfie, optional instructions, try-on, result |
| `popup.css` | Styles including prompt hint and header wake button |
| `popup.js` | Try-on flow, validate/upload/MIC/poll/download, policy error mapping |
| `content.js` | “Select from page” overlay; sends image URL to the panel |
| `background.js` | Service worker; opens side panel from extension icon |
| `assets/` | Logo and default placeholders (tshirt, guy) |

For backend setup, API paths, and content policy, see **[../backend/README.md](../backend/README.md)**.
