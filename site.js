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

  /* ------------------------------------------------------ News interaction */
  /* Each card shows two lines of text; a "Read more" button appears only
     when the text is actually cut off, and works the same on every device. */
  var newsCards = document.querySelectorAll('.news-item');
  function syncReadMore() {
    newsCards.forEach(function (item) {
      var desc = item.querySelector('.news-desc');
      var btn = item.querySelector('.news-more');
      if (!desc || !btn || item.classList.contains('open')) return;
      btn.hidden = desc.scrollHeight <= desc.clientHeight + 2;
    });
  }
  newsCards.forEach(function (item) {
    var btn = item.querySelector('.news-more');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var open = item.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.textContent = open ? 'Show less' : 'Read more';
    });
  });
  /* Show the latest six items; "Show all news" reveals the rest in place. */
  var LATEST = 6;
  var newsList = document.getElementById('news-list');
  var newsToggle = document.querySelector('.news-toggle');
  if (newsList && newsToggle && newsCards.length > LATEST) {
    var total = newsCards.length;
    var setToggle = function (expanded) {
      newsList.classList.toggle('is-limited', !expanded);
      newsToggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      newsToggle.innerHTML = expanded
        ? 'Show latest only'
        : 'Show all news <span class="news-toggle-n">(' + total + ')</span>';
    };
    setToggle(false);
    newsToggle.hidden = false;
    newsToggle.addEventListener('click', function () {
      var expand = newsToggle.getAttribute('aria-expanded') !== 'true';
      setToggle(expand);
      if (expand) {
        syncReadMore();   // newly shown cards decide whether they need "Read more"
      } else {
        // Collapsing removes a lot of height; keep the button in view.
        var top = newsToggle.getBoundingClientRect().top;
        if (top < 0 || top > window.innerHeight) {
          newsToggle.scrollIntoView({ block: 'center', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
        }
      }
    });
  }

  if (newsCards.length) {
    syncReadMore();
    window.addEventListener('resize', syncReadMore);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(syncReadMore);
  }

  /* --------------------------------------------- Self-healing stat counts */
  /* Keep the homepage numbers in sync with their source so they never drift:
     "Journal papers" / "Publications" come from publications_data.json and
     "Students mentored" counts the student cards on people.html and
     "Funded projects" counts the project cards on research.html. */
  function setStat(key, n) {
    document.querySelectorAll('[data-count="' + key + '"]').forEach(function (el) {
      el.textContent = n;
      var link = el.closest('[aria-label]');   // keep the screen-reader label in step
      if (link) link.setAttribute('aria-label', link.getAttribute('aria-label').replace(/^\d+/, n));
    });
  }
  if (document.querySelector('[data-count="publications"], [data-count="journal"]')) {
    fetch('publications_data.json')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!Array.isArray(data)) return;
        setStat('publications', data.length);
        setStat('journal', data.filter(function (p) { return p.type === 'Journal'; }).length);
      })
      .catch(function () {});
  }
  function countOnPage(key, url, selector) {
    if (!document.querySelector('[data-count="' + key + '"]') || !window.DOMParser) return;
    fetch(url)
      .then(function (r) { return r.ok ? r.text() : ''; })
      .then(function (page) {
        if (!page) return;
        var doc = new DOMParser().parseFromString(page, 'text/html');
        var n = doc.querySelectorAll(selector).length;
        if (n) setStat(key, n);
      })
      .catch(function () {});
  }
  countOnPage('students', 'people.html', '.people-grid .person-card');
  countOnPage('projects', 'research.html', '#research-projects .project-card');

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
      // Once revealed, drop the reveal styles so the element's own hover
      // transitions (lift, shadow) run at their normal speed.
      var done = function () { el.classList.remove('reveal'); el.style.removeProperty('--reveal-delay'); };
      el.addEventListener('transitionend', function te(ev) {
        if (ev.target !== el || ev.propertyName !== 'opacity') return;
        el.removeEventListener('transitionend', te);
        done();
      });
      setTimeout(done, 1600);
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
    var W = 1200, base = 42, A = 36, k = 1.8, f = 6.0, N = 240;  // richer: more cycles, slower decay
    var travel = 2 * Math.PI * 0.55;   // faster propagation along the beam
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
