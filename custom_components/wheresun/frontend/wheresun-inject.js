(function () {
  if (window.__wheresunInjectInit) return;
  window.__wheresunInjectInit = true;

  const VERSION = "0.2.2";
  const EDITOR_PATH = "/wheresun/editor.html";

  function walkTree(root, visit) {
    if (!root) return;
    visit(root);
    if (root.shadowRoot) walkTree(root.shadowRoot, visit);
    if (root.querySelectorAll) {
      root.querySelectorAll("*").forEach((child) => {
        visit(child);
        if (child.shadowRoot) walkTree(child.shadowRoot, visit);
      });
    }
  }

  function getHass() {
    if (window.hass) return window.hass;
    const roots = [document];
    if (document.body) roots.push(document.body);
    let found = null;
    for (const root of roots) {
      walkTree(root, (node) => {
        if (!found && node.hass) found = node.hass;
      });
      if (found) return found;
    }
    const ha = document.querySelector("home-assistant");
    if (ha && ha.hass) return ha.hass;
    const hc = document.querySelector("hc-main");
    if (hc && hc.hass) return hc.hass;
    return null;
  }

  function isHouseStep(root) {
    const text = (root.textContent || "").toLowerCase();
    return (
      text.includes("house layout") ||
      text.includes("plan de la maison") ||
      text.includes("edit house layout") ||
      text.includes("modifier le plan") ||
      text.includes("build your house") ||
      text.includes("construisez votre maison") ||
      text.includes("shadow rendering") ||
      text.includes("rendu des ombres") ||
      text.includes("squares and rectangles") ||
      text.includes("carrés et des rectangles")
    );
  }

  function findFlowId(root) {
    let found = null;
    walkTree(root, (node) => {
      if (found) return;
      if (node.flowId) found = node.flowId;
      else if (node._flowId) found = node._flowId;
      else if (node.flow && node.flow.flow_id) found = node.flow.flow_id;
    });
    return found;
  }

  async function resolveFlowId(hass, root) {
    const fromDom = findFlowId(root);
    if (fromDom) return fromDom;
    try {
      const result = await hass.callWS({ type: "wheresun/editor_active" });
      return result.flow_id || null;
    } catch (err) {
      return null;
    }
  }

  function hasIframe(root) {
    let found = false;
    walkTree(root, (node) => {
      if (found) return;
      if (node.localName === "iframe" && node.dataset && node.dataset.wheresunEditor) {
        found = true;
      }
    });
    return found;
  }

  function findMountPoint(root) {
    let mountPoint = null;

    walkTree(root, (node) => {
      if (mountPoint) return;
      if (node.localName === "ha-markdown") mountPoint = node;
      else if (node.classList && node.classList.contains("step-description")) mountPoint = node;
    });

    if (mountPoint && mountPoint.parentElement) {
      return { parent: mountPoint.parentElement, after: mountPoint };
    }

    let flowEl = null;
    walkTree(root, (node) => {
      if (
        node.localName === "config-subentry-flow" ||
        node.localName === "config-flow" ||
        node.localName === "dialog-data-entry-flow"
      ) {
        flowEl = node;
      }
    });

    if (flowEl && flowEl.shadowRoot) {
      const content =
        flowEl.shadowRoot.querySelector(".content") ||
        flowEl.shadowRoot.querySelector("form") ||
        flowEl.shadowRoot.querySelector("div");
      if (content) return { parent: content, after: null };
    }

    walkTree(root, (node) => {
      if (mountPoint) return;
      if (node.localName === "ha-md-dialog" || node.localName === "ha-dialog") {
        if (node.shadowRoot) {
          const content = node.shadowRoot.querySelector(".content, article, .body, div");
          if (content) mountPoint = content;
        }
      }
    });

    if (mountPoint) return { parent: mountPoint, after: null };
    return { parent: root, after: null };
  }

  function hookSubmit(root, flowId) {
    walkTree(root, (node) => {
      if (!node.tagName) return;
      const tag = node.tagName.toLowerCase();
      if (tag !== "mwc-button" && tag !== "ha-button" && tag !== "button") return;
      if (node.__wheresunSubmitHooked) return;
      const label = (node.textContent || "").toLowerCase();
      if (!label.includes("submit") && !label.includes("valider") && !label.includes("envoyer")) {
        return;
      }
      node.__wheresunSubmitHooked = true;
      node.addEventListener(
        "click",
        (event) => {
          if (event.__wheresunBypass) return;
          const iframe = document.querySelector('iframe[data-wheresun-editor="1"]');
          if (!iframe || !iframe.contentWindow) return;
          event.preventDefault();
          event.stopImmediatePropagation();
          const button = node;
          const finish = () => {
            const click = new MouseEvent("click", { bubbles: true, cancelable: true });
            click.__wheresunBypass = true;
            button.dispatchEvent(click);
          };
          const onSaved = (message) => {
            if (message.data && message.data.type === "wheresun-saved") {
              window.removeEventListener("message", onSaved);
              finish();
            }
          };
          window.addEventListener("message", onSaved);
          iframe.contentWindow.postMessage({ type: "wheresun-save", flow_id: flowId }, "*");
          setTimeout(() => {
            window.removeEventListener("message", onSaved);
            finish();
          }, 600);
        },
        true
      );
    });
  }

  async function mountEditor(root) {
    if (!isHouseStep(root)) return;
    if (hasIframe(root)) return;

    const hass = getHass();
    if (!hass) return;

    let flowId = await resolveFlowId(hass, root);
    for (let attempt = 0; !flowId && attempt < 25; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 200));
      flowId = await resolveFlowId(hass, root);
    }
    if (!flowId) {
      console.warn("WhereSun: unable to resolve config flow id");
      return;
    }

    const mount = findMountPoint(root);
    if (!mount.parent) return;

    const wrapper = document.createElement("div");
    wrapper.className = "wheresun-editor-mount";
    wrapper.dataset.wheresunEditor = "1";
    wrapper.style.cssText = "margin: 12px 0 16px; width: 100%; max-width: 480px;";

    const iframe = document.createElement("iframe");
    iframe.dataset.wheresunEditor = "1";
    iframe.title = "WhereSun house editor";
    iframe.src = `${EDITOR_PATH}?flow_id=${encodeURIComponent(flowId)}&v=${VERSION}`;
    iframe.style.cssText =
      "width: 100%; height: 420px; border: 1px solid var(--divider-color, #444); border-radius: 12px; background: #111;";
    iframe.setAttribute("loading", "eager");

    wrapper.appendChild(iframe);

    if (mount.after) {
      mount.after.insertAdjacentElement("afterend", wrapper);
    } else if (mount.parent.firstChild) {
      mount.parent.insertBefore(wrapper, mount.parent.firstChild);
    } else {
      mount.parent.appendChild(wrapper);
    }

    hookSubmit(root, flowId);
  }

  function collectRoots() {
    const roots = new Set();
    document.querySelectorAll(
      "ha-dialog, ha-md-dialog, dialog-data-entry-flow, div[role='dialog']"
    ).forEach((node) => roots.add(node));
    document.querySelectorAll("config-subentry-flow, config-flow").forEach((node) => {
      let parent = node;
      while (parent) {
        if (
          parent.localName === "ha-dialog" ||
          parent.localName === "ha-md-dialog" ||
          parent.localName === "dialog-data-entry-flow"
        ) {
          roots.add(parent);
          break;
        }
        parent = parent.parentElement || parent.parentNode;
      }
      if (!parent) roots.add(node);
    });
    if (!roots.size && document.body) roots.add(document.body);
    return roots;
  }

  function scan() {
    collectRoots().forEach((root) => {
      if (!isHouseStep(root)) return;
      mountEditor(root).catch((err) => console.warn("WhereSun mount failed", err));
    });
  }

  const observer = new MutationObserver(() => scan());
  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener("DOMContentLoaded", () => {
      observer.observe(document.body, { childList: true, subtree: true });
      scan();
    });
  }
  scan();
  setInterval(scan, 300);
})();
