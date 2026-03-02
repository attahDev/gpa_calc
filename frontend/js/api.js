/**
 * api.js
 * ------
 * All HTTP communication with the FastAPI backend.
 * Every function returns { data, error } — never throws.
 *
 * Token strategy:
 *   - Short-lived access token (15 min) stored in memory only — never localStorage
 *   - Long-lived refresh token stored in httpOnly cookie (set by server)
 *   - On 401, we silently attempt /auth/refresh before retrying once
 *   - On refresh failure, user is redirected to login
 */

const Api = (() => {

  const BASE_URL = (window.APP_CONFIG?.apiBase || 'http://localhost:8000').replace(/\/$/, '');

  // ── Access token in sessionStorage ────────────────────────────────────
  // sessionStorage survives page navigation but clears when the tab closes.
  // The httpOnly refresh cookie is the real long-lived secret.
  // This is just a 15-min convenience store so page reloads don't force re-login.

  const _TOKEN_KEY = 'gpa_access_token';

  function setAccessToken(token) { sessionStorage.setItem(_TOKEN_KEY, token); }
  function getAccessToken()      { return sessionStorage.getItem(_TOKEN_KEY); }
  function clearAccessToken()    { sessionStorage.removeItem(_TOKEN_KEY); }


  // ── Core fetch wrapper ─────────────────────────────────────────────────

  async function request(method, path, body = null, options = {}) {
    const url = `${BASE_URL}${path}`;

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const _token = getAccessToken();
    if (!options.skipAuth && _token) {
      headers['Authorization'] = `Bearer ${_token}`;
    }

    const sessionId = getGuestSessionId();
    if (sessionId && !options.skipSession) {
      headers['X-Session-ID'] = sessionId;
    }

    const config = {
      method,
      headers,
      credentials: 'include',   // send httpOnly refresh cookie on every request
    };

    if (body !== null) config.body = JSON.stringify(body);

    try {
      const response = await fetch(url, config);

      if (response.status === 204) return { data: null, error: null };

      let json;
      try { json = await response.json(); }
      catch { return { data: null, error: 'Server returned an unexpected response.' }; }

      // Silent token refresh on 401 (only once, not on auth routes themselves)
      if (response.status === 401 && !options._retried && !options.skipAuth) {
        const refreshed = await _silentRefresh();
        if (refreshed) {
          return request(method, path, body, { ...options, _retried: true });
        }
        // Refresh failed — redirect to login
        clearAccessToken();
        window.location.href = 'auth.html';
        return { data: null, error: 'Session expired.', code: 'SESSION_EXPIRED' };
      }

      if (!response.ok || json.error === true) {
        const message = json.detail?.message || json.message || json.detail || 'Something went wrong.';
        const code    = json.detail?.code    || json.code    || 'ERROR';
        return { data: null, error: message, code };
      }

      return { data: json, error: null };

    } catch (err) {
      if (err.name === 'TypeError') {
        return { data: null, error: 'Could not reach the server. Check your connection.', code: 'NETWORK_ERROR' };
      }
      return { data: null, error: err.message || 'An unexpected error occurred.', code: 'UNKNOWN' };
    }
  }

  // ── Silent refresh ─────────────────────────────────────────────────────

  let _refreshPromise = null;   // deduplicate concurrent refresh attempts

  async function _silentRefresh() {
    if (_refreshPromise) return _refreshPromise;

    _refreshPromise = (async () => {
      try {
        const response = await fetch(`${BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',   // send the httpOnly cookie
        });
        if (!response.ok) return false;
        const json = await response.json();
        if (json.token) {
          setAccessToken(json.token);
          // Update cached user if present
          if (json.user && typeof Auth !== 'undefined') {
            Auth._setCachedUser(json.user);
          }
          return true;
        }
        return false;
      } catch {
        return false;
      } finally {
        _refreshPromise = null;
      }
    })();

    return _refreshPromise;
  }


  const get    = (path, opts)       => request('GET',    path, null, opts);
  const post   = (path, body, opts) => request('POST',   path, body, opts);
  const patch  = (path, body, opts) => request('PATCH',  path, body, opts);
  const del    = (path, opts)       => request('DELETE', path, null, opts);


  // ── Guest session (still in localStorage — not sensitive) ──────────────

  const SESSION_KEY    = 'gpa_guest_session_id';
  const CALC_COUNT_KEY = 'gpa_guest_calc_count';

  function getGuestSessionId()  { return localStorage.getItem(SESSION_KEY); }
  function setGuestSessionId(id){ localStorage.setItem(SESSION_KEY, id); }
  function clearGuestSession()  {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(CALC_COUNT_KEY);
  }
  function getGuestCalcCount()  { return parseInt(localStorage.getItem(CALC_COUNT_KEY) || '0', 10); }
  function setGuestCalcCount(n) { localStorage.setItem(CALC_COUNT_KEY, String(n)); }


  // ── Auth endpoints ─────────────────────────────────────────────────────

  const auth = {
    async register({ email, password, full_name = null, gpa_scale = '4.0', university_name = null, session_id = null }) {
      const body = { email, password, gpa_scale };
      if (full_name)       body.full_name       = full_name;
      if (university_name) body.university_name = university_name;
      if (session_id)      body.session_id      = session_id;
      return post('/auth/register', body, { skipAuth: true });
    },

    async login(email, password) {
      return post('/auth/login', { email, password }, { skipAuth: true });
    },

    async logout() {
      return post('/auth/logout', {});
    },

    async me() {
      return get('/auth/me');
    },

    async refresh() {
      return _silentRefresh();
    },

    async updateProfile({ full_name, gpa_scale, university_name }) {
      const body = {};
      if (full_name !== undefined)       body.full_name       = full_name;
      if (gpa_scale !== undefined)       body.gpa_scale       = gpa_scale;
      if (university_name !== undefined) body.university_name = university_name;
      return patch('/auth/profile', body);
    },

    async changePassword({ current_password, new_password, confirm_password }) {
      return patch('/auth/password', { current_password, new_password, confirm_password });
    },

    async deleteAccount() {
      return del('/auth/account');
    },
  };


  // ── Guest endpoints ────────────────────────────────────────────────────

  const guest = {
    async createSession() {
      const result = await post('/guest/session', {}, { skipAuth: true, skipSession: true });
      if (result.data) {
        setGuestSessionId(result.data.session_id);
        setGuestCalcCount(result.data.calc_count);
      }
      return result;
    },

    async calculate(expression, scale = '4.0') {
      const result = await post('/guest/calculate', { expression, scale }, { skipAuth: true });
      if (result.data) setGuestCalcCount(result.data.calc_count);
      return result;
    },

    async ensureSession() {
      const existing = getGuestSessionId();
      if (existing) return { data: { session_id: existing }, error: null };
      return guest.createSession();
    },

    getSessionId: getGuestSessionId,
    getCalcCount: getGuestCalcCount,
    setCalcCount: setGuestCalcCount,
    clearSession: clearGuestSession,
  };


  // ── Semester endpoints ─────────────────────────────────────────────────

  const semesters = {
    list()        { return get('/semesters'); },
    create(name)  { return post('/semesters', { name }); },
    remove(id)    { return del(`/semesters/${id}`); },
  };


  // ── Course endpoints ───────────────────────────────────────────────────

  const courses = {
    list(semesterId)                        { return get(`/semesters/${semesterId}/courses`); },
    create(semesterId, { name, credit_hours, grade }) {
      return post(`/semesters/${semesterId}/courses`, { name, credit_hours, grade });
    },
    update(courseId, fields)  { return patch(`/courses/${courseId}`, fields); },
    remove(courseId)          { return del(`/courses/${courseId}`); },
  };


  // ── Calculation endpoints ──────────────────────────────────────────────

  const calculations = {
    semesterGPA(semesterId)            { return get(`/calculations/gpa/${semesterId}`); },
    cgpa()                             { return get('/calculations/cgpa'); },

    convert({ gpa, from_scale, to_scale }) {
      if (!getAccessToken()) {
        const result = post('/guest/convert', { gpa, from_scale, to_scale }, { skipAuth: true });
        result.then(r => { if (r.data) setGuestCalcCount(r.data.calc_count); });
        return result;
      }
      return post('/calculations/convert', { gpa, from_scale, to_scale });
    },

    targetGrade({ target_cgpa, remaining_courses }) {
      return post('/calculations/target-grade', { target_cgpa, remaining_courses });
    },

    projection({ upcoming_courses }) {
      return post('/calculations/projection', { upcoming_courses });
    },
  };


  // ── History endpoints ──────────────────────────────────────────────────

  const history = {
    list()  { return get('/history'); },
    clear() { return del('/history'); },
  };


  // ── Public API ─────────────────────────────────────────────────────────

  return {
    auth,
    guest,
    semesters,
    courses,
    calculations,
    history,
    // Token management — used by auth.js
    setAccessToken,
    getAccessToken,
    clearAccessToken,
    // Guest session helpers — used by auth.js
    getGuestSessionId,
    clearGuestSession,
  };

})();

window.Api = Api;