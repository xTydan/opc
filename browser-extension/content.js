(() => {
  if (window.__olxPcCollectorInstalled) return;
  window.__olxPcCollectorInstalled = true;
  const normalize = (href) => {
    try {
      const url = new URL(href, location.href);
      if (url.hostname !== "www.olx.pl" && url.hostname !== "olx.pl") return null;
      if (!url.pathname.startsWith("/d/oferta/")) return null;
      url.search = "";
      url.hash = "";
      return url.origin + url.pathname;
    } catch { return null; }
  };
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.action !== "COLLECT_LINKS") return;
    const urls = [...new Set([...document.querySelectorAll('a[href*="/d/oferta/"]')]
      .map(a => normalize(a.href)).filter(Boolean))];
    sendResponse({urls});
  });
})();