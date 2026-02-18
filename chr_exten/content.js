let selecting = false;

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "START_SELECT") {
    selecting = true;
    document.body.style.cursor = "crosshair";
  }
});

document.addEventListener("click", (e) => {
  if (!selecting) return;

  const img = e.target.closest("img");
  if (!img) return;

  e.preventDefault();
  e.stopPropagation();

  chrome.runtime.sendMessage({
    type: "GARMENT_SELECTED",
    src: img.src
  });

  selecting = false;
  document.body.style.cursor = "default";
});
