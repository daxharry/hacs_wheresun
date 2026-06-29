(function () {
  if (window.__wheresunLoaderInit) return;
  window.__wheresunLoaderInit = true;

  function loadMain() {
    if (window.__wheresunConfigFlowInit) return;
    if (document.querySelector("script[data-wheresun-main]")) return;
    const script = document.createElement("script");
    script.src = "/wheresun/wheresun-config-flow.js?v=0.2.1";
    script.dataset.wheresunMain = "1";
    script.async = true;
    document.head.appendChild(script);
  }

  loadMain();
  document.addEventListener("DOMContentLoaded", loadMain);
  setInterval(loadMain, 2000);
})();
