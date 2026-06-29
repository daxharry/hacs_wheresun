const VERSION = "0.2.4";

function loadInject() {
  if (window.__wheresunInjectInit) return;
  const base = "/wheresun/wheresun-inject.js";
  if (document.querySelector(`script[data-wheresun-inject="1"]`)) return;
  const script = document.createElement("script");
  script.type = "module";
  script.src = `${base}?v=${VERSION}`;
  script.dataset.wheresunInject = "1";
  document.head.appendChild(script);
}

loadInject();
document.addEventListener("DOMContentLoaded", loadInject);
setInterval(loadInject, 2000);
