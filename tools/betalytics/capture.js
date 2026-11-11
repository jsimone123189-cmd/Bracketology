/*
 * Betalytics pick capture — paste into the browser DevTools Console while
 * signed in to Betalytics, on the page that lists the picks.
 *
 * What it does (all locally, in your own tab):
 *   1. Re-reads the JSON data the page already loaded (same requests, your cookies).
 *   2. Records every JSON response the page loads from now on, so clicking
 *      through dates / tabs / "load more" adds to the capture.
 *   3. Shows a small panel: a counter, "Grab page text" (fallback for anything
 *      not loaded as JSON) and "Download", which saves one .json file.
 *
 * It never records request headers, cookies or tokens — only response bodies
 * and their URLs. Nothing is sent anywhere; the file only goes where you save it.
 */
(() => {
  if (window.__btlCapture) { window.__btlCapture.panel.style.display = 'block'; return; }

  const items = [];          // {kind, url, status, at, body}
  const seen = new Set();    // de-dup on url + body
  const MAX_BODY = 5e6;

  const panel = document.createElement('div');
  panel.style.cssText = 'position:fixed;z-index:2147483647;right:16px;bottom:16px;' +
    'background:#111;color:#fff;font:13px/1.4 system-ui,sans-serif;padding:12px 14px;' +
    'border-radius:10px;box-shadow:0 4px 18px rgba(0,0,0,.4);min-width:220px';
  panel.innerHTML =
    '<b>Betalytics capture</b><div id="btl-n" style="margin:6px 0">0 data responses</div>' +
    '<button id="btl-text">Grab page text</button> ' +
    '<button id="btl-dl">Download</button> ' +
    '<button id="btl-x" title="hide">×</button>';
  document.body.appendChild(panel);
  const counter = panel.querySelector('#btl-n');
  const refresh = () => {
    const d = items.filter(i => i.kind === 'json').length;
    const t = items.length - d;
    counter.textContent = `${d} data responses` + (t ? `, ${t} page snapshots` : '');
  };

  const add = (kind, url, status, body) => {
    if (body == null || body === '') return;
    if (typeof body === 'string' && body.length > MAX_BODY) return;
    const key = url + '|' + (typeof body === 'string' ? body : JSON.stringify(body));
    if (seen.has(key)) return;
    seen.add(key);
    items.push({ kind, url, status, at: new Date().toISOString(), body });
    refresh();
  };

  const tryJson = (url, status, text) => {
    const s = (text || '').trim();
    if (!s || (s[0] !== '{' && s[0] !== '[')) return;
    try { add('json', url, status, JSON.parse(s)); } catch (_) { /* not JSON */ }
  };

  // Record future fetch() responses.
  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    const res = await origFetch.apply(this, args);
    try {
      const url = res.url || String(args[0] && args[0].url || args[0]);
      res.clone().text().then(t => tryJson(url, res.status, t)).catch(() => {});
    } catch (_) {}
    return res;
  };

  // Record future XMLHttpRequest responses.
  const origOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this.addEventListener('load', () => {
      try {
        const t = this.responseType === '' || this.responseType === 'text'
          ? this.responseText
          : this.responseType === 'json' ? JSON.stringify(this.response) : '';
        tryJson(this.responseURL || String(url), this.status, t);
      } catch (_) {}
    });
    return origOpen.call(this, method, url, ...rest);
  };

  // Re-read data the page loaded before the script was pasted.
  const earlier = performance.getEntriesByType('resource')
    .filter(e => ['fetch', 'xmlhttprequest'].includes(e.initiatorType))
    .map(e => e.name);
  [...new Set(earlier)].forEach(url => {
    origFetch(url, { credentials: 'include' })
      .then(r => r.text().then(t => tryJson(url, r.status, t)))
      .catch(() => {});
  });

  panel.querySelector('#btl-text').onclick = () =>
    add('page_text', location.href, 200, document.body.innerText);

  panel.querySelector('#btl-dl').onclick = () => {
    const out = {
      tool: 'betalytics-capture', version: 1,
      page: location.href, captured_at: new Date().toISOString(), items,
    };
    const blob = new Blob([JSON.stringify(out)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `betalytics-capture-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a); a.click(); a.remove();
  };

  panel.querySelector('#btl-x').onclick = () => { panel.style.display = 'none'; };

  window.__btlCapture = { items, panel };
  console.log('Betalytics capture running. Click through dates/tabs, then press Download.');
})();
