/* Teaching page: collapsible course-material panels, automatic file
   counts/sizes, and an in-page PDF reader on desktop.
   Progressive enhancement — without JS every panel is open and every
   link opens its PDF directly. */
(function () {
  'use strict';

  /* ------------------------------------------------------ File sizes */
  function formatBytes(bytes) {
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(bytes >= 10485760 ? 0 : 1) + ' MB';
    return Math.max(1, Math.round(bytes / 1024)) + ' KB';
  }
  var sizeCache = {};
  function sizeOf(url) {
    if (!sizeCache[url]) {
      sizeCache[url] = fetch(url, { method: 'HEAD' })
        .then(function (r) { return r.ok ? Number(r.headers.get('content-length')) || 0 : 0; })
        .catch(function () { return 0; });
    }
    return sizeCache[url];
  }
  function fillSizes(panel) {
    panel.querySelectorAll('a[data-pdf]').forEach(function (a) {
      sizeOf(a.getAttribute('href')).then(function (bytes) {
        if (!bytes) return;
        a.setAttribute('data-size', formatBytes(bytes));
        var slot = a.querySelector('.mat-size');
        if (slot) slot.textContent = ' · ' + formatBytes(bytes);
      });
    });
  }

  /* ------------------------------------------------ Material panels */
  document.querySelectorAll('.materials-toggle').forEach(function (btn) {
    var panel = document.getElementById(btn.getAttribute('aria-controls'));
    if (!panel) return;
    var card = btn.closest('.teaching-card');
    var n = panel.querySelectorAll('.mat-open, .mat-chip').length;
    var count = btn.querySelector('.materials-count');
    if (count && n) count.textContent = n + (n === 1 ? ' file' : ' files');
    var sized = false;

    btn.addEventListener('click', function () {
      var open = !panel.classList.contains('open');
      panel.classList.toggle('open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (card) card.classList.toggle('is-open', open);
      if (open && !sized) { sized = true; fillSizes(panel); }
    });
  });

  // Deep link: teaching.html#me331 opens that course's materials
  function openFromHash() {
    var target = location.hash && document.getElementById(location.hash.slice(1));
    var deepBtn = target && target.querySelector('.materials-toggle');
    if (deepBtn && deepBtn.getAttribute('aria-expanded') !== 'true') deepBtn.click();
  }
  openFromHash();
  window.addEventListener('hashchange', openFromHash);

  /* ------------------------------------------------------ PDF reader */
  var dlg = document.querySelector('.pdf-viewer');
  if (!dlg || typeof dlg.showModal !== 'function') return;

  // Phones and tablets can't render PDFs inside an iframe, so they keep
  // the native behaviour (the link opens the file in a new tab).
  var canInline = window.matchMedia('(min-width: 761px) and (hover: hover) and (pointer: fine)');

  var frame = dlg.querySelector('.pv-frame');
  var elCourse = dlg.querySelector('.pv-course');
  var elTitle = dlg.querySelector('.pv-title');
  var elPos = dlg.querySelector('.pv-pos');
  var btnPrev = dlg.querySelector('.pv-prev');
  var btnNext = dlg.querySelector('.pv-next');
  var lnkOpen = dlg.querySelector('.pv-open');
  var lnkDownload = dlg.querySelector('.pv-download');
  var list = [], index = 0, trigger = null;

  function titleOf(a) {
    var t = a.getAttribute('data-title');
    if (t) return t;
    var el = a.querySelector('.mat-title');
    return (el ? el.textContent : a.textContent).trim();
  }

  function show(i) {
    index = i;
    var a = list[i];
    var url = a.getAttribute('href');
    var card = a.closest('.teaching-card');
    var course = card && card.querySelector('.course-title');
    var size = a.getAttribute('data-size');

    elCourse.textContent = (course ? course.textContent : '') + (size ? ' · PDF · ' + size : '');
    elTitle.textContent = titleOf(a);
    frame.title = titleOf(a);
    lnkOpen.href = url;
    lnkDownload.href = url;

    var many = list.length > 1;
    btnPrev.hidden = btnNext.hidden = !many;
    elPos.textContent = many ? (i + 1) + ' / ' + list.length : '';
    btnPrev.disabled = i === 0;
    btnNext.disabled = i === list.length - 1;

    dlg.classList.add('is-loading');
    frame.src = url + '#view=FitH';
  }

  frame.addEventListener('load', function () { dlg.classList.remove('is-loading'); });

  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[data-pdf]');
    if (!a || !canInline.matches) return;
    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    var panel = a.closest('.materials-panel') || document;
    list = Array.prototype.slice.call(panel.querySelectorAll('a[data-pdf]'));
    trigger = a;
    show(list.indexOf(a));
    document.documentElement.classList.add('pv-lock');
    dlg.showModal();
  });

  btnPrev.addEventListener('click', function () { if (index > 0) show(index - 1); });
  btnNext.addEventListener('click', function () { if (index < list.length - 1) show(index + 1); });
  dlg.querySelector('.pv-close').addEventListener('click', function () { dlg.close(); });

  // Click on the dimmed backdrop closes the reader
  dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });

  dlg.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft' && !btnPrev.disabled && !btnPrev.hidden) { e.preventDefault(); show(index - 1); }
    if (e.key === 'ArrowRight' && !btnNext.disabled && !btnNext.hidden) { e.preventDefault(); show(index + 1); }
  });

  dlg.addEventListener('close', function () {
    document.documentElement.classList.remove('pv-lock');
    frame.removeAttribute('src');
    dlg.classList.remove('is-loading');
    if (trigger) trigger.focus();
  });
})();
