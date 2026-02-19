/**
 * Atryon popup – Virtual try-on flow: upload → MIC → poll → download.
 * Vanilla JS, Chrome APIs: runtime, tabs, storage.
 */

(function () {
  const DEFAULT_BACKEND = 'https://atryon-chrome-extension.onrender.com';
  const POLL_INTERVAL_MS = 2000;
  const POLL_MAX_ATTEMPTS = 60;

  let garmentUrl = null;   // display URL (object URL or http)
  let garmentFile = null;  // set when user drops a file; uploaded at try-on
  let userFile = null;
  let backendBase = DEFAULT_BACKEND;

  const DEFAULT_GARMENT_SRC = 'assets/tshirt.png';
  const DEFAULT_SELFIE_SRC = 'assets/guy.png';

  const els = {
    garmentSquare: document.getElementById('garmentSquare'),
    garmentImg: document.getElementById('garmentImg'),
    garmentClear: document.getElementById('garmentClear'),
    selectGarment: document.getElementById('selectGarment'),
    selfieSquare: document.getElementById('selfieSquare'),
    selfieImg: document.getElementById('selfieImg'),
    selfieClear: document.getElementById('selfieClear'),
    userImage: document.getElementById('userImage'),
    triggerUpload: document.getElementById('triggerUpload'),
    promptInput: document.getElementById('promptInput'),
    tryOn: document.getElementById('tryOn'),
    status: document.getElementById('status'),
    resultSection: document.getElementById('resultSection'),
    resultImg: document.getElementById('resultImg'),
    downloadResult: document.getElementById('downloadResult'),
  };

  function setStatus(text, isError = false) {
    els.status.textContent = text;
    els.status.className = 'status' + (isError ? ' error' : text ? ' success' : '');
  }

  function showGarmentPreview(url, file) {
    garmentFile = file || null;
    garmentUrl = url;
    els.garmentImg.src = url;
    els.garmentSquare.classList.add('has-image');
    setStatus('Clothing selected, be sure to add your selfie');
    if (!url || !url.startsWith('blob:')) {
      chrome.storage.local.set({ atryonGarmentUrl: url });
    }
  }

  function clearGarment() {
    garmentUrl = null;
    garmentFile = null;
    els.garmentImg.src = DEFAULT_GARMENT_SRC;
    els.garmentSquare.classList.remove('has-image');
    chrome.storage.local.remove('atryonGarmentUrl');
    setStatus('');
  }

  function showSelfiePreview(file) {
    userFile = file;
    els.selfieImg.src = URL.createObjectURL(file);
    els.selfieSquare.classList.add('has-image');
    setStatus('Photo added');
  }

  function clearSelfie() {
    userFile = null;
    els.selfieImg.src = DEFAULT_SELFIE_SRC;
    els.selfieSquare.classList.remove('has-image');
    els.userImage.value = '';
    setStatus('');
  }

  function getBackendBase() {
    return backendBase.replace(/\/$/, '');
  }

  // Load saved backend URL and persisted garment
  chrome.storage.local.get(['atryonBackendUrl', 'atryonGarmentUrl'], function (data) {
    if (data.atryonBackendUrl) backendBase = data.atryonBackendUrl;
    if (data.atryonGarmentUrl) {
      garmentUrl = data.atryonGarmentUrl;
      els.garmentImg.src = data.atryonGarmentUrl;
      els.garmentSquare.classList.add('has-image');
      setStatus('Clothing selected, be sure to add your selfie');
    }
  });

  els.garmentClear.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    clearGarment();
  });

  els.selfieClear.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    clearSelfie();
  });

  // Drag and drop onto garment square
  function preventDefault(e) {
    e.preventDefault();
    e.stopPropagation();
  }
  els.garmentSquare.addEventListener('dragover', function (e) {
    preventDefault(e);
    e.dataTransfer.dropEffect = 'copy';
    els.garmentSquare.classList.add('drag-over');
  });
  els.garmentSquare.addEventListener('dragleave', function (e) {
    preventDefault(e);
    els.garmentSquare.classList.remove('drag-over');
  });
  els.garmentSquare.addEventListener('drop', function (e) {
    preventDefault(e);
    els.garmentSquare.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (!file.type.startsWith('image/')) {
        setStatus('Please drop an image file.', true);
        return;
      }
      showGarmentPreview(URL.createObjectURL(file), file);
      return;
    }
    const url = e.dataTransfer.getData('text/uri-list') || e.dataTransfer.getData('text/plain');
    if (url) {
      showGarmentPreview(url.trim());
      return;
    }
    setStatus('Drop an image file or an image from the page.', true);
  });

  // Select clothing from page (button still opens overlay)
  els.selectGarment.addEventListener('click', async function () {
    setStatus('Drag and drop an image from the page to the garment square…');
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id) {
        setStatus('No active tab', true);
        return;
      }
      chrome.tabs.sendMessage(tab.id, { type: 'START_SELECT' });
    } catch (e) {
      setStatus('Error: ' + (e.message || 'Could not access tab'), true);
    }
  });

  // Garment selected or selection cancelled (message from content script)
  chrome.runtime.onMessage.addListener(function (msg) {
    if (msg.type === 'GARMENT_SELECTED' && msg.src) {
      showGarmentPreview(msg.src);
    } else if (msg.type === 'CANCEL_SELECT') {
      setStatus('Selection cancelled');
    }
  });

  // Upload your photo (trigger hidden file input)
  els.triggerUpload.addEventListener('click', function () {
    els.userImage.click();
  });

  els.userImage.addEventListener('change', function () {
    const file = this.files && this.files[0];
    if (file) showSelfiePreview(file);
  });

  // Try on: upload → MIC → poll → download
  els.tryOn.addEventListener('click', async function () {
    if (!garmentUrl || !userFile) {
      setStatus('Please select clothing from the page and upload your photo.', true);
      return;
    }

    const base = getBackendBase();
    els.tryOn.disabled = true;
    setStatus('Uploading…');

    try {
      let garmentImage = garmentUrl;
      const form = new FormData();
      if (garmentFile) {
        form.append('files', garmentFile);
      }
      form.append('files', userFile);

      const uploadRes = await fetch(base + '/upload/images', {
        method: 'POST',
        body: form,
      });

      if (!uploadRes.ok) {
        const err = await uploadRes.text();
        throw new Error('Upload failed: ' + (err || uploadRes.status));
      }

      const uploadData = await uploadRes.json();
      const uploadIds = uploadData.upload_ids;
      if (!uploadIds || uploadIds.length === 0) throw new Error('No upload IDs returned');

      const userUploadId = uploadIds[uploadIds.length - 1];
      if (garmentFile && uploadIds.length >= 2) {
        garmentImage = 'upload:' + uploadIds[0];
      }
      setStatus('Starting try-on…');

      // 2) MIC request (garment URL or upload:id + upload:id for selfie)
      const prompt = (els.promptInput.value || ' ').trim() || ' ';
      const micRes = await fetch(base + '/bf_fl/mic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt,
          images: [garmentImage, 'upload:' + userUploadId],
        }),
      });

      if (!micRes.ok) {
        const err = await micRes.text();
        throw new Error('Try-on request failed: ' + (err || micRes.status));
      }

      const micData = await micRes.json();
      const pollingUrl = micData.polling_url;
      if (!pollingUrl) throw new Error('No polling URL returned');

      setStatus('Generating…');

      // 3) Poll until Ready
      let result = null;
      for (let i = 0; i < POLL_MAX_ATTEMPTS; i++) {
        const pollRes = await fetch(base + '/bf_fl/polling_requests?polling_url=' + encodeURIComponent(pollingUrl));
        if (!pollRes.ok) throw new Error('Poll failed: ' + pollRes.status);
        const pollData = await pollRes.json();
        if (pollData.status === 'Ready') {
          result = pollData.result;
          break;
        }
        if (pollData.status && pollData.status.toLowerCase() !== 'pending' && pollData.status.toLowerCase() !== 'processing') {
          throw new Error('Task failed: ' + (pollData.status || 'unknown'));
        }
        await new Promise(function (r) { setTimeout(r, POLL_INTERVAL_MS); });
      }

      if (!result || !result.sample) {
        throw new Error('No result image URL');
      }

      setStatus('Downloading result…');

      // 4) Download image via backend proxy
      const sampleUrl = result.sample;
      const downloadRes = await fetch(base + '/bf_fl/download_requests?url=' + encodeURIComponent(sampleUrl));
      if (!downloadRes.ok) {
        throw new Error('Download failed: ' + downloadRes.status + '. You can open the result URL in a new tab.');
      }
      const blob = await downloadRes.blob();
      const blobUrl = URL.createObjectURL(blob);

      els.resultImg.src = blobUrl;
      els.resultSection.hidden = false;
      setStatus('Done, scroll down to see the result');
    } catch (e) {
      setStatus(e.message || 'Something went wrong', true);
      els.resultSection.hidden = true;
    } finally {
      els.tryOn.disabled = false;
    }
  });

  // Download result image
  els.downloadResult.addEventListener('click', function () {
    const src = els.resultImg.src;
    if (!src) return;
    const a = document.createElement('a');
    a.href = src;
    a.download = 'atryon-result.png';
    a.click();
  });
})();
