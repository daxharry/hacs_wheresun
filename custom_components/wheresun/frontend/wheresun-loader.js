(function () {
  if (window.__wheresunLoaderInit) return;
  window.__wheresunLoaderInit = true;

  const VERSION = "0.2.3";
  const SCRIPTS = ["/wheresun/wheresun-inject.js"];

  function loadScript(path) {
    const base = path.split("?")[0];
    if (document.querySelector(`script[data-wheresun-src="${base}"]`)) return;
    const script = document.createElement("script");
    script.src = `${path}?v=${VERSION}`;
    script.dataset.wheresunSrc = base;
    script.async = false;
    document.head.appendChild(script);
  }

  function bootstrap() {
    SCRIPTS.forEach((path) => loadScript(path));
  }

  bootstrap();
  document.addEventListener("DOMContentLoaded", bootstrap);
  setInterval(bootstrap, 1500);
})();
