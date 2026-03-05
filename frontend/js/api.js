/**
 * utils.js
 * --------
 * Shared helpers used across all pages.
 * No dependencies — pure vanilla JS.
 *
 * Exports (attached to window.Utils):
 *   countUp(el, target, options)  — animated number reveal
 *   classifyGPA(label)            — label → CSS class
 *   formatGPA(value, decimals)    — consistent number formatting
 *   toast(message, type)          — show a toast notification
 *   showError(fieldId, message)   — inline field error
 *   clearError(fieldId)           — clear inline field error
 *   initAccordion(el)             — semester accordion behaviour
 *   initSidebarToggle()           — mobile sidebar open/close
 *   setLoading(btn, bool)         — button loading state
 *   debounce(fn, ms)              — debounce utility
 *   formatDate(isoString)         — human-readable date
 */

const Utils = (() => {

  /* ============================================================
     COUNT-UP ANIMATION
     Counts a number from 0 (or startValue) to target over duration ms.
     Uses requestAnimationFrame for smooth 60fps animation.

     Usage:
       countUp(document.getElementById('cgpa'), 3.87)
       countUp(el, 3.87, { duration: 1000, decimals: 2, onDone: () => {} })
     ============================================================ */

  function countUp(el, target, options = {}) {
    if (!el) return;

    const {
      duration  = 900,         // ms
      decimals  = 2,           // decimal places
      start     = 0,           // starting value
      easing    = easeOutExpo, // easing function
      onDone    = null,        // callback when animation ends
      suffix    = '',          // e.g. '/4.0'
      prefix    = '',
    } = options;

    const startTime = performance.now();
    const range = target - start;

    function tick(now) {
      const elapsed  = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const value    = start + range * easing(progress);

      el.textContent = prefix + value.toFixed(decimals) + suffix;

      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = prefix + target.toFixed(decimals) + suffix;
        if (onDone) onDone();
      }
    }

    requestAnimationFrame(tick);
  }

  // Easing: starts fast, decelerates — feels satisfying for a number reveal
  function easeOutExpo(t) {
    return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
  }


  /* ============================================================
     GPA CLASSIFICATION
     Maps the classification string from the API to a CSS class
     and a short display label.
     ============================================================ */

  const CLASSIFICATION_MAP = {
    'first':  { cls: 'first',  short: 'First Class' },
    'upper':  { cls: 'upper',  short: '2nd Class Upper' },
    'second upper': { cls: 'upper', short: '2nd Class Upper' },
    'lower':  { cls: 'lower',  short: '2nd Class Lower' },
    'second lower': { cls: 'lower', short: '2nd Class Lower' },
    'third':  { cls: 'third',  short: 'Third Class' },
    'pass':   { cls: 'third',  short: 'Pass' },
    'fail':   { cls: 'fail',   short: 'Fail' },
  };

  function classifyGPA(label) {
    if (!label) return { cls: 'muted', short: '—' };
    const lower = label.toLowerCase();
    for (const [key, val] of Object.entries(CLASSIFICATION_MAP)) {
      if (lower.includes(key)) return val;
    }
    return { cls: 'muted', short: label };
  }

  // Returns the full classification badge HTML
  function classificationBadge(label) {
    const { cls, short } = classifyGPA(label);
    return `<span class="classification-badge ${cls}">${short}</span>`;
  }


  /* ============================================================
     NUMBER FORMATTING
     ============================================================ */

  function formatGPA(value, decimals = 2) {
    if (value === null || value === undefined || isNaN(value)) return '—';
    return Number(value).toFixed(decimals);
  }

  function formatDate(isoString) {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-GB', {
      day:   'numeric',
      month: 'short',
      year:  'numeric',
    });
  }

  function formatDateTime(isoString) {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-GB', {
      day:   'numeric',
      month: 'short',
      year:  'numeric',
      hour:  '2-digit',
      minute:'2-digit',
    });
  }


  /* ============================================================
     TOAST NOTIFICATIONS
     Appends a toast to .toast-container (created if not present).
     Auto-dismisses after 4s.
     ============================================================ */

  const TOAST_ICONS = {
    success: '✓',
    error:   '✕',
    warning: '⚠',
    info:    'ℹ',
  };

  function toast(message, type = 'info', duration = 4000) {
    // Ensure message is always a string
    if (typeof message === 'object' && message !== null) {
      message = message.message || message.detail || JSON.stringify(message);
    }
    message = String(message || 'An error occurred.');
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `
      <span class="toast-icon">${TOAST_ICONS[type] || 'ℹ'}</span>
      <span class="toast-message">${message}</span>
    `;

    container.appendChild(el);

    // Trigger enter animation on next frame
    requestAnimationFrame(() => {
      requestAnimationFrame(() => el.classList.add('show'));
    });

    // Auto-dismiss
    setTimeout(() => dismiss(el), duration);

    // Click to dismiss
    el.addEventListener('click', () => dismiss(el));

    return el;
  }

  function dismiss(el) {
    el.classList.remove('show');
    el.classList.add('hide');
    el.addEventListener('transitionend', () => el.remove(), { once: true });
  }


  /* ============================================================
     INLINE FIELD ERRORS
     Shows error text directly below an input field.
     ============================================================ */

  function showError(fieldId, message) {
    const field = document.getElementById(fieldId);
    if (!field) return;

    field.classList.add('error');

    // Find or create error element
    let errorEl = field.parentElement.querySelector('.inline-error');
    if (!errorEl) {
      errorEl = document.createElement('div');
      errorEl.className = 'inline-error';
      field.insertAdjacentElement('afterend', errorEl);
    }

    errorEl.textContent = message;
    errorEl.classList.add('visible');
  }

  function clearError(fieldId) {
    const field = document.getElementById(fieldId);
    if (!field) return;

    field.classList.remove('error');

    const errorEl = field.parentElement.querySelector('.inline-error');
    if (errorEl) {
      errorEl.classList.remove('visible');
    }
  }

  function clearAllErrors(formEl) {
    if (!formEl) return;
    formEl.querySelectorAll('.input.error').forEach(el => el.classList.remove('error'));
    formEl.querySelectorAll('.inline-error.visible').forEach(el => el.classList.remove('visible'));
  }


  /* ============================================================
     ACCORDION
     Call once per accordion-item element.
     ============================================================ */

  function initAccordion(item) {
    const trigger = item.querySelector('.accordion-trigger');
    if (!trigger) return;

    trigger.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      item.classList.toggle('open', !isOpen);
    });
  }

  function initAllAccordions(container = document) {
    container.querySelectorAll('.accordion-item').forEach(initAccordion);
  }


  /* ============================================================
     SIDEBAR TOGGLE (mobile)
     ============================================================ */

  function initSidebarToggle() {
    const sidebar = document.querySelector('.sidebar');
    const toggle  = document.querySelector('.sidebar-toggle');
    if (!sidebar || !toggle) return;

    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    // Close sidebar when clicking outside
    document.addEventListener('click', (e) => {
      if (
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !toggle.contains(e.target)
      ) {
        sidebar.classList.remove('open');
      }
    });
  }


  /* ============================================================
     BUTTON LOADING STATE
     ============================================================ */

  function setLoading(btn, isLoading) {
    if (!btn) return;
    if (isLoading) {
      btn.classList.add('loading');
      btn.disabled = true;
      btn._originalText = btn.textContent;
    } else {
      btn.classList.remove('loading');
      btn.disabled = false;
      if (btn._originalText) btn.textContent = btn._originalText;
    }
  }


  /* ============================================================
     MODAL HELPERS
     ============================================================ */

  function openModal(overlayEl) {
    if (!overlayEl) return;
    overlayEl.classList.add('open');
    document.body.style.overflow = 'hidden';

    // Close on backdrop click
    overlayEl.addEventListener('click', (e) => {
      if (e.target === overlayEl) closeModal(overlayEl);
    }, { once: true });

    // Close on Escape
    const onEsc = (e) => {
      if (e.key === 'Escape') { closeModal(overlayEl); document.removeEventListener('keydown', onEsc); }
    };
    document.addEventListener('keydown', onEsc);
  }

  function closeModal(overlayEl) {
    if (!overlayEl) return;
    overlayEl.classList.remove('open');
    document.body.style.overflow = '';
  }


  /* ============================================================
     RESULT PANEL — trigger the reveal animation + count-up
     ============================================================ */

  function revealResult(panelEl, value, options = {}) {
    if (!panelEl) return;

    const numberEl = panelEl.querySelector('.result-number');
    if (!numberEl) return;

    // Add reveal class for the glow animation
    panelEl.classList.remove('reveal');
    void panelEl.offsetWidth; // force reflow to restart animation
    panelEl.classList.add('reveal');

    countUp(numberEl, value, {
      duration: 850,
      decimals: options.decimals ?? 2,
      suffix:   options.suffix ?? '',
    });

    // Update classification badge if present
    if (options.classification) {
      const badgeEl = panelEl.querySelector('.result-classification');
      if (badgeEl) badgeEl.innerHTML = classificationBadge(options.classification);
    }

    // Update scale label if present
    if (options.scale) {
      const scaleEl = panelEl.querySelector('.result-scale');
      if (scaleEl) scaleEl.textContent = scaleLabel(options.scale);
    }
  }


  /* ============================================================
     SCALE LABELS — human-readable from key
     ============================================================ */

  const SCALE_LABELS = {
    '4.0':    '4.0 Scale (US/Canada)',
    '5.0':    '5.0 Scale (Nigeria/West Africa)',
    '6.0_DE': '6-Point Scale (Germany)',
    '110':    '110 Scale (Italy)',
    '30':     '30 Scale (Italy)',
  };

  function scaleLabel(key) {
    return SCALE_LABELS[key] || key;
  }

  const SCALE_OPTIONS_HTML = Object.entries(SCALE_LABELS)
    .map(([k, v]) => `<option value="${k}">${v}</option>`)
    .join('');


  /* ============================================================
     CALC USAGE METER (guest)
     Updates the 5-dot meter showing calculations remaining.
     ============================================================ */

  function updateCalcMeter(containerEl, used, total = 5) {
    if (!containerEl) return;
    const dots = containerEl.querySelectorAll('.calc-dot');
    dots.forEach((dot, i) => {
      dot.classList.toggle('used', i < used);
      dot.classList.toggle('last-used', i === used - 1);
    });
    const textEl = containerEl.querySelector('.calc-meter-text');
    if (textEl) {
      const remaining = total - used;
      textEl.textContent = remaining > 0
        ? `${remaining} of ${total} remaining`
        : 'No calculations remaining';
    }
  }

  // Build the dots HTML
  function calcMeterHTML(used = 0, total = 5) {
    const dots = Array.from({ length: total }, (_, i) =>
      `<span class="calc-dot${i < used ? ' used' : ''}${i === used - 1 ? ' last-used' : ''}"></span>`
    ).join('');
    const remaining = total - used;
    return `
      <div class="calc-meter">
        <div class="calc-meter-dots">${dots}</div>
        <span class="calc-meter-text">${remaining} of ${total} remaining</span>
      </div>
    `;
  }


  /* ============================================================
     DEBOUNCE
     ============================================================ */

  function debounce(fn, ms = 300) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }


  /* ============================================================
     ACTIVE NAV LINK
     Marks the current page's nav link as active in the sidebar.
     ============================================================ */

  function markActiveNav() {
    const current = window.location.pathname.split('/').pop() || 'index';
    document.querySelectorAll('.nav-link').forEach(link => {
      const href = link.getAttribute('href') || '';
      const isActive = href === current || href.endsWith(current);
      link.classList.toggle('active', isActive);
    });
  }


  /* ============================================================
     USER AVATAR INITIALS
     ============================================================ */

  function avatarInitials(email) {
    if (!email) return '?';
    return email.charAt(0).toUpperCase();
  }


  /* ============================================================
     DOM HELPERS
     ============================================================ */

  function $(selector, parent = document) {
    return parent.querySelector(selector);
  }

  function $$(selector, parent = document) {
    return [...parent.querySelectorAll(selector)];
  }

  function el(tag, attrs = {}, ...children) {
    const element = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'class') element.className = v;
      else if (k === 'html') element.innerHTML = v;
      else element.setAttribute(k, v);
    });
    children.forEach(child => {
      if (typeof child === 'string') element.appendChild(document.createTextNode(child));
      else if (child) element.appendChild(child);
    });
    return element;
  }


  // Public API
  return {
    countUp,
    classifyGPA,
    classificationBadge,
    formatGPA,
    formatDate,
    formatDateTime,
    toast,
    showError,
    clearError,
    clearAllErrors,
    initAccordion,
    initAllAccordions,
    initSidebarToggle,
    setLoading,
    openModal,
    closeModal,
    revealResult,
    scaleLabel,
    SCALE_LABELS,
    SCALE_OPTIONS_HTML,
    updateCalcMeter,
    calcMeterHTML,
    debounce,
    markActiveNav,
    avatarInitials,
    $,
    $$,
    el,
  };

})();

window.Utils = Utils;