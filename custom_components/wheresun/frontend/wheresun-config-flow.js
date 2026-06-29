if (window.__wheresunConfigFlowInit) {
  // Already initialized.
} else {
  window.__wheresunConfigFlowInit = true;

  class WhereSunHouseEditor extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this.blocks = [];
      this.selectedId = null;
      this.dragMode = null;
      this.dragStart = null;
      this.nextId = 1;
      this.onChange = null;
    }

    connectedCallback() {
      if (!this.blocks.length) {
        this.blocks = [{ id: "r1", x: 35, y: 40, width: 30, height: 25 }];
        this.nextId = 2;
      }
      this.render();
      this.redraw();
    }

    setBlocks(blocks) {
      this.blocks = (blocks || []).map((block) => ({ ...block }));
      if (!this.blocks.length) {
        this.blocks = [{ id: "r1", x: 35, y: 40, width: 30, height: 25 }];
      }
      this.nextId =
        Math.max(
          0,
          ...this.blocks.map(
            (block) => Number(String(block.id).replace(/\D/g, "")) || 0
          )
        ) + 1;
      this.selectedId = null;
      if (this.shadowRoot && this.shadowRoot.querySelector("svg")) {
        this.redraw();
      }
      this.emitChange();
    }

    getBlocks() {
      return this.blocks.map(({ id, x, y, width, height }) => ({
        id,
        x: Math.round(x * 100) / 100,
        y: Math.round(y * 100) / 100,
        width: Math.round(width * 100) / 100,
        height: Math.round(height * 100) / 100,
      }));
    }

    emitChange() {
      if (typeof this.onChange === "function") {
        this.onChange(this.getBlocks());
      }
    }

    addSquare() {
      const block = {
        id: `r${this.nextId++}`,
        x: 40,
        y: 40,
        width: 20,
        height: 20,
      };
      this.blocks.push(block);
      this.selectedId = block.id;
      this.redraw();
      this.emitChange();
    }

    addRectangle() {
      const block = {
        id: `r${this.nextId++}`,
        x: 30,
        y: 45,
        width: 35,
        height: 18,
      };
      this.blocks.push(block);
      this.selectedId = block.id;
      this.redraw();
      this.emitChange();
    }

    deleteSelected() {
      if (!this.selectedId) return;
      this.blocks = this.blocks.filter((block) => block.id !== this.selectedId);
      this.selectedId = null;
      this.redraw();
      this.emitChange();
    }

    getSelected() {
      return this.blocks.find((block) => block.id === this.selectedId) || null;
    }

    svgPoint(event) {
      const svg = this.shadowRoot.querySelector("svg");
      const rect = svg.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * 100;
      const y = ((event.clientY - rect.top) / rect.height) * 100;
      return {
        x: Math.max(0, Math.min(100, x)),
        y: Math.max(0, Math.min(100, y)),
      };
    }

    hitTest(point) {
      for (let index = this.blocks.length - 1; index >= 0; index -= 1) {
        const block = this.blocks[index];
        if (
          point.x >= block.x &&
          point.x <= block.x + block.width &&
          point.y >= block.y &&
          point.y <= block.y + block.height
        ) {
          return block.id;
        }
      }
      return null;
    }

    resizeHandle(point, block) {
      const handle = 3;
      const corners = [
        ["nw", block.x, block.y],
        ["ne", block.x + block.width, block.y],
        ["sw", block.x, block.y + block.height],
        ["se", block.x + block.width, block.y + block.height],
      ];
      for (const [name, x, y] of corners) {
        if (Math.abs(point.x - x) <= handle && Math.abs(point.y - y) <= handle) {
          return name;
        }
      }
      return null;
    }

    clampBlock(block) {
      block.width = Math.max(5, Math.min(100, block.width));
      block.height = Math.max(5, Math.min(100, block.height));
      block.x = Math.max(0, Math.min(100 - block.width, block.x));
      block.y = Math.max(0, Math.min(100 - block.height, block.y));
    }

    onPointerDown(event) {
      const point = this.svgPoint(event);
      const selected = this.getSelected();
      if (selected) {
        const handle = this.resizeHandle(point, selected);
        if (handle) {
          this.dragMode = `resize-${handle}`;
          this.dragStart = { point, block: { ...selected } };
          return;
        }
      }

      const hit = this.hitTest(point);
      this.selectedId = hit;
      if (hit) {
        const block = this.getSelected();
        this.dragMode = "move";
        this.dragStart = {
          point,
          block: { ...block },
          offsetX: point.x - block.x,
          offsetY: point.y - block.y,
        };
      } else {
        this.dragMode = null;
      }
      this.redraw();
    }

    onPointerMove(event) {
      if (!this.dragMode || !this.dragStart) return;
      const point = this.svgPoint(event);
      const block = this.getSelected();
      if (!block) return;

      if (this.dragMode === "move") {
        block.x = point.x - this.dragStart.offsetX;
        block.y = point.y - this.dragStart.offsetY;
        this.clampBlock(block);
        this.redraw();
        this.emitChange();
        return;
      }

      const origin = this.dragStart.block;
      if (this.dragMode === "resize-se") {
        block.width = point.x - origin.x;
        block.height = point.y - origin.y;
      } else if (this.dragMode === "resize-sw") {
        block.x = point.x;
        block.width = origin.x + origin.width - point.x;
        block.height = point.y - origin.y;
      } else if (this.dragMode === "resize-ne") {
        block.y = point.y;
        block.width = point.x - origin.x;
        block.height = origin.y + origin.height - point.y;
      } else if (this.dragMode === "resize-nw") {
        block.x = point.x;
        block.y = point.y;
        block.width = origin.x + origin.width - point.x;
        block.height = origin.y + origin.height - point.y;
      }
      this.clampBlock(block);
      this.redraw();
      this.emitChange();
    }

    onPointerUp() {
      this.dragMode = null;
      this.dragStart = null;
    }

    render() {
      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; font-family: var(--ha-font-family, sans-serif); }
          .toolbar { display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
          button {
            border: 1px solid var(--divider-color, #ccc);
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color, #111);
            border-radius: 8px;
            padding: 8px 12px;
            cursor: pointer;
          }
          button:hover { background: var(--secondary-background-color, #f5f5f5); }
          .canvas-wrap {
            border: 1px solid var(--divider-color, #ccc);
            border-radius: 12px;
            overflow: hidden;
            background: #1a1919;
            max-width: 420px;
          }
          svg { width: 100%; height: auto; display: block; touch-action: none; }
          .hint { margin-top: 8px; color: var(--secondary-text-color, #666); font-size: 12px; }
        </style>
        <div class="toolbar">
          <button type="button" id="add-square">Square</button>
          <button type="button" id="add-rect">Rectangle</button>
          <button type="button" id="delete">Delete</button>
        </div>
        <div class="canvas-wrap">
          <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"></svg>
        </div>
        <div class="hint">Click to select, drag to move, pull corners to resize.</div>
      `;

      this.shadowRoot.getElementById("add-square").addEventListener("click", () => this.addSquare());
      this.shadowRoot.getElementById("add-rect").addEventListener("click", () => this.addRectangle());
      this.shadowRoot.getElementById("delete").addEventListener("click", () => this.deleteSelected());

      const svg = this.shadowRoot.querySelector("svg");
      svg.addEventListener("pointerdown", (event) => this.onPointerDown(event));
      svg.addEventListener("pointermove", (event) => this.onPointerMove(event));
      svg.addEventListener("pointerup", () => this.onPointerUp());
      svg.addEventListener("pointerleave", () => this.onPointerUp());
    }

    redraw() {
      const svg = this.shadowRoot.querySelector("svg");
      if (!svg) return;

      const parts = [
        '<rect width="100" height="100" fill="#1a1919" />',
        '<circle cx="50" cy="50" r="49" fill="none" stroke="#444" stroke-width="0.5" />',
      ];

      for (const block of this.blocks) {
        const selected = block.id === this.selectedId;
        parts.push(
          `<rect x="${block.x}" y="${block.y}" width="${block.width}" height="${block.height}" ` +
            `fill="${selected ? "#26bf75" : "#1b3024"}" stroke="${selected ? "#ffff66" : "#355f49"}" stroke-width="0.8" />`
        );
        if (selected) {
          const corners = [
            [block.x, block.y],
            [block.x + block.width, block.y],
            [block.x, block.y + block.height],
            [block.x + block.width, block.y + block.height],
          ];
          for (const [x, y] of corners) {
            parts.push(
              `<rect x="${x - 1.2}" y="${y - 1.2}" width="2.4" height="2.4" fill="#ffff66" />`
            );
          }
        }
      }

      svg.innerHTML = parts.join("");
    }
  }

  if (!customElements.get("wheresun-house-editor")) {
    customElements.define("wheresun-house-editor", WhereSunHouseEditor);
  }

  function walkRoots(root, visit) {
    if (!root) return;
    visit(root);
    const elements = root.querySelectorAll ? root.querySelectorAll("*") : [];
    elements.forEach((element) => {
      visit(element);
      if (element.shadowRoot) {
        walkRoots(element.shadowRoot, visit);
      }
    });
  }

  function getHass() {
    if (window.hass) return window.hass;
    const root = document.querySelector("home-assistant");
    if (root && root.hass) return root.hass;
    let found = null;
    walkRoots(document, (node) => {
      if (!found && node.hass) found = node.hass;
    });
    return found;
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
      text.includes("rendu des ombres")
    );
  }

  function findFlowIdDeep(root) {
    let found = null;
    walkRoots(root, (node) => {
      if (found) return;
      if (node.flowId) found = node.flowId;
      else if (node._flowId) found = node._flowId;
      else if (node.flow && node.flow.flow_id) found = node.flow.flow_id;
    });
    return found;
  }

  async function resolveFlowId(hass, root) {
    const fromDom = findFlowIdDeep(root);
    if (fromDom) return fromDom;
    try {
      const result = await hass.callWS({ type: "wheresun/editor_active" });
      return result.flow_id;
    } catch (error) {
      return null;
    }
  }

  async function saveBlocks(hass, flowId, blocks) {
    if (!hass || !flowId) return;
    try {
      await hass.callWS({
        type: "wheresun/editor_set",
        flow_id: flowId,
        blocks,
      });
    } catch (error) {
      console.warn("WhereSun: unable to save editor blocks", error);
    }
  }

  async function loadBlocks(hass, flowId) {
    if (!hass || !flowId) return [];
    try {
      const result = await hass.callWS({
        type: "wheresun/editor_get",
        flow_id: flowId,
      });
      return result.blocks || [];
    } catch (error) {
      return [];
    }
  }

  function hasEditorMounted(root) {
    let found = false;
    walkRoots(root, (node) => {
      if (found) return;
      if (
        node.localName === "wheresun-house-editor" ||
        node.classList?.contains("wheresun-editor-mount")
      ) {
        found = true;
      }
    });
    return found;
  }

  function findMountPoint(root) {
    let subentryFlow = null;
    walkRoots(root, (node) => {
      if (node.localName === "config-subentry-flow") {
        subentryFlow = node;
      }
    });
    if (subentryFlow?.shadowRoot) {
      const shadow = subentryFlow.shadowRoot;
      const content =
        shadow.querySelector(".content") ||
        shadow.querySelector("form") ||
        shadow.querySelector("div.config-flow") ||
        shadow.querySelector("div");
      if (content) return content;
      return shadow;
    }

    let configFlow = null;
    walkRoots(root, (node) => {
      if (node.localName === "config-flow") {
        configFlow = node;
      }
    });
    if (configFlow?.shadowRoot) {
      const shadow = configFlow.shadowRoot;
      const content =
        shadow.querySelector(".content") ||
        shadow.querySelector("form") ||
        shadow.querySelector("div.config-flow") ||
        shadow.querySelector("div");
      if (content) return content;
      return shadow;
    }

    let dialog = null;
    walkRoots(root, (node) => {
      if (node.localName === "ha-md-dialog" || node.localName === "ha-dialog") {
        dialog = node;
      }
    });
    if (dialog) {
      const slotContent = dialog.querySelector("config-subentry-flow, config-flow");
      if (slotContent) return findMountPoint(slotContent);
      if (dialog.shadowRoot) {
        const content = dialog.shadowRoot.querySelector(".content, article, div");
        if (content) return content;
      }
    }

    return root;
  }

  function hookSubmit(root, hass, flowId, editor) {
    walkRoots(root, (node) => {
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
        () => {
          saveBlocks(hass, flowId, editor.getBlocks());
        },
        true
      );
    });
  }

  async function mountEditor(root) {
    if (!isHouseStep(root)) return;
    if (hasEditorMounted(root)) return;

    const hass = getHass();
    if (!hass) {
      console.debug("WhereSun: hass not ready yet");
      return;
    }

    let flowId = await resolveFlowId(hass, root);
    for (let attempt = 0; !flowId && attempt < 10; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 200));
      flowId = await resolveFlowId(hass, root);
    }
    if (!flowId) {
      console.warn("WhereSun: no flow id for house editor");
      return;
    }

    const mountPoint = findMountPoint(root);
    const editor = document.createElement("wheresun-house-editor");
    editor.onChange = (blocks) => saveBlocks(hass, flowId, blocks);

    const wrapper = document.createElement("div");
    wrapper.className = "wheresun-editor-mount";
    wrapper.style.margin = "16px 0";
    wrapper.appendChild(editor);

    if (mountPoint.appendChild) {
      mountPoint.insertBefore(wrapper, mountPoint.firstChild);
    } else if (root.appendChild) {
      root.appendChild(wrapper);
    }

    const blocks = await loadBlocks(hass, flowId);
    editor.setBlocks(blocks.length ? blocks : undefined);
    await saveBlocks(hass, flowId, editor.getBlocks());
    hookSubmit(root, hass, flowId, editor);
  }

  function scanDialogs() {
    const roots = new Set();
    document.querySelectorAll("ha-dialog, ha-md-dialog, div[role='dialog']").forEach((node) => {
      roots.add(node);
    });
    if (!roots.size) {
      roots.add(document.body);
    }
    roots.forEach((root) => {
      if (!isHouseStep(root)) return;
      mountEditor(root).catch((error) => {
        console.warn("WhereSun editor mount failed", error);
      });
    });
  }

  const observer = new MutationObserver(() => scanDialogs());
  observer.observe(document.body, { childList: true, subtree: true });
  scanDialogs();
  setInterval(scanDialogs, 400);
}
