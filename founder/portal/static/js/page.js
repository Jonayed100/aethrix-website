/* Project Aethrix · light script for inner pages (project details): menu, tilt, magnetic buttons */
(function(){
  'use strict';
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = matchMedia('(pointer: fine)').matches;

  const menuBtn = document.getElementById('menuBtn'), navPanel = document.getElementById('navPanel');
  if(menuBtn && navPanel){
    menuBtn.addEventListener('click', () => {
      const open = navPanel.hidden;
      navPanel.hidden = !open;
      menuBtn.setAttribute('aria-expanded', String(open));
    });
  }

  const bar = document.getElementById('navProgress');
  if(bar){
    const sync = () => {
      const max = document.documentElement.scrollHeight - innerHeight;
      bar.style.transform = 'scaleX(' + (max > 0 ? Math.min(1, scrollY / max) : 0).toFixed(4) + ')';
    };
    addEventListener('scroll', sync, {passive: true}); sync();
  }

  /* Cube follows the pointer a little */
  const cube = document.querySelector('.pd-cube-stage');
  if(cube && finePointer && !reduce){
    addEventListener('pointermove', e => {
      const x = e.clientX / innerWidth - .5, y = e.clientY / innerHeight - .5;
      cube.style.setProperty('--px', (x * 24).toFixed(2) + 'deg');
      cube.style.setProperty('--py', (-y * 18).toFixed(2) + 'deg');
    }, {passive: true});
  }

  /* Feature cards appear as you scroll */
  const cards = document.querySelectorAll('.feat, .road li, .pd-other');
  if('IntersectionObserver' in window && !reduce){
    const io = new IntersectionObserver(entries => {
      entries.forEach(en => { if(en.isIntersecting){ en.target.classList.add('in'); io.unobserve(en.target); } });
    }, {rootMargin: '0px 0px -8% 0px'});
    cards.forEach((c, i) => { c.style.setProperty('--d', (i % 4) * 70 + 'ms'); c.classList.add('pre'); io.observe(c); });
  }

  if(finePointer && !reduce){
    document.querySelectorAll('.magnet').forEach(el => {
      el.addEventListener('pointermove', e => {
        const r = el.getBoundingClientRect();
        el.style.transform = 'translate(' + ((e.clientX - r.left - r.width / 2) * .18).toFixed(1) + 'px,' + ((e.clientY - r.top - r.height / 2) * .28).toFixed(1) + 'px)';
      });
      el.addEventListener('pointerleave', () => { el.style.transform = ''; });
    });
  }
})();