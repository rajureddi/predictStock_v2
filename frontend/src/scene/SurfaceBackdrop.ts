import * as THREE from 'three'

const VERT = /* glsl */`
uniform float uTime;
uniform float uEnergy;
uniform vec2 uPointer;
attribute float aSeed;
varying float vH;
varying float vFade;
varying float vRidge;

float wave(vec2 p, float t) {
  float h = sin(p.x * 0.18 + t * 0.55) * 0.9;
  h += sin(p.x * 0.07 - p.y * 0.22 + t * 0.35) * 1.4;
  h += sin((p.x + p.y) * 0.31 + t * 0.9) * 0.35;
  h += cos(p.y * 0.12 - t * 0.25) * 0.6;
  return h;
}

void main() {
  vec3 pos = position;
  float t = uTime * (1.0 + uEnergy * 1.6);
  float h = wave(pos.xz, t) * (0.8 + uEnergy * 0.5);
  float d = distance(pos.xz, uPointer);
  h += exp(-d * d * 0.01) * 1.2;
  pos.y += h;
  vH = h;
  float ridgeX = sin(t * 0.22) * 34.0;
  vRidge = exp(-pow(pos.x - ridgeX, 2.0) * 0.004) * smoothstep(-1.0, 2.2, h);
  vec4 mv = modelViewMatrix * vec4(pos, 1.0);
  vFade = smoothstep(150.0, 30.0, -mv.z);
  gl_PointSize = (1.6 + aSeed * 1.2) * (90.0 / -mv.z);
  gl_Position = projectionMatrix * mv;
}`

const FRAG = /* glsl */`
uniform vec3 uInk;
uniform vec3 uAccent;
varying float vH;
varying float vFade;
varying float vRidge;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float r = length(c);
  if (r > 0.5) discard;
  float a = smoothstep(0.5, 0.2, r);
  float lift = smoothstep(-2.5, 3.0, vH);
  vec3 col = mix(uInk, uAccent, clamp(vRidge * 1.4, 0.0, 1.0));
  gl_FragColor = vec4(col, a * vFade * (0.18 + 0.55 * lift + vRidge * 0.5));
}`

export class SurfaceBackdrop {
  private renderer: THREE.WebGLRenderer
  private scene = new THREE.Scene()
  private camera = new THREE.PerspectiveCamera(38, 1, 0.1, 400)
  private uniforms = {
    uTime: { value: 0 },
    uEnergy: { value: 0 },
    uPointer: { value: new THREE.Vector2(999, 999) },
    uInk: { value: new THREE.Color('#1A1C21') },
    uAccent: { value: new THREE.Color('#FF5500') },
  }
  private clock = new THREE.Clock()
  private ro: ResizeObserver
  private io: IntersectionObserver
  private visible = true
  private energy = 0
  private targetEnergy = 0
  private pointerTarget = new THREE.Vector2(999, 999)
  private parallax = new THREE.Vector2()
  private reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  private raycaster = new THREE.Raycaster()
  private plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)

  constructor(private host: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.setClearColor(0x000000, 0)
    this.renderer.domElement.setAttribute('aria-hidden', 'true')
    host.appendChild(this.renderer.domElement)

    const cols = 180, rows = 70, sx = 1.15, sz = 1.25
    const n = cols * rows
    const pos = new Float32Array(n * 3)
    const seed = new Float32Array(n)
    let k = 0
    for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
      pos[k * 3] = (i - cols / 2) * sx
      pos[k * 3 + 1] = 0
      pos[k * 3 + 2] = -j * sz + 10
      seed[k] = Math.random()
      k++
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1))
    const m = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, uniforms: this.uniforms, transparent: true, depthWrite: false })
    this.scene.add(new THREE.Points(g, m))

    this.ro = new ResizeObserver(() => this.resize())
    this.ro.observe(host)
    this.io = new IntersectionObserver(([e]) => { this.visible = e.isIntersecting; this.loop() })
    this.io.observe(host)
    window.addEventListener('pointermove', this.onMove, { passive: true })
    document.addEventListener('visibilitychange', this.loop)
    this.resize()
    if (this.reduced) this.uniforms.uTime.value = 12
    this.loop()
  }

  setEnergy(e: number) { this.targetEnergy = e }
  setInk(hex: string) { this.uniforms.uInk.value.set(hex) }

  private onMove = (e: PointerEvent) => {
    const r = this.host.getBoundingClientRect()
    if (e.clientY < r.top || e.clientY > r.bottom) { this.pointerTarget.set(999, 999); return }
    const ndc = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1)
    this.parallax.copy(ndc)
    this.raycaster.setFromCamera(ndc, this.camera)
    const hit = new THREE.Vector3()
    if (this.raycaster.ray.intersectPlane(this.plane, hit)) this.pointerTarget.set(hit.x, hit.z)
  }

  private resize() {
    const w = this.host.clientWidth, h = this.host.clientHeight
    if (!w || !h) return
    this.renderer.setSize(w, h, false)
    this.renderer.domElement.style.width = '100%'
    this.renderer.domElement.style.height = '100%'
    this.camera.aspect = w / h
    this.camera.updateProjectionMatrix()
    this.render()
  }

  private loop = () => {
    const run = this.visible && !document.hidden && !this.reduced
    this.renderer.setAnimationLoop(run ? this.tick : null)
    if (run) this.clock.getDelta()
    else this.render()
  }

  private tick = () => {
    const dt = Math.min(this.clock.getDelta(), 0.05)
    this.uniforms.uTime.value += dt
    this.energy += (this.targetEnergy - this.energy) * (1 - Math.exp(-dt * 1.5))
    this.uniforms.uEnergy.value = this.energy
    const p = this.uniforms.uPointer.value
    if (this.pointerTarget.x > 900) p.lerp(new THREE.Vector2(p.x, -400), 1 - Math.exp(-dt * 0.8))
    else { if (p.y < -300) p.copy(this.pointerTarget); p.lerp(this.pointerTarget, 1 - Math.exp(-dt * 4)) }
    this.render()
  }

  private render() {
    const px = this.reduced ? 0 : this.parallax.x
    this.camera.position.set(px * 3, 14 + this.parallax.y * 1.2, 24)
    this.camera.lookAt(0, 0, -26)
    this.renderer.render(this.scene, this.camera)
  }

  dispose() {
    this.renderer.setAnimationLoop(null)
    this.ro.disconnect(); this.io.disconnect()
    window.removeEventListener('pointermove', this.onMove)
    document.removeEventListener('visibilitychange', this.loop)
    this.scene.traverse(o => {
      const m = o as THREE.Points
      m.geometry?.dispose()
      ;(m.material as THREE.Material | undefined)?.dispose()
    })
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
