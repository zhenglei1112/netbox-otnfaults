class MapStylePreferenceControl {
  constructor({ mapStylePreferenceService, preferencesUrl, csrfToken }) {
    this.mapStylePreferenceService = mapStylePreferenceService;
    this.preferencesUrl = preferencesUrl;
    this.csrfToken = csrfToken || "";
    this.map = null;
    this.container = null;
    this.menu = null;
    this.statusElement = null;
    this.formElements = {};
    this.valueBadges = {};
    this.currentGroup = "province";
    this.hideTimer = null;
    this.boundPositionMenu = () => this.positionMenu();
    this.boundDocumentClick = (event) => {
      if (this.container?.contains(event.target) || this.menu?.contains(event.target)) return;
      this.hideMenu();
    };
    this.groupDefinitions = [
      {
        key: "province",
        label: "省界",
        desc: "填充与边界",
        icon: "mdi-map-outline",
        fields: [
          ["visible", "显示省界", "visibility"],
          ["fillColor", "填充颜色", "color"],
          ["fillOpacity", "填充透明度", "range", { min: "0", max: "1", step: "0.05" }],
          ["lineColor", "边线颜色", "color"],
          ["lineWidth", "边线宽度", "range", { min: "0", max: "10", step: "0.5" }],
          ["lineOpacity", "边线透明度", "range", { min: "0", max: "1", step: "0.05" }],
        ],
      },
      {
        key: "sites",
        label: "站点",
        desc: "点位与标签",
        icon: "mdi-map-marker-radius-outline",
        fields: [
          ["visible", "显示站点", "visibility"],
          ["circleColor", "点颜色", "color"],
          ["circleRadius", "点半径", "range", { min: "1", max: "24", step: "1" }],
          ["strokeColor", "描边颜色", "color"],
          ["strokeWidth", "描边宽度", "range", { min: "0", max: "8", step: "0.5" }],
          ["labelColor", "标签颜色", "color"],
          ["labelSize", "标签字号", "range", { min: "8", max: "36", step: "1" }],
          ["labelMinZoom", "标签最小缩放", "range", { min: "0", max: "24", step: "1" }],
        ],
      },
      {
        key: "paths",
        label: "路径",
        desc: "线路与高亮",
        icon: "mdi-vector-polyline",
        fields: [
          ["visible", "显示路径", "visibility"],
          ["lineColor", "路径颜色", "color"],
          ["lineWidth", "路径宽度", "range", { min: "0.5", max: "12", step: "0.5" }],
          ["lineOpacity", "路径透明度", "range", { min: "0", max: "1", step: "0.05" }],
          ["highlightColor", "高亮颜色", "color"],
          ["highlightWidth", "高亮宽度", "range", { min: "1", max: "20", step: "1" }],
        ],
      },
    ];
  }

  onAdd(map) {
    this.map = map;
    this.container = document.createElement("div");
    this.container.className = "maplibregl-ctrl maplibregl-ctrl-group map-style-control bg-body";
    this.container.style.overflow = "visible";
    this.container.addEventListener("click", (event) => event.stopPropagation());

    this.button = document.createElement("button");
    this.button.type = "button";
    this.button.className = "maplibregl-ctrl-icon toggle-button bg-transparent";
    this.button.title = "地图样式设置";
    this.button.innerHTML = '<i class="mdi mdi-palette-outline"></i>';
    this.button.addEventListener("click", (event) => {
      event.stopPropagation();
      this.toggleMenu();
    });
    this.button.onmouseenter = () => this.showMenu();

    this.container.onmouseleave = () => this.hideMenuWithDelay();
    this.container.appendChild(this.button);
    return this.container;
  }

  onRemove() {
    this.hideMenu();
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
    this.map = null;
    this.container = null;
  }

  toggleMenu() {
    if (this.menu) {
      this.hideMenu();
      return;
    }
    this.showMenu();
  }

  showMenu() {
    if (this.hideTimer) {
      clearTimeout(this.hideTimer);
      this.hideTimer = null;
    }
    this.createMenu();
  }

  hideMenuWithDelay() {
    this.hideTimer = setTimeout(() => this.hideMenu(), 200);
  }

  hideMenu() {
    if (this.menu && this.menu.parentNode) {
      this.menu.parentNode.removeChild(this.menu);
    }
    window.removeEventListener("resize", this.boundPositionMenu);
    document.removeEventListener("click", this.boundDocumentClick);
    this.menu = null;
    this.statusElement = null;
    this.formElements = {};
    this.valueBadges = {};
  }

  createMenu() {
    if (this.menu) return;

    const menu = document.createElement("div");
    menu.className = "view-control-menu map-style-menu card shadow bg-body p-2 border border-secondary-subtle";
    menu.onmouseenter = () => {
      if (this.hideTimer) clearTimeout(this.hideTimer);
    };
    menu.onmouseleave = () => this.hideMenuWithDelay();
    menu.addEventListener("click", (event) => event.stopPropagation());

    this.addHeader(menu, "地图样式");
    menu.appendChild(this.createGroupCards());
    this.addDivider(menu);

    const fieldContainer = document.createElement("div");
    fieldContainer.className = "map-style-fields";
    menu.appendChild(fieldContainer);

    this.groupDefinitions.forEach((group) => {
      fieldContainer.appendChild(this.createFieldSection(group));
    });

    this.addDivider(menu);
    this.statusElement = document.createElement("div");
    this.statusElement.className = "map-style-status text-body-secondary small px-2 py-1";
    this.statusElement.textContent = "调整后会立即预览，保存后作为你的默认样式。";
    menu.appendChild(this.statusElement);
    menu.appendChild(this.createActions());

    document.body.appendChild(menu);
    this.menu = menu;
    this.positionMenu();
    window.addEventListener("resize", this.boundPositionMenu);
    setTimeout(() => document.addEventListener("click", this.boundDocumentClick), 0);
    this._fillForm(this.mapStylePreferenceService.getConfig());
    this.showGroup(this.currentGroup);
  }

  positionMenu() {
    if (!this.menu || !this.container) return;

    const buttonRect = this.container.getBoundingClientRect();
    const viewportWidth = window.innerWidth || document.documentElement.clientWidth;
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    const menuWidth = Math.min(360, Math.max(300, viewportWidth - 24));
    const rightOfMenu = viewportWidth - buttonRect.left + 8;
    let left = viewportWidth - rightOfMenu - menuWidth;

    if (left < 12) {
      left = Math.max(12, viewportWidth - menuWidth - 12);
    }

    const top = Math.max(8, Math.min(buttonRect.top, viewportHeight - 120));
    this.menu.style.width = `${menuWidth}px`;
    this.menu.style.left = `${left}px`;
    this.menu.style.right = "auto";
    this.menu.style.top = `${top}px`;
  }

  addHeader(container, text) {
    const header = document.createElement("div");
    header.className = "dropdown-header bg-body-tertiary text-body-secondary rounded-1 mb-1";
    header.textContent = text;
    container.appendChild(header);
  }

  addDivider(container) {
    const divider = document.createElement("div");
    divider.className = "map-style-divider";
    container.appendChild(divider);
  }

  createGroupCards() {
    const groupCards = document.createElement("div");
    groupCards.className = "view-mode-cards map-style-group-cards";

    this.groupDefinitions.forEach((group) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = `mode-card map-style-group-card${group.key === this.currentGroup ? " active" : ""}`;
      card.dataset.group = group.key;
      card.innerHTML = `
        <div class="mode-card-label"><i class="mdi ${group.icon}"></i>${group.label}</div>
        <div class="mode-card-desc">${group.desc}</div>
      `;
      card.addEventListener("click", () => this.showGroup(group.key));
      groupCards.appendChild(card);
    });

    return groupCards;
  }

  createFieldSection(group) {
    const section = document.createElement("section");
    section.className = "map-style-section";
    section.dataset.group = group.key;

    group.fields.forEach(([fieldKey, labelText, inputType, attrs]) => {
      if (inputType === "visibility") {
        section.appendChild(this.createVisibilityField(group.key, fieldKey, labelText));
      } else if (inputType === "range") {
        section.appendChild(this.createRangeField(group.key, fieldKey, labelText, attrs));
      } else {
        section.appendChild(this.createColorField(group.key, fieldKey, labelText));
      }
    });

    return section;
  }

  createVisibilityField(groupKey, fieldKey, labelText) {
    const wrapper = this.createFieldWrapper(labelText, "map-style-visibility-row");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.hidden = true;
    this.registerField(groupKey, fieldKey, input);

    const toggle = document.createElement("div");
    toggle.className = "map-style-visibility-cards";
    const showButton = this.createVisibilityButton("显示", true, input);
    const hideButton = this.createVisibilityButton("隐藏", false, input);
    input.updateControl = () => {
      showButton.classList.toggle("active", input.checked);
      hideButton.classList.toggle("active", !input.checked);
    };

    toggle.appendChild(showButton);
    toggle.appendChild(hideButton);
    wrapper.appendChild(toggle);
    return wrapper;
  }

  createVisibilityButton(text, value, input) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "map-style-visibility-card";
    button.textContent = text;
    button.addEventListener("click", () => {
      input.checked = value;
      input.updateControl();
      this.preview();
    });
    return button;
  }

  createRangeField(groupKey, fieldKey, labelText, attrs) {
    const wrapper = this.createFieldWrapper(labelText);
    const valueBadge = document.createElement("span");
    valueBadge.className = "map-style-range-value";
    wrapper.querySelector(".map-style-field-label").appendChild(valueBadge);

    const input = document.createElement("input");
    input.type = "range";
    input.className = "time-range-slider map-style-slider";
    Object.entries(attrs || {}).forEach(([key, value]) => input.setAttribute(key, value));
    input.addEventListener("input", () => {
      this.updateRangeDisplay(input, valueBadge, attrs);
      this.preview();
    });

    wrapper.appendChild(input);
    this.registerField(groupKey, fieldKey, input);
    this.registerValueBadge(groupKey, fieldKey, valueBadge);
    return wrapper;
  }

  createColorField(groupKey, fieldKey, labelText) {
    const wrapper = this.createFieldWrapper(labelText);
    const swatch = document.createElement("label");
    swatch.className = "map-style-color-swatch";

    const input = document.createElement("input");
    input.type = "color";
    input.className = "map-style-color-input";
    input.addEventListener("input", () => {
      input.updateSwatch(input.value);
      this.preview();
    });
    input.updateSwatch = (value) => {
      swatch.style.setProperty("--map-style-swatch-color", value);
    };

    const value = document.createElement("span");
    value.className = "map-style-color-value";
    input.updateValueText = () => {
      value.textContent = input.value.toUpperCase();
    };
    input.addEventListener("input", () => input.updateValueText());

    swatch.appendChild(input);
    swatch.appendChild(value);
    wrapper.appendChild(swatch);
    this.registerField(groupKey, fieldKey, input);
    return wrapper;
  }

  createFieldWrapper(labelText, extraClassName = "") {
    const wrapper = document.createElement("div");
    wrapper.className = `map-style-field ${extraClassName}`.trim();

    const label = document.createElement("div");
    label.className = "map-style-field-label";
    label.textContent = labelText;
    wrapper.appendChild(label);
    return wrapper;
  }

  createActions() {
    const actions = document.createElement("div");
    actions.className = "map-style-actions";
    actions.appendChild(this.createActionButton("恢复默认", "btn-outline-secondary", () => this.reset()));
    actions.appendChild(this.createActionButton("保存默认", "btn-primary", () => this.save()));
    return actions;
  }

  createActionButton(text, className, handler) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `btn btn-sm ${className}`;
    button.textContent = text;
    button.addEventListener("click", handler);
    return button;
  }

  showGroup(groupKey) {
    this.currentGroup = groupKey;
    if (!this.menu) return;

    this.menu.querySelectorAll(".map-style-section").forEach((section) => {
      section.hidden = section.dataset.group !== groupKey;
    });
    this.menu.querySelectorAll(".map-style-group-card").forEach((card) => {
      card.classList.toggle("active", card.dataset.group === groupKey);
    });
  }

  registerField(groupKey, fieldKey, input) {
    if (!this.formElements[groupKey]) this.formElements[groupKey] = {};
    this.formElements[groupKey][fieldKey] = input;
  }

  registerValueBadge(groupKey, fieldKey, valueBadge) {
    if (!this.valueBadges[groupKey]) this.valueBadges[groupKey] = {};
    this.valueBadges[groupKey][fieldKey] = valueBadge;
  }

  _fillForm(config) {
    ["province", "sites", "paths"].forEach((groupKey) => {
      Object.entries(this.formElements[groupKey] || {}).forEach(([fieldKey, element]) => {
        const value = config[groupKey][fieldKey];
        if (element.type === "checkbox") {
          element.checked = Boolean(value);
          if (typeof element.updateControl === "function") element.updateControl();
        } else if (element.type === "color") {
          element.value = this.toColorInputValue(value);
          if (typeof element.updateSwatch === "function") element.updateSwatch(element.value);
          if (typeof element.updateValueText === "function") element.updateValueText();
        } else {
          element.value = value;
          const valueBadge = this.valueBadges[groupKey]?.[fieldKey];
          if (valueBadge) this.updateRangeDisplay(element, valueBadge, element);
        }
      });
    });
  }

  _collectFormData() {
    const styleConfig = { province: {}, sites: {}, paths: {} };
    ["province", "sites", "paths"].forEach((groupKey) => {
      Object.entries(this.formElements[groupKey] || {}).forEach(([fieldKey, element]) => {
        if (element.type === "checkbox") {
          styleConfig[groupKey][fieldKey] = element.checked;
        } else if (element.type === "range") {
          styleConfig[groupKey][fieldKey] = Number(element.value);
        } else {
          styleConfig[groupKey][fieldKey] = element.value;
        }
      });
    });
    return styleConfig;
  }

  updateRangeDisplay(input, valueBadge, attrs) {
    valueBadge.textContent = this.formatRangeValue(input.value, attrs);
    const min = Number(input.min || attrs?.min || 0);
    const max = Number(input.max || attrs?.max || 100);
    const value = Number(input.value);
    const percent = max === min ? 0 : ((value - min) / (max - min)) * 100;
    input.style.setProperty(
      "background-image",
      `linear-gradient(to right, #0d6efd 0%, #0d6efd ${percent}%, transparent ${percent}%, transparent 100%)`,
      "important",
    );
    input.style.setProperty("background-color", "var(--slider-track, #dee2e6)", "important");
  }

  formatRangeValue(value, attrs) {
    const numericValue = Number(value);
    const step = Number(attrs?.step || 1);
    if (!Number.isFinite(numericValue)) return String(value);
    if (step < 1) return numericValue.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
    return String(Math.round(numericValue));
  }

  toColorInputValue(value) {
    if (typeof value !== "string") return "#000000";
    if (/^#[0-9a-f]{6}$/i.test(value)) return value;
    const rgb = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
    if (!rgb) return "#000000";
    return `#${[rgb[1], rgb[2], rgb[3]]
      .map((part) => Number(part).toString(16).padStart(2, "0"))
      .join("")}`;
  }

  setStatus(message, isError = false) {
    if (!this.statusElement) return;
    this.statusElement.textContent = message;
    this.statusElement.classList.toggle("text-danger", isError);
    this.statusElement.classList.toggle("text-body-secondary", !isError);
  }

  preview() {
    const styleConfig = this._collectFormData();
    this.mapStylePreferenceService.apply(styleConfig);
    this.setStatus("已应用预览。");
  }

  reset() {
    const styleConfig = this.mapStylePreferenceService.resetToDefaults();
    this._fillForm(styleConfig);
    this.setStatus("已恢复默认样式。");
  }

  async save() {
    const styleConfig = this._collectFormData();
    this.mapStylePreferenceService.apply(styleConfig);

    try {
      const response = await fetch(this.preferencesUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCsrfToken(),
        },
        body: JSON.stringify({ style_config: styleConfig }),
      });
      const payload = await this.parseJsonResponse(response);
      if (!response.ok) {
        throw new Error(payload.error || "保存失败");
      }
      this.mapStylePreferenceService.apply(payload.style_config || styleConfig);
      this._fillForm(this.mapStylePreferenceService.getConfig());
      this.setStatus("已保存为你的默认样式。");
    } catch (error) {
      this.setStatus(error.message || "保存失败", true);
    }
  }

  getCsrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : this.csrfToken;
  }

  async parseJsonResponse(response) {
    const text = await response.text();
    if (!text) return {};

    try {
      return JSON.parse(text);
    } catch (error) {
      if (response.ok) throw error;
      return { error: `保存失败：HTTP ${response.status}` };
    }
  }
}

window.MapStylePreferenceControl = MapStylePreferenceControl;
