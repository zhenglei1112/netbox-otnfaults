/**
 * Shared frame-rate debug toggle for MapLibre/Mapbox map windows.
 *
 * Default state is off. Press Ctrl+Alt+Shift+F inside a map window to toggle
 * the mapbox-gl-framerate control.
 */
(function () {
  "use strict";

  const HOTKEY_LABEL = "Ctrl+Alt+Shift+F";
  const DEFAULT_POSITION = "top-left";
  const registry = new WeakMap();

  function getControlClass() {
    if (window.FrameRateControl) return window.FrameRateControl;
    if (window.mapboxgl && window.mapboxgl.FrameRateControl) {
      return window.mapboxgl.FrameRateControl;
    }
    if (window.maplibregl && window.maplibregl.FrameRateControl) {
      return window.maplibregl.FrameRateControl;
    }
    return null;
  }

  function isToggleHotkey(event) {
    const ctrlKey = Boolean(event && event.ctrlKey);
    return Boolean(event && ctrlKey && event.altKey && event.shiftKey && event.code === "KeyF" && !event.repeat);
  }

  function normalizeOptions(options) {
    return Object.assign(
      {
        position: DEFAULT_POSITION,
        controlOptions: {
          background: "rgba(0, 0, 0, 0.82)",
          color: "#7cf859",
        },
      },
      options || {}
    );
  }

  function buildState(map, options) {
    return {
      map: map,
      control: null,
      enabled: false,
      options: normalizeOptions(options),
      keydownHandler: null,
    };
  }

  function toggle(state) {
    if (!state || !state.map) return false;

    if (state.enabled && state.control) {
      state.map.removeControl(state.control);
      state.control = null;
      state.enabled = false;
      return false;
    }

    const ControlClass = getControlClass();
    if (!ControlClass) {
      console.warn("[OTNMap] mapbox-gl-framerate is not loaded.");
      return false;
    }

    state.control = new ControlClass(state.options.controlOptions);
    state.map.addControl(state.control, state.options.position);
    state.enabled = true;
    return true;
  }

  function register(map, options) {
    if (!map || registry.has(map)) {
      return registry.get(map) || null;
    }

    const state = buildState(map, options);
    state.keydownHandler = function (event) {
      if (!isToggleHotkey(event)) return;
      event.preventDefault();
      event.stopPropagation();
      toggle(state);
    };

    document.addEventListener("keydown", state.keydownHandler);
    registry.set(map, state);

    return state;
  }

  function unregister(map) {
    const state = registry.get(map);
    if (!state) return;

    document.removeEventListener("keydown", state.keydownHandler);
    if (state.enabled && state.control) {
      state.map.removeControl(state.control);
    }
    registry.delete(map);
  }

  window.OTNMapFrameRateToggle = {
    hotkey: HOTKEY_LABEL,
    register: register,
    unregister: unregister,
    _isToggleHotkey: isToggleHotkey,
  };
})();
