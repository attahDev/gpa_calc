/**
 * auth.js
 * -------
 * Session management, route protection, and user state.
 *
 * Token strategy:
 *   - Access token lives in memory (Api._accessToken) — never localStorage
 *   - Refresh token lives in httpOnly cookie — JS cannot read it
 *   - User profile cached in sessionStorage (cleared on tab close)
 *   - On page load, we attempt a silent refresh to restore session
 */

const Auth = (() => {

  const USER_KEY = 'gpa_user_cache';   // sessionStorage — cleared on tab close


  // ── User cache ─────────────────────────────────────────────────────────

  function getCachedUser() {
    try {
      const raw = sessionStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  }

  function setCachedUser(user) {
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function clearCachedUser() {
    sessionStorage.removeItem(USER_KEY);
  }

  function getUser() {
    return getCachedUser();
  }


  // ── Session state ──────────────────────────────────────────────────────

  function isLoggedIn() {
    return !!Api.getAccessToken();
  }


  // ── Route protection ───────────────────────────────────────────────────

  async function requireAuth(redirectTo = 'auth') {
    // Try silent refresh first — restores session after page reload
    if (!isLoggedIn()) {
      const ok = await Api.auth.refresh();
      if (!ok) {
        const current = window.location.href;
        window.location.href = `${redirectTo}?next=${encodeURIComponent(current)}`;
        return false;
      }
    }
    return true;
  }

  async function requireGuest(redirectTo = 'dashboard') {
    // If we have a token, already logged in
    if (isLoggedIn()) {
      window.location.href = redirectTo;
      return false;
    }
    // Try silent refresh — if cookie is valid, redirect to dashboard
    const ok = await Api.auth.refresh();
    if (ok) {
      window.location.href = redirectTo;
      return false;
    }
    return true;
  }


  // ── Login / Register / Logout ──────────────────────────────────────────

  async function login(email, password) {
    const { data, error } = await Api.auth.login(email, password);
    if (error) return { data: null, error };

    // Server sets the httpOnly refresh cookie automatically
    // We store the short-lived access token in memory
    Api.setAccessToken(data.token);
    setCachedUser(data.user);
    Api.clearGuestSession();

    return { data, error: null };
  }

  async function register({ email, password, full_name, gpa_scale, university_name }) {
    const session_id = Api.getGuestSessionId();

    const { data, error } = await Api.auth.register({
      email, password, full_name, gpa_scale, university_name, session_id,
    });
    if (error) return { data: null, error };

    Api.setAccessToken(data.token);
    setCachedUser(data.user);
    Api.clearGuestSession();

    return { data, error: null };
  }

  async function logout() {
    await Api.auth.logout().catch(() => {});   // clears the httpOnly cookie server-side
    Api.clearAccessToken();
    clearCachedUser();
    window.location.href = 'index';
  }


  // ── Load / refresh user from API ───────────────────────────────────────

  async function loadUser() {
    if (!isLoggedIn()) return null;

    const { data, error } = await Api.auth.me();
    if (error) {
      // 401 is handled in api.js (auto-refresh + redirect) — just return null here
      return null;
    }

    setCachedUser(data);
    return data;
  }


  // ── Sidebar population ─────────────────────────────────────────────────

  function populateSidebar(user) {
    if (!user) user = getUser();
    if (!user) return;

    document.querySelectorAll('.user-avatar').forEach(el => {
      el.textContent = user.email.charAt(0).toUpperCase();
    });
    document.querySelectorAll('.user-name').forEach(el => {
      el.textContent = user.full_name || user.university_name || user.email;
    });
    document.querySelectorAll('.user-scale').forEach(el => {
      el.textContent = user.gpa_scale + ' scale';
    });
  }


  // ── Init ───────────────────────────────────────────────────────────────

  function init() {
    if (typeof Utils !== 'undefined') {
      Utils.markActiveNav();
      Utils.initSidebarToggle();
    }

    populateSidebar();

    document.querySelectorAll('[data-action="logout"]').forEach(btn => {
      btn.addEventListener('click', e => { e.preventDefault(); logout(); });
    });

    const params = new URLSearchParams(window.location.search);
    if (params.has('next')) {
      sessionStorage.setItem('login_redirect', params.get('next'));
    }
  }

  function handleLoginRedirect() {
    const next = sessionStorage.getItem('login_redirect');
    if (next) {
      sessionStorage.removeItem('login_redirect');
      window.location.href = next;
    } else {
      window.location.href = 'dashboard';
    }
  }


  // ── Public API ─────────────────────────────────────────────────────────

  return {
    getUser,
    isLoggedIn,
    requireAuth,
    requireGuest,
    login,
    register,
    logout,
    loadUser,
    populateSidebar,
    init,
    handleLoginRedirect,
    // Exposed for api.js silent refresh to update cache
    _setCachedUser: setCachedUser,
  };

})();

window.Auth = Auth;