(function () {
  const EDITOR_STEPS = new Set(["house", "house_reconfigure"]);
  const SCRIPT_ID = "wheresun-house-editor-script";
  const FLOW_SCRIPT_ID = "wheresun-config-flow-script";

  function loadScript(id, src) {
    if (document.getElementById(id)) {
      return Promise.resolve();
    }
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.id = id;
      script.type = "module";
      script.src = src;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Unable to load ${src}`));
      document.head.appendChild(script);
    });
  }

  function findBlocksInput(root) {
    const inputs = root.querySelectorAll("ha-form, form, .mdc-dialog__content");
    for (const container of inputs) {
      const field = container.querySelector('textarea[name="blocks_json"], input[name="blocks_json"]');
      if (field) {
        return field;
      }
    }
    const direct = root.querySelector('textarea[name="blocks_json"], input[name="blocks_json"]');
    return direct || null;
  }

  function findFlowId(root) {
    const dialog = root.closest("ha-dialog") || root;
    const flow = dialog.__flow || dialog.flow || null;
    if (flow && flow.flowId) {
      return flow.flowId;
    }
    return null;
  }

  function syncInput(editor, input) {
    const blocks = editor.getBlocks();
    input.value = JSON.stringify(blocks);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function mountEditor(container, input) {
    if (container.querySelector("wheresun-house-editor")) {
      return;
    }

    let initial = [];
    try {
      initial = JSON.parse(input.value || "[]");
    } catch (error) {
      initial = [];
    }

    const wrapper = document.createElement("div");
    wrapper.style.marginBottom = "16px";
    const editor = document.createElement("wheresun-house-editor");
    editor.setBlocks(initial);
    editor.onChange = () => syncInput(editor, input);
    wrapper.appendChild(editor);
    container.insertBefore(wrapper, input.closest("ha-form-field, .formfield, div") || input);

    const field = input.closest("ha-form-field, .formfield");
    if (field) {
      field.style.display = "none";
    } else {
      input.style.display = "none";
    }

    syncInput(editor, input);
  }

  async function enhanceDialog(dialog) {
    const content = dialog.querySelector(".content, .mdc-dialog__content, ha-dialog");
    if (!content) {
      return;
    }

    const stepNode = content.querySelector('[class*="step"], h1, h2, .header');
    const stepText = (dialog.textContent || "").toLowerCase();
    const isEditorStep =
      stepText.includes("maison") ||
      stepText.includes("house") ||
      stepText.includes("blocks_json");

    const input = findBlocksInput(dialog);
    if (!input || !isEditorStep) {
      return;
    }

    await loadScript(SCRIPT_ID, "/wheresun/wheresun-house-editor.js");
    mountEditor(content, input);
  }

  function scanDialogs() {
    const dialogs = document.querySelectorAll("ha-dialog, div[role='dialog']");
    dialogs.forEach((dialog) => {
      if (dialog.__wheresunEnhanced) {
        return;
      }
      const input = findBlocksInput(dialog);
      if (!input) {
        return;
      }
      dialog.__wheresunEnhanced = true;
      enhanceDialog(dialog).catch((error) => {
        console.warn("WhereSun editor failed to mount", error);
        dialog.__wheresunEnhanced = false;
      });
    });
  }

  const observer = new MutationObserver(() => scanDialogs());
  observer.observe(document.body, { childList: true, subtree: true });
  scanDialogs();
})();
