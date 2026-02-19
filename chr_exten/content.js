(function () {
  let overlay = null;
  let tooltipEl = null;
  let escHandler = null;
  let lastOutlinedImg = null;

  function showOverlay() {
    if (overlay) return;
    overlay = document.createElement('div');
    overlay.id = 'atryon-select-overlay';
    overlay.style.cssText = [
      'position: fixed; inset: 0;',
      'background: rgba(0,0,0,0.05);',
      'cursor: crosshair;',
      'z-index: 2147483647;',
      'pointer-events: auto;'
    ].join(' ');
    document.body.appendChild(overlay);

    tooltipEl = document.createElement('div');
    tooltipEl.textContent = 'Click to select clothing';
    tooltipEl.style.cssText = [
      'position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);',
      'padding: 8px 16px; background: #3d3630; color: #e8e2da;',
      'font-family: Roboto, sans-serif; font-size: 14px; border-radius: 8px;',
      'z-index: 2147483647; pointer-events: none; box-shadow: 0 2px 8px rgba(0,0,0,0.2);'
    ].join(' ');
    document.body.appendChild(tooltipEl);

    overlay.addEventListener('mousemove', onOverlayMouseMove);
    overlay.addEventListener('click', onOverlayClick);

    escHandler = function (e) {
      if (e.key === 'Escape') {
        hideOverlay();
        chrome.runtime.sendMessage({ type: 'CANCEL_SELECT' });
      }
    };
    document.addEventListener('keydown', escHandler);
  }

  function hideOverlay() {
    if (escHandler) {
      document.removeEventListener('keydown', escHandler);
      escHandler = null;
    }
    if (overlay) {
      overlay.removeEventListener('mousemove', onOverlayMouseMove);
      overlay.removeEventListener('click', onOverlayClick);
      overlay.remove();
      overlay = null;
    }
    if (tooltipEl) {
      tooltipEl.remove();
      tooltipEl = null;
    }
    document.body.style.cursor = '';
    clearHoverOutline();
  }

  function clearHoverOutline() {
    if (lastOutlinedImg) {
      lastOutlinedImg.classList.remove('atryon-hover-outline');
      lastOutlinedImg.style.outline = '';
      lastOutlinedImg.style.outlineOffset = '';
      lastOutlinedImg = null;
    }
  }

  function onOverlayMouseMove(e) {
    var elements = document.elementsFromPoint(e.clientX, e.clientY);
    var img = null;
    for (var i = 0; i < elements.length; i++) {
      if (elements[i].tagName === 'IMG') {
        img = elements[i];
        break;
      }
    }
    if (img !== lastOutlinedImg) {
      clearHoverOutline();
      if (img) {
        img.classList.add('atryon-hover-outline');
        img.style.outline = '3px solid #6b7c5c';
        img.style.outlineOffset = '2px';
        lastOutlinedImg = img;
      }
    }
  }

  function onOverlayClick(e) {
    var elements = document.elementsFromPoint(e.clientX, e.clientY);
    var img = null;
    for (var i = 0; i < elements.length; i++) {
      if (elements[i].tagName === 'IMG') {
        img = elements[i];
        break;
      }
    }
    if (!img) return;
    e.preventDefault();
    e.stopPropagation();
    chrome.storage.local.set({ atryonGarmentUrl: img.src });
    chrome.runtime.sendMessage({ type: 'GARMENT_SELECTED', src: img.src });
    hideOverlay();
  }

  chrome.runtime.onMessage.addListener(function (msg) {
    if (msg.type === 'START_SELECT') {
      showOverlay();
    }
  });
})();
