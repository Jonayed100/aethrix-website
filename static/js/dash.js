/* Project Aethrix · dashboard behaviour (counters, tabs, tilt, range outputs, copy) */
(function(){
  'use strict';
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = matchMedia('(pointer: fine)').matches;

  /* Count-up numbers: <dd data-count="12"> or data-format="bdt" for taka */
  const bdt = n => '৳ ' + Math.round(n).toLocaleString('en-IN');
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = Number(el.dataset.count) || 0;
    const fmt = el.dataset.format === 'bdt' ? bdt : n => String(Math.round(n));
    if(reduce || target === 0){ el.textContent = fmt(target); return; }
    const t0 = performance.now(), dur = 1200 + Math.min(800, target * 4);
    el.textContent = fmt(0);
    requestAnimationFrame(function step(now){
      const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(target * e);
      if(p < 1) requestAnimationFrame(step);
    });
  });

  /* Tabs: <div data-tabs> with buttons [aria-controls] */
  document.querySelectorAll('[data-tabs]').forEach(group => {
    const buttons = [...group.querySelectorAll('[role=tab]')];
    const show = btn => {
      buttons.forEach(b => {
        const on = b === btn;
        b.setAttribute('aria-selected', String(on));
        b.tabIndex = on ? 0 : -1;
        const panel = document.getElementById(b.getAttribute('aria-controls'));
        if(panel) panel.hidden = !on;
      });
      try{ history.replaceState(null, '', '?tab=' + btn.dataset.tab); }catch(e){}
    };
    buttons.forEach(b => b.addEventListener('click', () => show(b)));
    group.addEventListener('keydown', e => {
      const i = buttons.indexOf(document.activeElement);
      if(i < 0) return;
      if(e.key === 'ArrowRight' || e.key === 'ArrowLeft'){
        const next = buttons[(i + (e.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length];
        next.focus(); show(next);
      }
    });
  });

  /* Range inputs with a live value: <input type=range data-out="id"> */
  document.querySelectorAll('input[type=range][data-out]').forEach(input => {
    const out = document.getElementById(input.dataset.out);
    const bar = input.dataset.bar ? document.getElementById(input.dataset.bar) : null;
    const sync = () => {
      if(out) out.textContent = input.value + '%';
      if(bar) bar.style.setProperty('--p', input.value + '%');
    };
    input.addEventListener('input', sync); sync();
  });

  /* Budget slider: <output data-bdt-for="input id"> shows the amount in taka */
  document.querySelectorAll('output[data-bdt-for]').forEach(out => {
    const input = document.getElementById(out.dataset.bdtFor);
    if(!input) return;
    const sync = () => { out.textContent = bdt(input.value) + (Number(input.value) >= Number(input.max) ? '+' : ''); };
    input.addEventListener('input', sync); sync();
  });

  /* Hide the progress slider's effect when status is Completed */
  const status = document.getElementById('id_o-status'), prog = document.getElementById('id_o-progress');
  if(status && prog){
    const lock = () => { const done = status.value === 'completed'; if(done){ prog.value = 100; prog.dispatchEvent(new Event('input')); } prog.disabled = done; };
    status.addEventListener('change', lock); lock();
    prog.form.addEventListener('submit', () => { prog.disabled = false; });
  }

  /* Card tilt */
  if(finePointer && !reduce){
    document.querySelectorAll('.tilt-card').forEach(el => {
      el.addEventListener('pointermove', e => {
        const r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        el.style.transform = 'perspective(900px) rotateX(' + ((.5 - y) * 6).toFixed(2) + 'deg) rotateY(' + ((x - .5) * 8).toFixed(2) + 'deg)';
      });
      el.addEventListener('pointerleave', () => { el.style.transform = ''; });
    });
  }

  /* Copy buttons: <button data-copy="text"> */
  document.querySelectorAll('[data-copy]').forEach(btn => {
    btn.addEventListener('click', () => {
      const label = btn.textContent, text = btn.dataset.copy;
      const done = () => { btn.textContent = 'Copied'; setTimeout(() => { btn.textContent = label; }, 1500); };
      try{ navigator.clipboard.writeText(text).then(done, () => { btn.textContent = text; }); }
      catch(e){ btn.textContent = text; }
    });
  });

  /* Scroll the message thread to the newest message */
  const thread = document.querySelector('.thread');
  if(thread && location.hash === '#thread'){ thread.lastElementChild && thread.lastElementChild.scrollIntoView({block: 'center'}); }
})();