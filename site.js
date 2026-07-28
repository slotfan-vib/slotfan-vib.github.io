/* Shared behaviour: theme toggle, mobile nav, scroll reveal.
   Progressive enhancement — the site is fully usable without JS. */
(function () {
  'use strict';

  var root = document.documentElement;

  /* ------------------------------------------------------------ Theme */
  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  function currentTheme() {
    return root.getAttribute('data-theme') ||
      (systemPrefersDark() ? 'dark' : 'light');
  }
  function setTheme(theme) {
    root.setAttribute('data-theme', theme);
    try { localStorage.setItem('theme', theme); } catch (e) {}
    document.querySelectorAll('.theme-toggle').forEach(function (btn) {
      btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
    });
  }
  document.querySelectorAll('.theme-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      setTheme(currentTheme() === 'dark' ? 'light' : 'dark');
    });
  });

  /* -------------------------------------------------------- Mobile nav */
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    var closeNav = function () {
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    };
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    links.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', closeNav);
    });
    window.addEventListener('resize', function () {
      if (window.innerWidth > 760) closeNav();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeNav();
    });
  }

  /* ------------------------------------------------------- Scroll reveal */
  var reduce = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var items = document.querySelectorAll(
    '[data-reveal], .timeline-entry, .news-item, .publication-card, .project-card, .person-card, .teaching-card'
  );

  if (reduce || !('IntersectionObserver' in window)) {
    items.forEach(function (el) { el.classList.add('visible'); });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var el = entry.target;
      var siblings = el.parentElement ? el.parentElement.children : [el];
      var idx = Array.prototype.indexOf.call(siblings, el);
      el.style.setProperty('--reveal-delay', Math.min(idx, 6) * 0.05 + 's');
      el.classList.add('visible');
      observer.unobserve(el);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  items.forEach(function (el) {
    if (!el.classList.contains('reveal')) el.classList.add('reveal');
    observer.observe(el);
  });

  /* ------------------------------------------------ Live vibration trace */
  var wave = document.querySelector('.waveform-line');
  var sig = document.querySelector('.hero-signature');
  if (wave) {
    var W = 1200, base = 42, A = 36, k = 2.4, f = 4.6, N = 200;  // TRIAL: A 30->36 (taller)
    var travel = 2 * Math.PI * 0.20;   // TRIAL: 0.26->0.20 (slower) — waves propagate along the beam
    var onscreen = true, running = false, startTs = null;

    function frame(ts) {
      if (!onscreen) { running = false; return; }
      if (startTs === null) startTs = ts;
      var t = (ts - startTs) / 1000;
      var d = '';
      for (var i = 0; i <= N; i++) {
        var x = i / N * W;
        var env = Math.exp(-k * (x / W));
        var y = base - A * env * Math.sin(2 * Math.PI * f * (x / W) - travel * t);
        d += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ' ' + y.toFixed(2) + ' ';
      }
      wave.setAttribute('d', d);
      requestAnimationFrame(frame);
    }
    function startWave() {
      if (running) return;
      running = true; startTs = null;
      wave.style.strokeDasharray = 'none';
      requestAnimationFrame(frame);
    }

    if (sig && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        onscreen = entries[0].isIntersecting;
        if (onscreen) startWave();
      }, { threshold: 0.05 }).observe(sig);
    }
    // Kick off after the one-time draw-in animation completes.
    setTimeout(function () { if (onscreen) startWave(); }, 2200);
  }
})();
