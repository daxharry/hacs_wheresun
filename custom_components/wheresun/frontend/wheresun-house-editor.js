class WhereSunHouseEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.blocks = [];
    this.selectedId = null;
    this.dragMode = null;
    this.dragStart = null;
    this.nextId = 1;
    this.scale = 4;
    this.onChange = null;
  }

  connectedCallback() {
    if (!this.blocks.length) {
      this.blocks = [
        { id: "r1", x: 35, y: 40, width: 30, height: 25 },
      ];
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
      Math.max(0, ...this.blocks.map((block) => Number(String(block.id).replace(/\D/g, "")) || 0)) + 1;
    this.selectedId = null;
    this.redraw();
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
    const size = 20;
    const block = {
      id: `r${this.nextId++}`,
      x: 40,
      y: 40,
      width: size,
      height: size,
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
        <button type="button" id="add-square">Carré</button>
        <button type="button" id="add-rect">Rectangle</button>
        <button type="button" id="delete">Supprimer</button>
      </div>
      <div class="canvas-wrap">
        <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"></svg>
      </div>
      <div class="hint">Cliquez pour sélectionner, glissez pour déplacer, tirez les coins pour redimensionner.</div>
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
          parts.push(`<rect x="${x - 1.2}" y="${y - 1.2}" width="2.4" height="2.4" fill="#ffff66" />`);
        }
      }
    }

    svg.innerHTML = parts.join("");
  }
}

customElements.define("wheresun-house-editor", WhereSunHouseEditor);
