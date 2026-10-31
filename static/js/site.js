/* Project Aethrix · page behaviour and the 3D stage (needs three.js r128 loaded first) */
(function(){
"use strict";
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const finePointer = matchMedia('(pointer: fine)').matches;
if (finePointer) document.documentElement.classList.add('fine-pointer');

/* ---------- Mobile menu ---------- */
const menuBtn = document.getElementById('menuBtn'), navPanel = document.getElementById('navPanel');
menuBtn.addEventListener('click', () => {
  const open = navPanel.hidden;
  navPanel.hidden = !open;
  menuBtn.setAttribute('aria-expanded', String(open));
});
navPanel.addEventListener('click', e => { if(e.target.closest('a')){ navPanel.hidden = true; menuBtn.setAttribute('aria-expanded','false'); } });

/* ---------- Founder name: extruded 3D type, light follows the pointer ---------- */
const nameEl = document.getElementById('nameEl');
const EXT_N = 16, cA = [238, 28, 52], cB = [52, 5, 12];
let nameFont = 80;
const measureName = () => { nameFont = parseFloat(getComputedStyle(nameEl).fontSize) || 80; };
measureName(); addEventListener('resize', measureName);
let nAng = .9, nPtr = false, nPtrX = 0, nPtrY = 0, pulse = 0, lastSheen = 0;
const nameT0 = performance.now();
addEventListener('pointermove', e => { nPtr = true; nPtrX = e.clientX; nPtrY = e.clientY; }, {passive: true});
function nameSheen(){ nameEl.classList.remove('sheen'); void nameEl.offsetWidth; nameEl.classList.add('sheen'); }
function setExt(ang, depth){
  const dx = Math.cos(ang), dy = Math.sin(ang), st = depth / EXT_N, out = [];
  for(let k = 1; k <= EXT_N; k++){
    const t = (k - 1) / (EXT_N - 1);
    const c = cA.map((v, j) => Math.round(v + (cB[j] - v) * t));
    out.push((dx * st * k).toFixed(2) + 'px ' + (dy * st * k).toFixed(2) + 'px 0 rgb(' + c.join(',') + ')');
  }
  out.push((dx * (depth + 6)).toFixed(1) + 'px ' + (dy * (depth + 6)).toFixed(1) + 'px 26px rgba(0,0,0,.6)');
  out.push('0 0 ' + (30 + pulse * 34).toFixed(0) + 'px rgba(238,28,52,' + (.22 + pulse * .45).toFixed(2) + ')');
  nameEl.style.setProperty('--ext', out.join(','));
  nameEl.style.setProperty('--ty', (-dx * 9).toFixed(2) + 'deg');
  nameEl.style.setProperty('--tx', (dy * 6).toFixed(2) + 'deg');
}
if(reduce) setExt(.9, nameFont * .15);
else {
  setTimeout(nameSheen, 1500);
  requestAnimationFrame(function nameLoop(now){
    if(scrollY < innerHeight * 1.2){
      const t = (now - nameT0) / 1000;
      const grow = Math.min(1, Math.max(0, (t - .6) / 1.1)), g = 1 - Math.pow(1 - grow, 3);
      let target;
      if(nPtr){ const r = nameEl.getBoundingClientRect(); target = Math.atan2((r.top + r.height / 2) - nPtrY, (r.left + r.width / 2) - nPtrX); }
      else target = .9 + Math.sin(t * .55) * .6;
      let d = target - nAng; d = Math.atan2(Math.sin(d), Math.cos(d)); nAng += d * .07;
      const cyc = t % 6;
      pulse = (cyc > 4.4 && cyc < 5.4) ? Math.sin((cyc - 4.4) * Math.PI) : 0;
      if(cyc > 4.4 && now - lastSheen > 3000){ lastSheen = now; nameSheen(); }
      setExt(nAng, nameFont * .15 * g * (1 + pulse * .55));
    }
    requestAnimationFrame(nameLoop);
  });
}

/* ---------- "We build" word highlight ---------- */
const bws = [...document.querySelectorAll('.bw')];
let bi = 0;
bws[0].classList.add('on');
if(!reduce) setInterval(() => { bws[bi].classList.remove('on'); bi = (bi + 1) % bws.length; bws[bi].classList.add('on'); }, 1500);

/* ---------- Tilt + magnetic buttons ---------- */
function bindTilt(scope){
  if(!finePointer || reduce) return;
  scope.querySelectorAll('.tilt').forEach(el => {
    if(el.dataset.tb) return; el.dataset.tb = '1';
    el.addEventListener('pointermove', e => {
      const r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      el.style.transform = 'perspective(900px) rotateX(' + ((.5 - y) * 9).toFixed(2) + 'deg) rotateY(' + ((x - .5) * 11).toFixed(2) + 'deg) translateZ(0)';
      el.style.setProperty('--gx', (x*100).toFixed(1) + '%'); el.style.setProperty('--gy', (y*100).toFixed(1) + '%');
    });
    el.addEventListener('pointerleave', () => { el.style.transform = ''; });
  });
}
bindTilt(document);
if(finePointer && !reduce){
  document.querySelectorAll('.magnet').forEach(el => {
    el.addEventListener('pointermove', e => {
      const r = el.getBoundingClientRect();
      el.style.transform = 'translate(' + ((e.clientX - r.left - r.width/2) * .22).toFixed(1) + 'px,' + ((e.clientY - r.top - r.height/2) * .32).toFixed(1) + 'px)';
    });
    el.addEventListener('pointerleave', () => { el.style.transform = ''; });
  });
}

/* ---------- Cursor glow ---------- */
const glowEl = document.getElementById('cursorGlow');
let gx = innerWidth/2, gy = innerHeight/2, tx = gx, ty = gy, px = 0, py = 0;
if(finePointer){
  addEventListener('pointermove', e => { tx = e.clientX; ty = e.clientY; px = e.clientX/innerWidth*2-1; py = e.clientY/innerHeight*2-1; }, {passive:true});
}

function copyText(btn, text, selectEl, label){
  const done = () => { btn.textContent = 'Copied'; setTimeout(() => btn.textContent = label, 1600); };
  const fallback = () => { const r = document.createRange(); r.selectNodeContents(selectEl); const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r); btn.textContent = 'Press copy'; setTimeout(() => btn.textContent = label, 2200); };
  try{ navigator.clipboard.writeText(text).then(done, fallback); }catch(err){ fallback(); }
}
const copyMailBtn = document.getElementById('copyMail');
if(copyMailBtn) copyMailBtn.addEventListener('click', function(){ const m = document.getElementById('mail'); copyText(this, m.textContent, m, 'Copy'); });

/* ---------- Scroll → scene index ---------- */
const scenes = [...document.querySelectorAll('[data-scene]')];
const navLinks = [...document.querySelectorAll('[data-nav]')];
const navProgress = document.getElementById('navProgress');
let centers = [], f = 0, activeIdx = -1;
function measure(){
  centers = scenes.map(s => { const r = s.getBoundingClientRect(); return r.top + scrollY + r.height/2; });
  onScroll();
}
function onScroll(){
  if(!centers.length) return;
  const vc = scrollY + innerHeight/2, last = centers.length - 1;
  if(vc <= centers[0]) f = 0;
  else if(vc >= centers[last]) f = last;
  else for(let i = 0; i < last; i++){ if(vc < centers[i+1]){ f = i + (vc - centers[i]) / (centers[i+1] - centers[i]); break; } }
  const max = document.documentElement.scrollHeight - innerHeight;
  navProgress.style.transform = 'scaleX(' + (max > 0 ? Math.min(1, scrollY / max) : 0).toFixed(4) + ')';
  const idx = Math.round(f);
  if(idx !== activeIdx){
    activeIdx = idx;
    navLinks.forEach(a => a.classList.toggle('on', Number(a.dataset.nav) === idx));
    document.getElementById('hudIdx').textContent = String(idx + 1).padStart(2, '0');
    document.getElementById('hudName').textContent = SHAPE_NAMES[idx];
  }
}
const SHAPE_NAMES = ['Cube unit','Torus knot','Galaxy','Aethrix A','Helix','Grid'];
addEventListener('scroll', onScroll, {passive:true});
addEventListener('resize', measure);
addEventListener('load', measure);
if(document.fonts && document.fonts.ready) document.fonts.ready.then(measure);
measure();

/* ---------- WebGL stage: robot core in the hero, particle forms below ---------- */
function hasGL(){ try{ const c = document.createElement('canvas'); return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl'))); }catch(e){ return false; } }
let renderer = null;
if(window.THREE && hasGL()){
  try{ renderer = new THREE.WebGLRenderer({canvas: document.getElementById('stage'), antialias: true, alpha: true, powerPreference: 'high-performance'}); }catch(e){ renderer = null; }
}
if(!renderer){ document.documentElement.classList.add('no-webgl'); glowLoop(); return; }

renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.75));
renderer.setClearColor(0x000000, 0);
renderer.outputEncoding = THREE.sRGBEncoding;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
camera.position.set(0, 0, 7);
const lin = h => new THREE.Color(h).convertSRGBToLinear();

/* Studio reflections for the metal: soft white and red light panels baked into an environment map */
const pmrem = new THREE.PMREMGenerator(renderer);
const envScene = new THREE.Scene();
envScene.add(new THREE.Mesh(new THREE.SphereGeometry(20, 32, 16), new THREE.MeshBasicMaterial({color: lin('#0a0405'), side: THREE.BackSide})));
function softbox(w, h, c, x, y, z){ const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({color: c, side: THREE.DoubleSide})); m.position.set(x, y, z); m.lookAt(0, 0, 0); envScene.add(m); }
softbox(10, 3, new THREE.Color(6, 6, 6), -6, 8, 6);
softbox(3, 12, new THREE.Color(6, .35, .5), 9, 0, -4);
softbox(12, 1.2, new THREE.Color(3, 3, 3.2), 0, -6, 8);
softbox(2, 8, new THREE.Color(4, .7, .4), -9, -1, -6);
scene.environment = pmrem.fromScene(envScene, .035).texture;

/* ---------- Particle forms (dust shell, knot, galaxy, helix, grid) ---------- */
const small = innerWidth < 760;
const N = small ? 2800 : 5600;
document.getElementById('hudPts').textContent = N.toLocaleString('en-US');

function genShapes(){
  const sph = new Float32Array(N*3), knot = new Float32Array(N*3), gal = new Float32Array(N*3), aGl = new Float32Array(N*3), hel = new Float32Array(N*3), cub = new Float32Array(N*3);
  const AP = [[0, 1.4], [1.2, -1.3], [.67, -1.3], [0, -.05], [-.67, -1.3], [-1.2, -1.3]];
  const inPoly = (x, y) => { let c = false; for(let a = 0, b = AP.length - 1; a < AP.length; b = a++){ const [xi, yi] = AP[a], [xj, yj] = AP[b]; if(((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) c = !c; } return c; };
  const J = a => (Math.random() - .5) * a;
  const set = (arr, i, x, y, z) => { arr[i*3] = x; arr[i*3+1] = y; arr[i*3+2] = z; };
  const tilt = 1.08, ct = Math.cos(tilt), st = Math.sin(tilt);
  for(let i = 0; i < N; i++){
    const vs = .26;
    set(sph, i, Math.round(J(6.4)/vs)*vs, Math.round(J(4.4)/vs)*vs, Math.round(J(3.2)/vs)*vs - .6);
    const t = Math.random() * Math.PI * 2, R = (2 + Math.cos(3*t)) * .5;
    set(knot, i, R*Math.cos(2*t) + J(.32), R*Math.sin(2*t) + J(.32), -Math.sin(3*t)*.62 + J(.32));
    const arm = i % 3, rr = Math.pow(Math.random(), .55) * 2.7;
    const a = arm * 2.0944 + rr * 1.75 + J(.55 * (1.25 - rr/2.7));
    const gx = Math.cos(a)*rr, gz = Math.sin(a)*rr, gy = J(.22 * (1 - rr/3));
    set(gal, i, gx, gy*ct - gz*st, gy*st + gz*ct);
    if(Math.random() < .45){
      const e = Math.floor(Math.random() * 6), u = Math.random(), A0 = AP[e], A1 = AP[(e + 1) % 6];
      set(aGl, i, A0[0] + (A1[0] - A0[0]) * u, A0[1] + (A1[1] - A0[1]) * u, (Math.random() < .5 ? -1 : 1) * .22 + J(.02));
    } else {
      let ax, ay;
      do { ax = Math.random() * 2.4 - 1.2; ay = Math.random() * 2.7 - 1.3; } while(!inPoly(ax, ay));
      set(aGl, i, ax, ay, J(.44));
    }
    if(Math.random() < .76){
      const u = Math.random(), ang = u * Math.PI * 5 + (i % 2) * Math.PI;
      set(hel, i, Math.cos(ang)*.9 + J(.08), (u - .5)*4 + J(.05), Math.sin(ang)*.9 + J(.08));
    } else {
      const k = Math.floor(Math.random()*28), u = (k + .5)/28, ang = u * Math.PI * 5, m = Math.random();
      set(hel, i, Math.cos(ang)*.9*(1 - 2*m), (u - .5)*4, Math.sin(ang)*.9*(1 - 2*m));
    }
    const g = 6, s = 1.2;
    let p = Math.random()*2 - 1, q = Math.round(Math.random()*g)/g*2 - 1;
    if(Math.random() < .5){ const tmp = p; p = q; q = tmp; }
    const face = Math.floor(Math.random()*6);
    const pts = [[s,p*s,q*s],[-s,p*s,q*s],[p*s,s,q*s],[p*s,-s,q*s],[p*s,q*s,s],[p*s,q*s,-s]][face];
    set(cub, i, pts[0] + J(.02), pts[1] + J(.02), pts[2] + J(.02));
  }
  return [sph, knot, gal, aGl, hel, cub];
}
const SHAPES = genShapes();
const geo = new THREE.BufferGeometry();
const posArr = new Float32Array(SHAPES[0]);
geo.setAttribute('position', new THREE.BufferAttribute(posArr, 3));
const rnd = new Float32Array(N*3);
for(let i = 0; i < N*3; i++) rnd[i] = Math.random();
geo.setAttribute('aRnd', new THREE.BufferAttribute(rnd, 3));
const pMat = new THREE.ShaderMaterial({
  uniforms: {
    uTime: {value: 0}, uTurb: {value: 0}, uSize: {value: small ? 2.6 : 2.3}, uPR: {value: renderer.getPixelRatio()}, uOpacity: {value: 1},
    uC1: {value: new THREE.Color('#ee1c34')}, uC2: {value: new THREE.Color('#ff7a45')}, uC3: {value: new THREE.Color('#ffe9e4')}
  },
  vertexShader: `
    attribute vec3 aRnd;
    uniform float uTime, uTurb, uSize, uPR;
    uniform vec3 uC1, uC2, uC3;
    varying vec3 vCol; varying float vA;
    void main(){
      vec3 p = position;
      p += (aRnd - 0.5) * uTurb * 1.8;
      p += 0.03 * vec3(sin(uTime*1.3 + aRnd.x*40.0), cos(uTime*1.1 + aRnd.y*40.0), sin(uTime*0.9 + aRnd.z*40.0));
      vec4 mv = modelViewMatrix * vec4(p, 1.0);
      gl_Position = projectionMatrix * mv;
      float spark = step(0.965, aRnd.z);
      gl_PointSize = uSize * uPR * (0.55 + aRnd.x * 0.9 + spark * 1.6) * (7.0 / -mv.z);
      vCol = mix(uC1, uC2, aRnd.y * aRnd.y);
      vCol = mix(vCol, uC3, spark * 0.85);
      vA = clamp(1.25 - (-mv.z - 5.0) * 0.22, 0.25, 1.0);
    }`,
  fragmentShader: `
    uniform float uOpacity;
    varying vec3 vCol; varying float vA;
    void main(){
      float r = length(gl_PointCoord - 0.5);
      float a = pow(smoothstep(0.5, 0.0, r), 1.7);
      gl_FragColor = vec4(vCol, a * vA * uOpacity);
    }`,
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
});
const points = new THREE.Points(geo, pMat);
const root = new THREE.Group();
root.add(points);
scene.add(root);

const gc = document.createElement('canvas'); gc.width = gc.height = 256;
const gctx = gc.getContext('2d'), grad = gctx.createRadialGradient(128,128,0,128,128,128);
grad.addColorStop(0, 'rgba(255,255,255,.55)'); grad.addColorStop(.35, 'rgba(255,255,255,.12)'); grad.addColorStop(1, 'rgba(255,255,255,0)');
gctx.fillStyle = grad; gctx.fillRect(0, 0, 256, 256);
const glowTex = new THREE.CanvasTexture(gc);
const glowMat = new THREE.SpriteMaterial({map: glowTex, color: lin('#ee1c34'), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: .5, toneMapped: false});
const glowSprite = new THREE.Sprite(glowMat);
glowSprite.scale.set(6.5, 6.5, 1); glowSprite.position.z = -1.6;
root.add(glowSprite);

/* ---------- Robot core: an angular cube unit, no round parts ---------- */
const metal = new THREE.MeshStandardMaterial({color: lin('#2b2628'), metalness: .93, roughness: .26, envMapIntensity: 1.3});
const plateMat = new THREE.MeshStandardMaterial({color: lin('#3b3436'), metalness: .95, roughness: .16, envMapIntensity: 1.6});
const redGlow = new THREE.MeshStandardMaterial({color: lin('#2a0408'), emissive: lin('#ff1f3a'), emissiveIntensity: 2.4, metalness: .2, roughness: .4});
const redLight = new THREE.MeshBasicMaterial({color: lin('#ff2a40'), toneMapped: false});
const seamMat = new THREE.LineBasicMaterial({color: lin('#ff2a40'), transparent: true, opacity: .8, toneMapped: false});

const robot = new THREE.Group();
robot.rotation.set(.48, -.68, 0);   // three-quarter view so three faces catch the light
root.add(robot);
const body = new THREE.Group();
robot.add(body);

// reactor heart: octahedron with a counter-rotating cage
const reactorMat = new THREE.MeshStandardMaterial({color: lin('#300408'), emissive: lin('#ff2a3d'), emissiveIntensity: 1.4, flatShading: true, metalness: .3, roughness: .5});
const reactor = new THREE.Mesh(new THREE.OctahedronGeometry(.34, 0), reactorMat);
body.add(reactor);
const reactorWire = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(.5, .5, .5)), new THREE.LineBasicMaterial({color: lin('#ffb4a2'), transparent: true, opacity: .6, toneMapped: false}));
body.add(reactorWire);
const coreLight = new THREE.PointLight(lin('#ff2a3d'), 1.5, 5, 2);
body.add(coreLight);

// 2x2x2 armoured blocks that turn like a puzzle and split open
const H = .34, C = .6;
const cubeGeo = new THREE.BoxGeometry(C, C, C);
const cubeEdges = new THREE.EdgesGeometry(cubeGeo);
const plateGeo = new THREE.BoxGeometry(C * .64, C * .64, .02);
const ventGeo = new THREE.BoxGeometry(C * .44, .034, .012);
const shell = new THREE.Group(); body.add(shell);
const pivot = new THREE.Group(); shell.add(pivot);
const cubies = [];
[-1, 1].forEach(x => [-1, 1].forEach(y => [-1, 1].forEach(z => {
  const g = new THREE.Group();
  g.add(new THREE.Mesh(cubeGeo, metal));
  g.add(new THREE.LineSegments(cubeEdges, seamMat));
  [[x, 0, 0], [0, y, 0], [0, 0, z]].forEach((n, idx) => {
    const plate = new THREE.Mesh(plateGeo, plateMat);
    plate.position.set(n[0] * (C/2 + .01), n[1] * (C/2 + .01), n[2] * (C/2 + .01));
    if(n[0]) plate.rotation.y = Math.PI / 2;
    if(n[1]) plate.rotation.x = Math.PI / 2;
    g.add(plate);
    if((x + y + z + 3 + idx) % 2 === 0){
      const vent = new THREE.Mesh(ventGeo, redLight);
      vent.position.set(n[0] * (C/2 + .024), n[1] * (C/2 + .024), n[2] * (C/2 + .024));
      if(n[0]){ vent.rotation.y = Math.PI / 2; vent.position.y -= C * .17; }
      else if(n[1]){ vent.rotation.x = Math.PI / 2; vent.position.z -= C * .17; }
      else vent.position.y -= C * .17;
      g.add(vent);
    }
  });
  g.userData.L = new THREE.Vector3(x, y, z);
  g.position.set(x * H, y * H, z * H);
  shell.add(g); cubies.push(g);
})));

// laser beams that fire through the gaps when the blocks split
const beamMat = new THREE.MeshBasicMaterial({color: lin('#ff3048'), transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false});
const beams = [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]].map(d => {
  const m = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), beamMat);
  m.userData.d = new THREE.Vector3(d[0], d[1], d[2]);
  body.add(m); return m;
});

// square scan frame
const sq = s => [new THREE.Vector3(-s, 0, -s), new THREE.Vector3(s, 0, -s), new THREE.Vector3(s, 0, s), new THREE.Vector3(-s, 0, s)];
const scanMat = new THREE.LineBasicMaterial({color: lin('#ff3b4e'), transparent: true, opacity: 0, toneMapped: false});
const scan = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(sq(.95)), scanMat);
body.add(scan);

// targeting brackets on the eight corners
const brackets = [];
[-1, 1].forEach(x => [-1, 1].forEach(y => [-1, 1].forEach(z => {
  const br = new THREE.Group();
  [[.2, .022, .022, -x * .09, 0, 0], [.022, .2, .022, 0, -y * .09, 0], [.022, .022, .2, 0, 0, -z * .09]].forEach(a => {
    const arm = new THREE.Mesh(new THREE.BoxGeometry(a[0], a[1], a[2]), redLight);
    arm.position.set(a[3], a[4], a[5]); br.add(arm);
  });
  br.userData.s = new THREE.Vector3(x, y, z);
  body.add(br); brackets.push(br);
})));

// square gyro frame with red corner blocks
const frameA = new THREE.Group(); frameA.rotation.x = Math.PI / 2 - .25; robot.add(frameA);
const frameASpin = new THREE.Group(); frameA.add(frameASpin);
const FS = 1.25;
[[0, FS, 2*FS, .045], [0, -FS, 2*FS, .045], [FS, 0, .045, 2*FS], [-FS, 0, .045, 2*FS]].forEach(b => {
  const beam = new THREE.Mesh(new THREE.BoxGeometry(b[2], b[3], .045), metal);
  beam.position.set(b[0], b[1], 0); frameASpin.add(beam);
});
[[1,1],[1,-1],[-1,1],[-1,-1]].forEach(c => {
  const blk = new THREE.Mesh(new THREE.BoxGeometry(.12, .12, .12), redGlow);
  blk.position.set(c[0] * FS, c[1] * FS, 0); frameASpin.add(blk);
});
// triangle light frame
const tri = [0, 1, 2].map(i => { const a = Math.PI / 2 + i * Math.PI * 2 / 3; return new THREE.Vector3(Math.cos(a) * 1.72, Math.sin(a) * 1.72, 0); });
const triMat = new THREE.LineBasicMaterial({color: lin('#ff2a40'), transparent: true, opacity: .75, toneMapped: false});
const triangle = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(tri), triMat);
const triG = new THREE.Group(); triG.rotation.set(.25, .5, 0); triG.add(triangle); robot.add(triG);

// two scout drones patrolling a square path
const droneGeo = new THREE.TetrahedronGeometry(.1, 0);
const path = sq(1.55);
const drones = [0, 1].map(i => {
  const d = new THREE.Group();
  d.add(new THREE.Mesh(droneGeo, metal));
  d.add(new THREE.LineSegments(new THREE.EdgesGeometry(droneGeo), seamMat));
  robot.add(d); return d;
});

// lighting
scene.add(new THREE.AmbientLight(lin('#3a1a1c'), .5));
scene.add(new THREE.HemisphereLight(lin('#ffffff'), lin('#2a0508'), .35));
const keyL = new THREE.DirectionalLight(lin('#fff1ec'), 1.9); keyL.position.set(-4, 5, 6); scene.add(keyL);
const rimL = new THREE.DirectionalLight(lin('#ff2a3d'), 3.4); rimL.position.set(5, 1.5, -4); scene.add(rimL);
const rimL2 = new THREE.DirectionalLight(lin('#ff6a3a'), 1.2); rimL2.position.set(-5, -3, -2); scene.add(rimL2);
const sweepL = new THREE.PointLight(lin('#ff3b30'), 3, 6, 2); robot.add(sweepL);

/* ---------- Motion helpers ---------- */
const clamp01 = x => Math.max(0, Math.min(1, x));
const easeOutBack = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const easeInOut = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
function servo(tt, period, move, step){ const n = Math.floor(tt / period), r = clamp01((tt - n * period) / move); return (n + easeOutBack(r)) * step; }
const CYCLE = 7;
const TURNS = [0, .75, 1.5, 5.4, 6.15];
function openAmt(p){
  if(p < 2.5) return 0;
  if(p < 3.0) return easeOutBack((p - 2.5) / .5);
  if(p < 4.5) return 1;
  if(p < 4.9){ const x = (p - 4.5) / .4; return 1 - x * x * x; }
  return 0;
}
const crossed = (a, b, t) => b >= a ? (a < t && t <= b) : (t > a || t <= b);

let turn = null;
function startTurn(now){
  if(turn) finishTurn();
  const axis = ['x', 'y', 'z'][Math.floor(Math.random() * 3)], side = Math.random() < .5 ? -1 : 1, dir = Math.random() < .5 ? -1 : 1;
  robot.updateMatrixWorld(true);
  pivot.rotation.set(0, 0, 0); pivot.updateMatrixWorld(true);
  const members = cubies.filter(c => c.userData.L[axis] === side);
  members.forEach(c => pivot.attach(c));
  turn = {axis, dir, members, t0: now};
}
function finishTurn(){
  pivot.rotation.set(0, 0, 0);
  pivot.rotation[turn.axis] = turn.dir * Math.PI / 2;
  robot.updateMatrixWorld(true);
  const q = Math.PI / 2;
  turn.members.forEach(c => {
    shell.attach(c);
    c.userData.L.set(Math.round(c.position.x / H), Math.round(c.position.y / H), Math.round(c.position.z / H));
    c.position.copy(c.userData.L).multiplyScalar(H);
    c.rotation.set(Math.round(c.rotation.x / q) * q, Math.round(c.rotation.y / q) * q, Math.round(c.rotation.z / q) * q);
  });
  pivot.rotation.set(0, 0, 0);
  turn = null;
  shakeAmt = Math.max(shakeAmt, .35);
}

/* Per-section placement. my/ms/mo are the phone-width y, scale and opacity. */
const K = [
  {x: 1.85, y: .05, s: 1.0,  o: .5,   spin: .1,  my: 1.2, ms: .56, mo: .45},
  {x: 2.45, y: .75, s: .72,  o: .55,  spin: .22, my: .4,  ms: .8,  mo: .32},
  {x: 0,    y: 0,   s: 1.55, o: .28,  spin: .06, my: 0,   ms: 1.1, mo: .25},
  {x: 2.05, y: .05, s: 1.0,  o: .75,  spin: .12, my: .3,  ms: .8,  mo: .3},
  {x: 1.95, y: 0,   s: .95,  o: .9,   spin: .3,  my: .3,  ms: .8,  mo: .35},
  {x: -2.15,y: 0,   s: .95,  o: .85,  spin: .2,  my: .2,  ms: .8,  mo: .3}
];
let narrow = false, xScale = 1;
function resize(){
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h; camera.updateProjectionMatrix();
  narrow = w < 760 || camera.aspect < .85;
  xScale = Math.max(.55, Math.min(1.15, camera.aspect / 1.6));
}
addEventListener('resize', resize);
resize();

const hold = t => { const u = Math.min(1, Math.max(0, (t - .2) / .6)); return u*u*(3 - 2*u); };
function target(ff){
  const i = Math.floor(ff), j = Math.min(i + 1, K.length - 1), t = hold(ff - i), a = K[i], b = K[j], o = {};
  for(const k in a) o[k] = a[k] + (b[k] - a[k]) * t;
  if(narrow){ o.x = 0; o.y = o.my; o.s = o.ms; o.o = o.mo; } else o.x *= xScale;
  return o;
}
const cur = Object.assign({}, target(0), {s: .2, f: 0});

let pointerSeen = false;
if(finePointer) addEventListener('pointermove', () => { pointerSeen = true; }, {passive: true, once: true});

let last = performance.now(), time = 0, li = -1, lj = -1, lt = -1, prevScroll = scrollY;
let cycleStart = -.8, prevCyc = 0, shakeAmt = 0, nextLook = 0, autoYaw = 0, autoPitch = 0;
const hv = {y: 0, x: 0};

/* Tap or click the hero to make the unit split open on demand */
addEventListener('pointerdown', e => {
  if(reduce || e.button > 0) return;
  if(e.target.closest('a,button,input,textarea,select,label,.modal,.nav')) return;
  if(scrollY > innerHeight * .7) return;
  const ph = ((time - cycleStart) % CYCLE + CYCLE) % CYCLE;
  if(ph < 2.4 || ph > 5.0){
    if(turn) finishTurn();
    cycleStart = time - 2.5; prevCyc = 2.5;
  }
}, {passive: true});

function frame(now){
  const dt = Math.max(0, Math.min((now - last) / 1000, .05)); last = now;
  const motion = reduce ? 0 : 1;
  time += dt * motion;
  const k = 1 - Math.exp(-dt * (reduce ? 14 : 3));

  cur.f += (f - cur.f) * (1 - Math.exp(-dt * (reduce ? 14 : 2.6)));
  const tg = target(cur.f);
  for(const key in tg) cur[key] += (tg[key] - cur[key]) * k;

  // particle morph
  const i = Math.floor(cur.f), j = Math.min(i + 1, SHAPES.length - 1), t = hold(cur.f - i);
  if(i !== li || j !== lj || Math.abs(t - lt) > 1e-4){
    const A = SHAPES[i], B = SHAPES[j];
    for(let n = 0; n < posArr.length; n++) posArr[n] = A[n] + (B[n] - A[n]) * t;
    geo.attributes.position.needsUpdate = true;
    li = i; lj = j; lt = t;
  }
  pMat.uniforms.uTurb.value = Math.sin(Math.PI * t) * .9;
  pMat.uniforms.uTime.value = time;
  pMat.uniforms.uOpacity.value = cur.o;

  const vel = scrollY - prevScroll; prevScroll = scrollY;
  root.position.set(cur.x, cur.y, 0);
  root.scale.setScalar(cur.s);
  points.rotation.y += dt * cur.spin * motion + Math.max(-.06, Math.min(.06, vel * .0012)) * motion;
  points.rotation.x = Math.sin(time * .25) * .18 + py * .25;
  points.rotation.z = px * .12;

  // robot: full size in the hero, folds away as you scroll on
  const w = clamp01(1 - cur.f * 1.35), we = w * w * (3 - 2 * w);
  robot.visible = we > .01;
  let open = 0;
  if(robot.visible){
    robot.scale.setScalar(.78 * we);
    const ph = ((time - cycleStart) % CYCLE + CYCLE) % CYCLE;
    if(!reduce){
      TURNS.forEach(tt => { if(crossed(prevCyc, ph, tt)) startTurn(time); });
      if(crossed(prevCyc, ph, 4.9)) shakeAmt = 1;
    }
    prevCyc = ph;
    open = openAmt(ph);
    shakeAmt *= Math.exp(-dt * 7);

    if(turn){
      const p = clamp01((time - turn.t0) / .45);
      pivot.rotation.set(0, 0, 0);
      pivot.rotation[turn.axis] = turn.dir * Math.PI / 2 * easeOutBack(p);
      if(p >= 1) finishTurn();
    }
    if(!turn) cubies.forEach(c => c.position.copy(c.userData.L).multiplyScalar(H + open * .3));

    reactor.scale.setScalar(.75 + open * .55);
    reactor.rotation.x += dt * (.5 + open * 3) * motion;
    reactor.rotation.y += dt * (.7 + open * 4) * motion;
    reactorWire.scale.setScalar(.9 + open * .5);
    reactorWire.rotation.y -= dt * (.4 + open * 2.5) * motion;
    reactorWire.rotation.z += dt * .3 * motion;
    reactorMat.emissiveIntensity = 1.3 + open * 3.5 + Math.sin(time * 6) * .15 * motion;
    coreLight.intensity = 1.4 + open * 7;

    const flick = .75 + .25 * Math.sin(time * 40) * motion;
    beams.forEach(m => {
      const len = .05 + open * 2.1;
      m.scale.set(m.userData.d.x ? len : .02, m.userData.d.y ? len : .02, m.userData.d.z ? len : .02);
      m.position.copy(m.userData.d).multiplyScalar(.2 + len / 2);
    });
    beamMat.opacity = open * .85 * flick;

    if(ph > 3.0 && ph < 4.5){
      const s = (ph - 3.0) / 1.5;
      scan.position.y = Math.cos(s * Math.PI * 2) * .95;
      scanMat.opacity = Math.sin(s * Math.PI);
    } else scanMat.opacity = 0;

    const bk = .98 + open * .45 + Math.sin(time * 3) * .02 * motion;
    brackets.forEach(br => br.position.copy(br.userData.s).multiplyScalar(bk));

    // body: servo-style look, stepping toward the cursor or scanning on its own
    let tyaw, tpitch;
    if(pointerSeen){ tyaw = px * .5; tpitch = py * .3; }
    else {
      if(time >= nextLook){ autoYaw = (Math.random() - .5) * .7; autoPitch = (Math.random() - .5) * .35; nextLook = time + .9 + Math.random() * .9; }
      tyaw = autoYaw; tpitch = autoPitch;
    }
    tyaw = Math.round(tyaw / .13) * .13; tpitch = Math.round(tpitch / .11) * .11;
    hv.y += ((tyaw - body.rotation.y) * 70 - hv.y * 11) * dt; body.rotation.y += hv.y * dt;
    hv.x += ((tpitch - body.rotation.x) * 70 - hv.x * 11) * dt; body.rotation.x += hv.x * dt;

    frameASpin.rotation.z = servo(time, 1.6, .5, Math.PI / 4);
    triangle.rotation.z = -servo(time + .8, 2.2, .6, Math.PI * 2 / 3);
    drones.forEach((d, n) => {
      const tt = time + n * 2.6, step = Math.floor(tt / 1.3), r = easeInOut(clamp01((tt - step * 1.3) / .5));
      const a0 = path[(((step + n * 2) % 4) + 4) % 4], a1 = path[(((step + n * 2 + 1) % 4) + 4) % 4];
      d.position.lerpVectors(a0, a1, r);
      d.position.y = n ? .35 : -.35;
      d.rotation.y += dt * 2.4 * motion; d.rotation.x += dt * 1.3 * motion;
    });
    sweepL.position.set(Math.cos(time * 1.1) * 2.6, 1.1, Math.sin(time * 1.1) * 2.6);

    const sh = shakeAmt * .05;
    robot.position.set((Math.random() - .5) * sh, Math.sin(time * 1.2) * .04 + (Math.random() - .5) * sh, 0);
  }
  glowMat.opacity = ((.16 + .2 * w) + open * .3 * we) * Math.max(cur.o, .6 * we);

  camera.position.x += (px * .3 - camera.position.x) * k;
  camera.position.y += (-py * .2 - camera.position.y) * k;
  camera.lookAt(0, 0, 0);

  renderer.render(scene, camera);
  moveGlow();
  requestAnimationFrame(frame);
}
function moveGlow(){
  if(!finePointer) return;
  gx += (tx - gx) * .12; gy += (ty - gy) * .12;
  glowEl.style.transform = 'translate3d(' + gx.toFixed(1) + 'px,' + gy.toFixed(1) + 'px,0)';
}
function glowLoop(){ moveGlow(); requestAnimationFrame(glowLoop); }
requestAnimationFrame(frame);
})();
