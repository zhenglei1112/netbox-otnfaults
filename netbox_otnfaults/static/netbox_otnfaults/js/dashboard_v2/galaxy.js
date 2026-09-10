import {
  celestialFieldOfView,
  createCelestialView,
  greenwichMeanSiderealDegrees,
} from './starfield.js?v=20260910-presentation-v1';

const DEG_TO_RAD = Math.PI / 180;
const GALAXY_TEXTURE_URL = new URL('../../img/dashboard-v2-milky-way-8k.jpg', import.meta.url);

const VERTEX_SHADER = `
  attribute vec2 a_position;
  void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
  }
`;

const FRAGMENT_SHADER = `
  precision highp float;
  uniform sampler2D u_texture;
  uniform vec2 u_resolution;
  uniform vec3 u_forward;
  uniform vec3 u_right;
  uniform vec3 u_up;
  uniform float u_focal_length;
  uniform float u_sidereal_angle;
  const float PI = 3.141592653589793;

  void main() {
    vec2 offset = gl_FragCoord.xy - (u_resolution * 0.5);
    vec3 earth = normalize(
      u_forward
      + (u_right * offset.x / u_focal_length)
      + (u_up * offset.y / u_focal_length)
    );
    float cosine = cos(u_sidereal_angle);
    float sine = sin(u_sidereal_angle);
    vec3 equatorial = vec3(
      (earth.x * cosine) - (earth.y * sine),
      (earth.x * sine) + (earth.y * cosine),
      earth.z
    );
    vec3 galactic = vec3(
      dot(vec3(-0.0548755604, -0.8734370902, -0.4838350155), equatorial),
      dot(vec3(0.4941094279, -0.4448296300, 0.7469822445), equatorial),
      dot(vec3(-0.8676661490, -0.1980763734, 0.4559837762), equatorial)
    );
    float longitude = atan(galactic.y, galactic.x);
    float latitude = asin(clamp(galactic.z, -1.0, 1.0));
    vec2 textureCoordinate = vec2(
      fract((longitude / (2.0 * PI)) + 0.5),
      0.5 - (latitude / PI)
    );
    vec3 source = texture2D(u_texture, textureCoordinate).rgb;
    vec3 lifted = max(source - vec3(0.0025), vec3(0.0));
    lifted = pow(lifted * 2.75, vec3(0.72));
    float luminance = dot(lifted, vec3(0.2126, 0.7152, 0.0722));
    vec3 cool = lifted * vec3(0.82, 0.98, 1.18);
    vec3 warm = lifted * vec3(1.42, 0.88, 0.62);
    vec3 galaxy = mix(cool, warm, smoothstep(0.08, 0.48, luminance));
    vec3 space = vec3(0.002, 0.006, 0.014);
    gl_FragColor = vec4(space + (galaxy * 0.41), 1.0);
  }
`;

function compileShader(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader) || '未知着色器错误';
    gl.deleteShader(shader);
    throw new Error(message);
  }
  return shader;
}

function createProgram(gl) {
  const vertexShader = compileShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
  const fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
  const program = gl.createProgram();
  gl.attachShader(program, vertexShader);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);
  gl.deleteShader(vertexShader);
  gl.deleteShader(fragmentShader);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const message = gl.getProgramInfoLog(program) || '未知着色器链接错误';
    gl.deleteProgram(program);
    throw new Error(message);
  }
  return program;
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('银河纹理加载失败'));
    image.src = url.href;
  });
}

export function galacticTextureCoordinates(vector) {
  const longitude = Math.atan2(vector[1], vector[0]);
  const latitude = Math.asin(Math.min(1, Math.max(-1, vector[2])));
  return {
    u: ((longitude / (2 * Math.PI)) + 1.5) % 1,
    v: 0.5 - (latitude / Math.PI),
  };
}

export async function initializeDashboardV2Galaxy(map) {
  const canvas = document.getElementById('dashboard-v2-galaxy');
  if (!canvas || !map) return null;
  const gl = canvas.getContext('webgl', {
    alpha: false,
    antialias: false,
    depth: false,
    stencil: false,
    preserveDrawingBuffer: false,
  });
  if (!gl) throw new Error('浏览器不支持银河 WebGL 渲染');

  const image = await loadImage(GALAXY_TEXTURE_URL);
  const program = createProgram(gl);
  const positionBuffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
    -1, -1, 1, -1, -1, 1,
    -1, 1, 1, -1, 1, 1,
  ]), gl.STATIC_DRAW);
  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, image);

  const locations = {
    position: gl.getAttribLocation(program, 'a_position'),
    resolution: gl.getUniformLocation(program, 'u_resolution'),
    forward: gl.getUniformLocation(program, 'u_forward'),
    right: gl.getUniformLocation(program, 'u_right'),
    up: gl.getUniformLocation(program, 'u_up'),
    focalLength: gl.getUniformLocation(program, 'u_focal_length'),
    siderealAngle: gl.getUniformLocation(program, 'u_sidereal_angle'),
    texture: gl.getUniformLocation(program, 'u_texture'),
  };
  let animationFrame = 0;
  let visible = true;

  const render = () => {
    animationFrame = 0;
    const bounds = canvas.getBoundingClientRect();
    const pixelRatio = Math.min(Math.max(window.devicePixelRatio || 1, 1), 2);
    const width = Math.max(1, Math.round(bounds.width * pixelRatio));
    const height = Math.max(1, Math.round(bounds.height * pixelRatio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    const fieldOfView = celestialFieldOfView(map) * DEG_TO_RAD;
    const focalLength = (Math.min(width, height) * 0.5) / Math.tan(fieldOfView * 0.5);
    const view = createCelestialView(map.getCenter?.() ?? [103, 34.3], map.getBearing?.() ?? 0);
    gl.viewport(0, 0, width, height);
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.enableVertexAttribArray(locations.position);
    gl.vertexAttribPointer(locations.position, 2, gl.FLOAT, false, 0, 0);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.uniform1i(locations.texture, 0);
    gl.uniform2f(locations.resolution, width, height);
    gl.uniform3fv(locations.forward, view.forward);
    gl.uniform3fv(locations.right, view.right);
    gl.uniform3fv(locations.up, view.up);
    gl.uniform1f(locations.focalLength, focalLength);
    gl.uniform1f(locations.siderealAngle, greenwichMeanSiderealDegrees(new Date()) * DEG_TO_RAD);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
  };
  const scheduleRender = () => {
    if (animationFrame) return;
    animationFrame = requestAnimationFrame(render);
  };

  map.on('move', scheduleRender);
  map.on('resize', scheduleRender);
  const resizeObserver = typeof ResizeObserver === 'function'
    ? new ResizeObserver(scheduleRender)
    : null;
  resizeObserver?.observe(canvas);
  const clockTimer = window.setInterval(scheduleRender, 60000);
  scheduleRender();

  return {
    render: scheduleRender,
    setVisible(nextVisible) {
      visible = Boolean(nextVisible);
      canvas.hidden = !visible;
      if (visible) scheduleRender();
    },
    destroy() {
      map.off('move', scheduleRender);
      map.off('resize', scheduleRender);
      resizeObserver?.disconnect();
      window.clearInterval(clockTimer);
      if (animationFrame) cancelAnimationFrame(animationFrame);
      gl.deleteTexture(texture);
      gl.deleteBuffer(positionBuffer);
      gl.deleteProgram(program);
    },
  };
}
