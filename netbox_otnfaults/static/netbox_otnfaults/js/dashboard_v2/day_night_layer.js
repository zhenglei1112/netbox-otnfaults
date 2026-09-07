const DEG_TO_RAD = Math.PI / 180;
const RAD_TO_DEG = 180 / Math.PI;
const GRID_STEP = 2;
const MAX_MERCATOR_LATITUDE = 85.051129;
const UPDATE_INTERVAL_MS = 60000;

function normalizeDegrees(value) {
  return ((value % 360) + 360) % 360;
}

function normalizeLongitude(value) {
  const normalized = normalizeDegrees(value + 180) - 180;
  return normalized === -180 ? 180 : normalized;
}

function mercatorY(latitudeDegrees) {
  const latitude = Math.max(
    -MAX_MERCATOR_LATITUDE,
    Math.min(MAX_MERCATOR_LATITUDE, latitudeDegrees),
  ) * DEG_TO_RAD;
  return (1 - (Math.log(Math.tan(latitude) + (1 / Math.cos(latitude))) / Math.PI)) / 2;
}

export function solarSubpoint(date = new Date()) {
  const julianDate = (date.getTime() / 86400000) + 2440587.5;
  const daysSinceJ2000 = julianDate - 2451545;
  const meanLongitude = normalizeDegrees(280.46 + (0.9856474 * daysSinceJ2000));
  const meanAnomaly = normalizeDegrees(357.528 + (0.9856003 * daysSinceJ2000)) * DEG_TO_RAD;
  const eclipticLongitude = (
    meanLongitude
    + (1.915 * Math.sin(meanAnomaly))
    + (0.02 * Math.sin(2 * meanAnomaly))
  ) * DEG_TO_RAD;
  const obliquity = (23.439 - (0.0000004 * daysSinceJ2000)) * DEG_TO_RAD;
  const declination = Math.asin(Math.sin(obliquity) * Math.sin(eclipticLongitude));
  const rightAscension = Math.atan2(
    Math.cos(obliquity) * Math.sin(eclipticLongitude),
    Math.cos(eclipticLongitude),
  ) * RAD_TO_DEG;
  const siderealDegrees = normalizeDegrees(280.46061837 + (360.98564736629 * daysSinceJ2000));
  return {
    longitude: normalizeLongitude(rightAscension - siderealDegrees),
    latitude: declination * RAD_TO_DEG,
  };
}

export function surfaceIllumination(longitude, latitude, sunPosition) {
  const longitudeDifference = (longitude - sunPosition.longitude) * DEG_TO_RAD;
  const latitudeRadians = latitude * DEG_TO_RAD;
  const sunLatitude = sunPosition.latitude * DEG_TO_RAD;
  return (
    (Math.sin(latitudeRadians) * Math.sin(sunLatitude))
    + (Math.cos(latitudeRadians) * Math.cos(sunLatitude) * Math.cos(longitudeDifference))
  );
}

function smoothstep(start, end, value) {
  const progress = Math.max(0, Math.min(1, (value - start) / (end - start)));
  return progress * progress * (3 - (2 * progress));
}

export function dayNightStrengths(illumination) {
  return {
    day: smoothstep(0.08, 0.68, illumination),
    night: 1 - smoothstep(-0.18, 0.1, illumination),
  };
}

function buildSurfaceVertices() {
  const vertices = [];
  const latitudes = [-MAX_MERCATOR_LATITUDE];
  for (let latitude = -84; latitude <= 84; latitude += GRID_STEP) latitudes.push(latitude);
  latitudes.push(MAX_MERCATOR_LATITUDE);
  const appendVertex = (longitude, latitude) => {
    vertices.push({
      longitude,
      latitude,
      x: (longitude + 180) / 360,
      y: mercatorY(latitude),
    });
  };
  for (let latitudeIndex = 0; latitudeIndex < latitudes.length - 1; latitudeIndex += 1) {
    const latitude = latitudes[latitudeIndex];
    const north = latitudes[latitudeIndex + 1];
    for (let longitude = -180; longitude < 180; longitude += GRID_STEP) {
      const east = longitude + GRID_STEP;
      appendVertex(longitude, latitude);
      appendVertex(east, latitude);
      appendVertex(longitude, north);
      appendVertex(longitude, north);
      appendVertex(east, latitude);
      appendVertex(east, north);
    }
  }
  return vertices;
}

function compileShader(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader) || '昼夜着色器编译失败';
    gl.deleteShader(shader);
    throw new Error(message);
  }
  return shader;
}

function createShader(gl, shaderDescription) {
  const vertexSource = `#version 300 es
    ${shaderDescription.vertexShaderPrelude}
    ${shaderDescription.define}
    in vec2 a_pos;
    in float a_illumination;
    out float v_illumination;
    void main() {
      v_illumination = a_illumination;
      gl_Position = projectTile(a_pos);
    }
  `;
  const fragmentSource = `#version 300 es
    precision highp float;
    in float v_illumination;
    out vec4 fragColor;
    float smoothValue(float start, float end, float value) {
      float progress = clamp((value - start) / (end - start), 0.0, 1.0);
      return progress * progress * (3.0 - (2.0 * progress));
    }
    void main() {
      float day = smoothValue(0.08, 0.68, v_illumination);
      float night = 1.0 - smoothValue(-0.18, 0.1, v_illumination);
      vec3 dayColor = vec3(0.30, 0.50, 0.72);
      vec3 nightColor = vec3(0.0, 0.008, 0.025);
      float dayOpacity = day * 0.20;
      float nightOpacity = night * 0.68;
      float opacity = max(dayOpacity, nightOpacity);
      float dayMix = dayOpacity / max(dayOpacity + nightOpacity, 0.0001);
      fragColor = vec4(mix(nightColor, dayColor, dayMix), opacity);
    }
  `;
  const vertexShader = compileShader(gl, gl.VERTEX_SHADER, vertexSource);
  const fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
  const program = gl.createProgram();
  gl.attachShader(program, vertexShader);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);
  gl.deleteShader(vertexShader);
  gl.deleteShader(fragmentShader);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const message = gl.getProgramInfoLog(program) || '昼夜着色器链接失败';
    gl.deleteProgram(program);
    throw new Error(message);
  }
  return {
    program,
    position: gl.getAttribLocation(program, 'a_pos'),
    illumination: gl.getAttribLocation(program, 'a_illumination'),
  };
}

export function createDayNightLayer() {
  const surfaceVertices = buildSurfaceVertices();
  return {
    id: 'dashboard-v2-day-night',
    type: 'custom',
    renderingMode: '2d',
    enabled: true,
    shaderMap: new Map(),
    lastUpdate: 0,

    updateBuffer(gl, date = new Date()) {
      const sunPosition = solarSubpoint(date);
      const data = new Float32Array(surfaceVertices.length * 3);
      surfaceVertices.forEach((vertex, index) => {
        const offset = index * 3;
        data[offset] = vertex.x;
        data[offset + 1] = vertex.y;
        data[offset + 2] = surfaceIllumination(
          vertex.longitude,
          vertex.latitude,
          sunPosition,
        );
      });
      gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
      gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
      this.lastUpdate = date.getTime();
    },

    onAdd(map, gl) {
      this.map = map;
      this.buffer = gl.createBuffer();
      this.updateBuffer(gl);
      this.timer = window.setInterval(() => {
        this.lastUpdate = 0;
        map.triggerRepaint();
      }, UPDATE_INTERVAL_MS);
    },

    getShader(gl, shaderDescription) {
      if (!this.shaderMap.has(shaderDescription.variantName)) {
        this.shaderMap.set(shaderDescription.variantName, createShader(gl, shaderDescription));
      }
      return this.shaderMap.get(shaderDescription.variantName);
    },

    render(gl, args) {
      if (!this.enabled) return;
      if ((Date.now() - this.lastUpdate) >= UPDATE_INTERVAL_MS) this.updateBuffer(gl);
      const shader = this.getShader(gl, args.shaderData);
      gl.useProgram(shader.program);
      gl.uniformMatrix4fv(
        gl.getUniformLocation(shader.program, 'u_projection_fallback_matrix'),
        false,
        args.defaultProjectionData.fallbackMatrix,
      );
      gl.uniformMatrix4fv(
        gl.getUniformLocation(shader.program, 'u_projection_matrix'),
        false,
        args.defaultProjectionData.mainMatrix,
      );
      gl.uniform4f(
        gl.getUniformLocation(shader.program, 'u_projection_tile_mercator_coords'),
        ...args.defaultProjectionData.tileMercatorCoords,
      );
      gl.uniform4f(
        gl.getUniformLocation(shader.program, 'u_projection_clipping_plane'),
        ...args.defaultProjectionData.clippingPlane,
      );
      gl.uniform1f(
        gl.getUniformLocation(shader.program, 'u_projection_transition'),
        args.defaultProjectionData.projectionTransition,
      );
      gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
      gl.enableVertexAttribArray(shader.position);
      gl.vertexAttribPointer(shader.position, 2, gl.FLOAT, false, 12, 0);
      gl.enableVertexAttribArray(shader.illumination);
      gl.vertexAttribPointer(shader.illumination, 1, gl.FLOAT, false, 12, 8);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.drawArrays(gl.TRIANGLES, 0, surfaceVertices.length);
    },

    onRemove(_map, gl) {
      window.clearInterval(this.timer);
      gl.deleteBuffer(this.buffer);
      this.shaderMap.forEach((shader) => gl.deleteProgram(shader.program));
      this.shaderMap.clear();
    },
  };
}

export function initializeDashboardV2DayNight(map) {
  if (!map) return null;
  const layer = createDayNightLayer();
  const addLayer = () => {
    if (!map.getLayer('dashboard-v2-day-night')) map.addLayer(layer);
  };
  if (map.loaded?.()) addLayer();
  else map.once('load', addLayer);
  return {
    layerId: 'dashboard-v2-day-night',
    destroy() {
      map.off?.('load', addLayer);
      if (map.getLayer('dashboard-v2-day-night')) map.removeLayer('dashboard-v2-day-night');
    },
    getEnabled: () => layer.enabled,
    setEnabled(enabled) {
      layer.enabled = Boolean(enabled);
      if (layer.enabled) layer.lastUpdate = 0;
      map.triggerRepaint?.();
      return layer.enabled;
    },
  };
}
