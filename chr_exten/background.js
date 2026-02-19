chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch(function (err) { console.error(err); });

chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
  // Later: auth, retries, queueing
});
