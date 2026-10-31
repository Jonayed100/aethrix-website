/* Project Aethrix · 3D scenes for the dashboards and sign-in pages.
   Needs three.js r128 loaded first. Each <canvas data-3d="..."> starts itself:
     data-3d="bars"   founder: 3D bookings-per-month columns (data-source = json_script id, data-overlay = labels div)
     data-3d="blocks" client: the project being built block by block (data-progress = 0..100)
     data-3d="gate"   sign-in pages: armoured cube lattice (data-mode="founder" for the founder login)
   Without WebGL the page gets class "no-gl" and shows its plain fallback. */
(function(){
  'use strict';
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const clamp01 = x => Math.max(0, Math.min(1, x));
  const easeOutBack = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  const easeOutCubic = x => 1 - Math.pow(1 - x, 3);
  let lin;

  function hasGL(){
    try{ const c = document.createElement('canvas'); return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl'))); }
    catch(e){ return false; }
  }

  /* ---------- Shared renderer, studio lighting and loop ---------- */
  function stage(canvas){
    let renderer;
    try{ renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: true, powerPreference: 'high-performance'}); }
    catch(e){ return null; }
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.75));
    renderer.setClearColor(0x000000, 0);
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;

    const scene = new THREE.Scene();
    const pmrem = new THREE.PMREMGenerator(renderer);
    const env = new THREE.Scene();
    env.add(new THREE.Mesh(new THREE.BoxGeometry(40, 40, 40), new THREE.MeshBasicMaterial({color: lin('#0a0405'), side: THREE.BackSide})));
    [[10, 3, [6, 6, 6], -6, 8, 6], [3, 12, [6, .35, .5], 9, 0, -4], [12, 1.2, [3, 3, 3.2], 0, -6, 8], [2, 8, [4, .7, .4], -9, -1, -6]].forEach(b => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(b[0], b[1]),
        new THREE.MeshBasicMaterial({color: new THREE.Color(b[2][0], b[2][1], b[2][2]), side: THREE.DoubleSide}));
      m.position.set(b[3], b[4], b[5]); m.lookAt(0, 0, 0); env.add(m);
    });
    scene.environment = pmrem.fromScene(env, .035).texture;
    scene.add(new THREE.AmbientLight(lin('#3a1a1c'), .55));
    scene.add(new THREE.HemisphereLight(lin('#ffffff'), lin('#2a0508'), .3));
    const key = new THREE.DirectionalLight(lin('#fff1ec'), 1.7); key.position.set(-4, 7, 6); scene.add(key);
    const rim = new THREE.DirectionalLight(lin('#ff2a3d'), 3.2); rim.position.set(6, 2, -5); scene.add(rim);

    const camera = new THREE.PerspectiveCamera(35, 1, .1, 100);
    const host = canvas.parentElement;
    const S = {renderer, scene, camera, host, w: 1, h: 1, visible: true, px: 0, py: 0, hover: false, onResize: null};
    function resize(){
      const r = host.getBoundingClientRect();
      S.w = Math.max(1, r.width); S.h = Math.max(1, r.height);
      renderer.setSize(S.w, S.h, false);
      camera.aspect = S.w / S.h; camera.updateProjectionMatrix();
      if(S.onResize) S.onResize();
    }
    if(window.ResizeObserver) new ResizeObserver(resize).observe(host); else addEventListener('resize', resize);
    resize();
    if(window.IntersectionObserver) new IntersectionObserver(es => { S.visible = es[0].isIntersecting; }).observe(host);
    host.addEventListener('pointermove', e => {
      const r = host.getBoundingClientRect();
      S.px = (e.clientX - r.left) / r.width * 2 - 1; S.py = (e.clientY - r.top) / r.height * 2 - 1; S.hover = true;
    }, {passive: true});
    host.addEventListener('pointerleave', () => { S.hover = false; });
    S.fit = (halfW, halfH) => {
      const tv = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
      return Math.max(halfH / tv, halfW / (tv * camera.aspect));
    };
    S.loop = fn => {
      let last = performance.now(), t = 0;
      requestAnimationFrame(function frame(now){
        const dt = Math.max(0, Math.min((now - last) / 1000, .05)); last = now;
        if(S.visible){ t += dt; fn(t, dt); renderer.render(scene, camera); }
        requestAnimationFrame(frame);
      });
    };
    return S;
  }

  const edgeLine = (geo, color, opacity) => new THREE.LineSegments(new THREE.EdgesGeometry(geo),
    new THREE.LineBasicMaterial({color: lin(color), transparent: opacity < 1, opacity, toneMapped: false}));

  /* ---------- Founder: bookings per month as 3D columns ---------- */
  function bars(canvas, data, overlay){
    const S = stage(canvas); if(!S) return false;
    const {scene, camera} = S;
    const n = data.length, gap = 1.3, W = .82, H = 3;
    const max = Math.max(1, ...data.map(d => d.value));
    const span = (n - 1) * gap, pw = span + 1.8;
    const root = new THREE.Group(); scene.add(root);

    const plat = new THREE.Mesh(new THREE.BoxGeometry(pw, .14, 2.4),
      new THREE.MeshStandardMaterial({color: lin('#1a0b0c'), metalness: .85, roughness: .32, envMapIntensity: 1.2}));
    plat.position.y = -.07; root.add(plat);
    const pe = edgeLine(plat.geometry, '#ff2a40', .5); pe.position.copy(plat.position); root.add(pe);
    const gp = [];
    for(let x = -pw / 2; x <= pw / 2 + 1e-6; x += .3) gp.push(x, .003, -1.2, x, .003, 1.2);
    for(let z = -1.2; z <= 1.2 + 1e-6; z += .3) gp.push(-pw / 2, .003, z, pw / 2, .003, z);
    const gg = new THREE.BufferGeometry(); gg.setAttribute('position', new THREE.Float32BufferAttribute(gp, 3));
    root.add(new THREE.LineSegments(gg, new THREE.LineBasicMaterial({color: lin('#ff2a40'), transparent: true, opacity: .1, toneMapped: false})));

    const geo = new THREE.BoxGeometry(W, 1, W); geo.translate(0, .5, 0);
    const edgeGeo = new THREE.EdgesGeometry(geo);
    const capGeo = new THREE.BoxGeometry(W * 1.05, .04, W * 1.05);
    const cols = data.map((d, i) => {
      const g = new THREE.Group(); g.position.x = i * gap - span / 2; root.add(g);
      const base = d.current ? .3 : .06;
      const mat = new THREE.MeshStandardMaterial({color: lin('#2b2426'), metalness: .9, roughness: .24, envMapIntensity: 1.4,
        emissive: lin('#ff1f3a'), emissiveIntensity: base});
      const body = new THREE.Mesh(geo, mat); body.userData.i = i; g.add(body);
      const accent = d.current ? '#ff7a45' : '#ff2a40';
      const edges = new THREE.LineSegments(edgeGeo, new THREE.LineBasicMaterial({color: lin(accent), transparent: true, opacity: .9, toneMapped: false}));
      g.add(edges);
      const cap = new THREE.Mesh(capGeo, new THREE.MeshBasicMaterial({color: lin(accent), toneMapped: false})); g.add(cap);
      const val = document.createElement('div'); val.className = 'b3-val'; val.textContent = '0';
      const lab = document.createElement('div'); lab.className = 'b3-lab'; lab.textContent = d.label;
      overlay.appendChild(val); overlay.appendChild(lab);
      return {g, body, edges, cap, mat, val, lab, d, base, shown: -1,
              h: d.value ? Math.max(.14, d.value / max * H) : .02};
    });

    const beamMat = new THREE.MeshBasicMaterial({color: lin('#ff3048'), transparent: true, opacity: 0, depthWrite: false,
      blending: THREE.AdditiveBlending, side: THREE.DoubleSide, toneMapped: false});
    const beam = new THREE.Mesh(new THREE.BoxGeometry(.05, .03, 2.4), beamMat);
    beam.position.y = .02; root.add(beam);

    let R = 12;
    S.onResize = () => { R = S.fit(pw / 2 + .5, 2.6) * 1.08; };
    S.onResize();
    const v = new THREE.Vector3(), ndc = new THREE.Vector2(), ray = new THREE.Raycaster();
    const place = (el, x, y, z, dy) => {
      v.set(x, y, z).applyMatrix4(root.matrixWorld).project(camera);
      el.style.transform = 'translate(' + ((v.x * .5 + .5) * S.w).toFixed(1) + 'px,' + ((-v.y * .5 + .5) * S.h).toFixed(1) + 'px) translate(-50%,' + dy + ')';
    };
    let yaw = -.38, pitch = .42;
    S.loop(t => {
      const ty = -.38 + (reduce ? 0 : Math.sin(t * .16) * .22) + (S.hover ? S.px * .18 : 0);
      const tp = .42 + (S.hover ? -S.py * .08 : 0);
      yaw += (ty - yaw) * .05; pitch += (tp - pitch) * .05;
      camera.position.set(Math.sin(yaw) * Math.cos(pitch) * R, 1.25 + Math.sin(pitch) * R, Math.cos(yaw) * Math.cos(pitch) * R);
      camera.lookAt(0, 1.25, 0);
      root.updateMatrixWorld();

      let hovered = -1;
      if(S.hover){
        ndc.set(S.px, -S.py); ray.setFromCamera(ndc, camera);
        const hit = ray.intersectObjects(cols.map(c => c.body))[0];
        if(hit) hovered = hit.object.userData.i;
      }
      cols.forEach((c, i) => {
        const p = reduce ? 1 : clamp01((t - .25 - i * .13) / 1.1);
        const e = p >= 1 ? 1 : Math.max(0, easeOutBack(p));
        const h = Math.max(.001, c.h * e);
        c.body.scale.y = h; c.edges.scale.y = h; c.cap.position.y = h + .02;
        const pulse = reduce ? 0 : Math.max(0, Math.sin(t * 1.8 - i * .7)) * .06;
        const glow = hovered === i ? .75 : c.base + pulse;
        c.mat.emissiveIntensity += (glow - c.mat.emissiveIntensity) * .15;
        const shown = Math.round(c.d.value * Math.min(1, p * 1.15));
        if(shown !== c.shown){ c.val.textContent = shown; c.shown = shown; }
        c.val.classList.toggle('on', hovered === i); c.lab.classList.toggle('on', hovered === i);
        place(c.val, c.g.position.x, h + .2, 0, '-100%');
        place(c.lab, c.g.position.x, 0, W / 2 + .4, '0');
      });
      const bp = reduce ? -1 : ((t * .22) % 1.6) - .3;
      beam.position.x = -pw / 2 + pw * clamp01(bp);
      beamMat.opacity = bp >= 0 && bp <= 1 ? Math.sin(Math.PI * bp) * .9 : 0;
    });
    return true;
  }

  /* ---------- Client: the project built block by block ---------- */
  function blocks(canvas, progress){
    const S = stage(canvas); if(!S) return false;
    const {scene, camera} = S;
    const NX = 5, NZ = 5, NY = 3, s = .42, gp = .06, step = s + gp, total = NX * NY * NZ;
    const filled = Math.round(clamp01(progress / 100) * total);
    const root = new THREE.Group(); scene.add(root);
    const pw = NX * step + .5, off = (NX - 1) * step / 2;

    const plat = new THREE.Mesh(new THREE.BoxGeometry(pw, .12, pw),
      new THREE.MeshStandardMaterial({color: lin('#1a0b0c'), metalness: .85, roughness: .3, envMapIntensity: 1.2}));
    plat.position.y = -.06; root.add(plat);
    const pe = edgeLine(plat.geometry, '#ff2a40', .6); pe.position.copy(plat.position); root.add(pe);

    const geo = new THREE.BoxGeometry(s, s, s), eg = new THREE.EdgesGeometry(geo);
    const litMat = new THREE.MeshStandardMaterial({color: lin('#3a1f22'), metalness: .85, roughness: .24, envMapIntensity: 1.4,
      emissive: lin('#ff1f3a'), emissiveIntensity: .3});
    const lastMat = litMat.clone();
    const litEdge = new THREE.LineBasicMaterial({color: lin('#ff3048'), toneMapped: false});
    const ghostEdge = new THREE.LineBasicMaterial({color: lin('#ff2a40'), transparent: true, opacity: .13, toneMapped: false});
    const placed = [];
    let k = 0, nextSlot = null;
    for(let y = 0; y < NY; y++) for(let z = 0; z < NZ; z++) for(let xi = 0; xi < NX; xi++){
      const x = z % 2 ? NX - 1 - xi : xi;
      const pos = new THREE.Vector3(x * step - off, s / 2 + y * step, z * step - off);
      if(k < filled){
        const last = k === filled - 1 && filled < total;
        const m = new THREE.Mesh(geo, last ? lastMat : litMat);
        m.add(new THREE.LineSegments(eg, litEdge));
        m.position.copy(pos); m.visible = reduce; root.add(m);
        placed.push({m, pos, last, delay: .35 + k * (2.4 / Math.max(filled, 1)), drop: 2.6 + Math.random() * 1.6, spin: (Math.random() - .5) * 4});
      } else {
        if(k === filled) nextSlot = pos;
        const e = new THREE.LineSegments(eg, ghostEdge); e.position.copy(pos); root.add(e);
      }
      k++;
    }

    // Laser that marks where the next block goes
    const laserMat = new THREE.MeshBasicMaterial({color: lin('#ff3048'), transparent: true, opacity: 0, depthWrite: false,
      blending: THREE.AdditiveBlending, toneMapped: false});
    const laser = new THREE.Mesh(new THREE.BoxGeometry(.03, 1, .03), laserMat);
    const target = nextSlot || (placed.length ? placed[placed.length - 1].pos : new THREE.Vector3());
    const top = NY * step + 1.6;
    laser.scale.y = top - target.y; laser.position.set(target.x, (top + target.y) / 2, target.z);
    root.add(laser);
    const marker = edgeLine(new THREE.BoxGeometry(s * 1.15, s * 1.15, s * 1.15), '#ff7a45', 1);
    marker.position.copy(target); marker.visible = !!nextSlot; root.add(marker);

    // Scanner frame that sweeps up and down the structure
    const sq = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-pw / 2, 0, -pw / 2), new THREE.Vector3(pw / 2, 0, -pw / 2), new THREE.Vector3(pw / 2, 0, pw / 2), new THREE.Vector3(-pw / 2, 0, pw / 2)]),
      new THREE.LineBasicMaterial({color: lin('#ff3048'), transparent: true, opacity: 0, toneMapped: false}));
    root.add(sq);

    let R = 8;
    S.onResize = () => { R = S.fit(pw * .78, pw * .62) * 1.12; };
    S.onResize();
    const doneAll = filled >= total;
    S.loop(t => {
      const yaw = .75 + (reduce ? 0 : t * .1) + (S.hover ? S.px * .25 : 0);
      camera.position.set(Math.sin(yaw) * R * .82, R * .62, Math.cos(yaw) * R * .82);
      camera.lookAt(0, NY * step * .38, 0);
      placed.forEach(b => {
        const p = reduce ? 1 : clamp01((t - b.delay) / .55);
        b.m.visible = p > 0;
        b.m.position.y = b.pos.y + b.drop * (1 - p * p);
        b.m.rotation.y = b.spin * (1 - p);
        const l = t - b.delay - .55;
        if(!reduce && l > 0 && l < .25){ const q = Math.sin(l / .25 * Math.PI); b.m.scale.set(1 + q * .12, 1 - q * .2, 1 + q * .12); }
        else b.m.scale.set(1, 1, 1);
      });
      const pulse = reduce ? .5 : .5 + .5 * Math.sin(t * 4);
      lastMat.emissiveIntensity = .4 + pulse * .9;
      litMat.emissiveIntensity = doneAll ? .35 + (reduce ? 0 : Math.sin(t * 2) * .15) : .3;
      const ready = reduce || t > 2.9;
      laserMat.opacity = ready && nextSlot ? .35 + pulse * .45 : 0;
      marker.material.opacity = 1; marker.visible = ready && !!nextSlot;
      marker.rotation.y = reduce ? 0 : t * .8;
      const sp = reduce ? -1 : (t * .3) % 1.8;
      sq.position.y = clamp01(sp) * (NY * step + .2);
      sq.material.opacity = sp <= 1 ? Math.sin(Math.PI * clamp01(sp)) * .8 : 0;
    });
    return true;
  }

  /* ---------- Sign-in pages: armoured cube lattice that twists like a puzzle ---------- */
  function gate(canvas, mode){
    const S = stage(canvas); if(!S) return false;
    const {scene, camera} = S;
    const founder = mode === 'founder';
    const root = new THREE.Group(); root.rotation.set(.5, -.72, 0); scene.add(root);
    const C = .52, G = .58;
    const metal = new THREE.MeshStandardMaterial({color: lin('#2b2628'), metalness: .93, roughness: .24, envMapIntensity: 1.4});
    const plate = new THREE.MeshStandardMaterial({color: lin('#3b3436'), metalness: .95, roughness: .16, envMapIntensity: 1.6});
    const seam = new THREE.LineBasicMaterial({color: lin('#ff2a40'), transparent: true, opacity: .85, toneMapped: false});
    const vent = new THREE.MeshBasicMaterial({color: lin(founder ? '#ff7a45' : '#ff2a40'), toneMapped: false});
    const geo = new THREE.BoxGeometry(C, C, C), eg = new THREE.EdgesGeometry(geo);
    const plateGeo = new THREE.BoxGeometry(C * .66, C * .66, .02), ventGeo = new THREE.BoxGeometry(C * .42, .03, .012);
    const shell = new THREE.Group(); root.add(shell);
    const pivot = new THREE.Group(); shell.add(pivot);
    const cubies = [];
    for(let x = -1; x <= 1; x++) for(let y = -1; y <= 1; y++) for(let z = -1; z <= 1; z++){
      if(!x && !y && !z) continue;
      const g = new THREE.Group();
      g.add(new THREE.Mesh(geo, metal));
      g.add(new THREE.LineSegments(eg, seam));
      [[x, 0, 0], [0, y, 0], [0, 0, z]].forEach((nrm, idx) => {
        if(!nrm[0] && !nrm[1] && !nrm[2]) return;
        const p = new THREE.Mesh(plateGeo, plate);
        p.position.set(nrm[0] * (C / 2 + .01), nrm[1] * (C / 2 + .01), nrm[2] * (C / 2 + .01));
        if(nrm[0]) p.rotation.y = Math.PI / 2;
        if(nrm[1]) p.rotation.x = Math.PI / 2;
        g.add(p);
        if((x + y + z + 3 + idx) % 2 === 0){
          const vv = new THREE.Mesh(ventGeo, vent);
          vv.position.set(nrm[0] * (C / 2 + .025), nrm[1] * (C / 2 + .025), nrm[2] * (C / 2 + .025));
          if(nrm[0]) vv.rotation.y = Math.PI / 2;
          if(nrm[1]) vv.rotation.x = Math.PI / 2;
          g.add(vv);
        }
      });
      g.userData.L = new THREE.Vector3(x, y, z);
      g.position.set(x * G, y * G, z * G);
      shell.add(g); cubies.push(g);
    }
    const coreMat = new THREE.MeshStandardMaterial({color: lin('#300408'), emissive: lin('#ff2a3d'), emissiveIntensity: 1.6, flatShading: true});
    const core = new THREE.Mesh(new THREE.OctahedronGeometry(.3, 0), coreMat); root.add(core);
    const coreLight = new THREE.PointLight(lin('#ff2a3d'), 2, 4, 2); root.add(coreLight);

    const frame = new THREE.Group(); frame.rotation.x = Math.PI / 2 - .3; root.add(frame);
    const frameSpin = new THREE.Group(); frame.add(frameSpin);
    const FS = 1.55;
    [[0, FS, 2 * FS, .05], [0, -FS, 2 * FS, .05], [FS, 0, .05, 2 * FS], [-FS, 0, .05, 2 * FS]].forEach(b => {
      const beam = new THREE.Mesh(new THREE.BoxGeometry(b[2], b[3], .05), metal); beam.position.set(b[0], b[1], 0); frameSpin.add(beam);
    });
    [[1, 1], [1, -1], [-1, 1], [-1, -1]].forEach(c => {
      const blk = new THREE.Mesh(new THREE.BoxGeometry(.13, .13, .13), vent); blk.position.set(c[0] * FS, c[1] * FS, 0); frameSpin.add(blk);
    });

    const pts = [];
    for(let i = 0; i < 700; i++){
      const vs = .3;
      pts.push(Math.round((Math.random() - .5) * 14 / vs) * vs, Math.round((Math.random() - .5) * 10 / vs) * vs, Math.round((Math.random() - .5) * 6 / vs) * vs - 2);
    }
    const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    const dust = new THREE.Points(pg, new THREE.PointsMaterial({color: lin('#ff3048'), size: .035, transparent: true, opacity: .55, toneMapped: false}));
    scene.add(dust);

    let R = 7;
    S.onResize = () => { R = S.fit(2.7, 2.5) * 1.05; };
    S.onResize();

    let turn = null, nextTurn = .8;
    const q = Math.PI / 2;
    function startTurn(t){
      const axis = ['x', 'y', 'z'][Math.floor(Math.random() * 3)], side = [-1, 0, 1][Math.floor(Math.random() * 3)], dir = Math.random() < .5 ? -1 : 1;
      shell.updateMatrixWorld(true);
      pivot.rotation.set(0, 0, 0); pivot.updateMatrixWorld(true);
      const members = cubies.filter(c => c.userData.L[axis] === side);
      members.forEach(c => pivot.attach(c));
      turn = {axis, dir, members, t0: t};
    }
    function endTurn(){
      pivot.rotation.set(0, 0, 0); pivot.rotation[turn.axis] = turn.dir * q;
      shell.updateMatrixWorld(true);
      turn.members.forEach(c => {
        shell.attach(c);
        c.userData.L.set(Math.round(c.position.x / G), Math.round(c.position.y / G), Math.round(c.position.z / G));
        c.position.copy(c.userData.L).multiplyScalar(G);
        c.rotation.set(Math.round(c.rotation.x / q) * q, Math.round(c.rotation.y / q) * q, Math.round(c.rotation.z / q) * q);
      });
      pivot.rotation.set(0, 0, 0);
      turn = null;
    }
    const servo = (t, period, move, stepA) => { const k = Math.floor(t / period), r = clamp01((t - k * period) / move); return (k + easeOutBack(r)) * stepA; };
    const every = founder ? 1.1 : 1.6;
    S.loop(t => {
      if(!reduce){
        if(!turn && t >= nextTurn){ startTurn(t); nextTurn = t + every; }
        if(turn){
          const p = clamp01((t - turn.t0) / .45);
          pivot.rotation.set(0, 0, 0); pivot.rotation[turn.axis] = turn.dir * q * easeOutBack(p);
          if(p >= 1) endTurn();
        }
        root.rotation.y = -.72 + t * .12;
        frameSpin.rotation.z = servo(t, 1.6, .5, Math.PI / 4);
        core.rotation.x += .02; core.rotation.y += .03;
        dust.rotation.y = t * .02;
      }
      const glow = .5 + .5 * Math.sin(t * (founder ? 3 : 2));
      coreMat.emissiveIntensity = 1.2 + glow * 1.4;
      coreLight.intensity = 1.5 + glow * 2;
      camera.position.set((S.hover ? S.px : 0) * .8, (S.hover ? -S.py : 0) * .5 + .2, R);
      camera.lookAt(0, 0, 0);
    });
    return true;
  }

  function init(){
    const canvases = document.querySelectorAll('canvas[data-3d]');
    if(!canvases.length) return;
    if(!window.THREE || !hasGL()){ document.documentElement.classList.add('no-gl'); return; }
    lin = h => new THREE.Color(h).convertSRGBToLinear();
    canvases.forEach(c => {
      let ok = false;
      try{
        const kind = c.getAttribute('data-3d');
        if(kind === 'bars'){
          const data = JSON.parse(document.getElementById(c.dataset.source).textContent);
          ok = bars(c, data, document.getElementById(c.dataset.overlay));
        } else if(kind === 'blocks') ok = blocks(c, Number(c.dataset.progress) || 0);
        else if(kind === 'gate') ok = gate(c, c.dataset.mode);
      }catch(e){ if(window.console) console.warn('3D scene failed', e); ok = false; }
      if(!ok) document.documentElement.classList.add('no-gl');
    });
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
