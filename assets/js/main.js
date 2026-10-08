/* ============================================================================
   Weifeng Ye · yei1y.github.io
   main.js — theme, language, navigation, reveal animations, reading progress
   No dependencies. Everything degrades gracefully if JS is unavailable.
   ========================================================================= */

(function () {
  'use strict';

  var root = document.documentElement;
  var STORE_THEME = 'wy-theme';
  var STORE_LANG = 'wy-lang';
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------------------------------------------------- theme ---- */
  var themeBtn = document.getElementById('themeBtn');
  var themeIcon = document.getElementById('themeIcon');
  var themeMeta = document.querySelector('meta[name="theme-color"]');

  function paintThemeIcon(theme) {
    if (themeIcon) themeIcon.textContent = theme === 'dark' ? '☀' : '☾';
    if (themeMeta) themeMeta.setAttribute('content', theme === 'dark' ? '#12181D' : '#FBFAF6');
  }

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    paintThemeIcon(theme);
  }

  function storeTheme(theme) {
    try { localStorage.setItem(STORE_THEME, theme); } catch (e) {}
  }

  // A colour-scheme change repaints the whole page; cross-fade it so the switch
  // does not read as a flash. Browsers without the API simply swap instantly.
  function setTheme(theme) {
    if (!reduced && document.startViewTransition) {
      var vt = document.startViewTransition(function () { applyTheme(theme); });
      if (vt && vt.finished && vt.finished.catch) vt.finished.catch(function () {});
    } else {
      applyTheme(theme);
    }
    storeTheme(theme);
  }

  paintThemeIcon(root.getAttribute('data-theme') || 'light');

  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      setTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });
  }

  // Follow the system only while the visitor has not chosen a theme themselves.
  var scheme = window.matchMedia('(prefers-color-scheme: dark)');
  var onSchemeChange = function (e) {
    var stored = null;
    try { stored = localStorage.getItem(STORE_THEME); } catch (err) {}
    if (!stored) applyTheme(e.matches ? 'dark' : 'light');
  };
  if (scheme.addEventListener) scheme.addEventListener('change', onSchemeChange);

  /* ------------------------------------------------------- language ---- */
  var langBtn = document.getElementById('langBtn');

  function paintLangBtn(lang) {
    if (!langBtn) return;
    var next = lang === 'en' ? '中文' : 'English';
    langBtn.setAttribute('aria-label', '切换到' + (lang === 'en' ? '中文' : 'English') + ' / Switch to ' + next);
    langBtn.setAttribute('title', next);
  }

  function setLang(lang) {
    root.setAttribute('data-lang', lang);
    root.setAttribute('lang', lang === 'en' ? 'en' : 'zh-CN');
    paintLangBtn(lang);
    try { localStorage.setItem(STORE_LANG, lang); } catch (e) {}
  }

  paintLangBtn(root.getAttribute('data-lang') === 'en' ? 'en' : 'zh');

  if (langBtn) {
    langBtn.addEventListener('click', function () {
      setLang(root.getAttribute('data-lang') === 'en' ? 'zh' : 'en');
    });
  }

  /* ------------------------------------------------------ mobile nav ---- */
  var burger = document.getElementById('burger');
  var navLinks = document.getElementById('navLinks');

  if (burger && navLinks) {
    burger.addEventListener('click', function () {
      var open = navLinks.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    navLinks.addEventListener('click', function (e) {
      if (e.target.closest('a')) {
        navLinks.classList.remove('is-open');
        burger.setAttribute('aria-expanded', 'false');
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && navLinks.classList.contains('is-open')) {
        navLinks.classList.remove('is-open');
        burger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ----------------------------------------- nav shadow + progress bar -- */
  var nav = document.getElementById('nav');
  var progress = document.getElementById('progress');
  var toTop = document.getElementById('toTop');

  function onScroll() {
    var y = window.scrollY || window.pageYOffset;
    var docH = document.documentElement.scrollHeight - window.innerHeight;
    var ratio = docH > 0 ? Math.min(1, y / docH) : 0;

    if (progress) progress.style.width = (ratio * 100) + '%';
    if (nav) nav.classList.toggle('is-stuck', y > 8);
    if (toTop) toTop.classList.toggle('is-on', y > 760);
  }

  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      onScroll();
      ticking = false;
    });
  }, { passive: true });

  onScroll();

  if (toTop) {
    toTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* --------------------------------------------------- scroll spy ------ */
  // Only anchor links that point at a section on *this* page take part.
  var spyLinks = Array.prototype.filter.call(
    document.querySelectorAll('#navLinks a'),
    function (a) {
      var href = a.getAttribute('href') || '';
      return href.charAt(0) === '#' && href.length > 1;
    }
  );

  if (spyLinks.length) {
    var targets = spyLinks
      .map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); })
      .filter(Boolean);

    if (targets.length) {
      var spy = function () {
        var y = (window.scrollY || window.pageYOffset) + 140;
        var current = null;
        targets.forEach(function (sec) {
          if (sec.offsetTop <= y) current = sec.id;
        });
        spyLinks.forEach(function (a) {
          a.classList.toggle('is-active', a.getAttribute('href') === '#' + current);
        });
      };
      window.addEventListener('scroll', spy, { passive: true });
      spy();
    }
  }

  /* --------------------------------------------------- reveal on scroll - */
  // Deliberately geometry-based rather than IntersectionObserver: the page must
  // never be able to leave content invisible if an observer callback is missed.
  var reveals = Array.prototype.slice.call(document.querySelectorAll('.reveal'));

  function revealCheck() {
    var vh = window.innerHeight || document.documentElement.clientHeight;
    var queued = 0;
    reveals.forEach(function (el) {
      if (el.classList.contains('is-in')) return;
      // Reveal once the element's top edge is near the fold — or if it is
      // already above it (deep link, restored scroll position, printing).
      if (el.getBoundingClientRect().top >= vh - 60) return;
      var delay = reduced ? 0 : Math.min(queued * 55, 220);
      queued++;
      window.setTimeout(function () { el.classList.add('is-in'); }, delay);
    });
  }

  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        io.unobserve(entry.target);
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
    reveals.forEach(function (el) { io.observe(el); });
  }

  // Safety net: covers browsers without IO, and any missed observer callback.
  window.addEventListener('scroll', revealCheck, { passive: true });
  window.addEventListener('resize', revealCheck, { passive: true });
  window.addEventListener('load', revealCheck);
  revealCheck();

  // Last-resort guarantee: nothing on this page may stay invisible because an
  // animation did not fire. After a few seconds every block is simply shown.
  window.setTimeout(function () {
    reveals.forEach(function (el) { el.classList.add('is-in'); });
  }, 2500);

  /* ------------------------------------------------------------ year ---- */
  var yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());
})();
