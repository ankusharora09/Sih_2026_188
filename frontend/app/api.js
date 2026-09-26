/* =========================================================================
   API client — one place that knows every real backend endpoint.
   401 responses trigger the login gate; other errors surface as toasts.
   ========================================================================= */

const API = (() => {
  const BASE = '/api/v1';
  let token = sessionStorage.getItem('sih_token') || '';
  let onUnauthorized = null;

  function setToken(t) {
    token = t || '';
    if (t) sessionStorage.setItem('sih_token', t);
    else sessionStorage.removeItem('sih_token');
  }
  function getToken() { return token; }
  function setUnauthorizedHandler(fn) { onUnauthorized = fn; }

  async function req(path, { method = 'GET', body, raw = false, silent = false } = {}) {
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (body !== undefined) headers['Content-Type'] = 'application/json';

    let resp;
    try {
      resp = await fetch(`${BASE}${path}`, {
        method, headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (netErr) {
      throw new ApiError('Backend unreachable — is the API server running?', 0, netErr);
    }

    if (resp.status === 401) {
      setToken('');
      if (onUnauthorized) onUnauthorized();
      throw new ApiError('Session expired — please authenticate again.', 401);
    }
    if (!resp.ok) {
      let detail = `Request failed (${resp.status})`;
      try {
        const j = await resp.json();
        detail = typeof j.detail === 'string' ? j.detail
               : Array.isArray(j.detail) ? j.detail.map(d => d.msg || JSON.stringify(d)).join('; ')
               : detail;
      } catch (_) { /* non-JSON error body */ }
      if (!silent) console.warn(`[api] ${method} ${path} → ${resp.status}: ${detail}`);
      throw new ApiError(detail, resp.status);
    }
    if (resp.status === 204) return null;
    return raw ? resp.blob() : resp.json();
  }

  class ApiError extends Error {
    constructor(message, status, cause) {
      super(message);
      this.status = status;
      this.cause = cause;
    }
  }

  return {
    setToken, getToken, setUnauthorizedHandler, ApiError,

    /* ---- auth ---- */
    devToken: (user_id, role) => req('/auth/dev-token', { method: 'POST', body: { user_id, role }, silent: true }),

    /* ---- cases ---- */
    createCase: (subject_name) => req('/cases', { method: 'POST', body: { subject_name } }),
    listCases: () => req('/cases'),
    getCase: (id) => req(`/cases/${id}`),

    /* ---- files ---- */
    uploadFile: (caseId, file, fileType = 'document') => {
      const fd = new FormData();
      fd.append('upload', file, file.name);
      if (fileType) fd.append('file_type', fileType);
      return fetch(`${BASE}/cases/${caseId}/files`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        body: fd,
      }).then(async r => {
        if (!r.ok) throw new ApiError(`Upload failed (${r.status})`, r.status);
        return r.json();
      });
    },
    fileContentUrl: (caseId, fileId) => `${BASE}/cases/${caseId}/files/${fileId}/content`,
    fileBlob: (caseId, fileId) => req(`/cases/${caseId}/files/${fileId}/content`, { raw: true }),
    listFiles: (caseId) => req(`/cases/${caseId}/files`),

    /* ---- screening ---- */
    startScreening: (caseId) => req(`/cases/${caseId}/screen`, { method: 'POST' }),
    getScreening: (caseId) => req(`/cases/${caseId}/screening`),
    caseAudit: (caseId) => req(`/cases/${caseId}/audit`),
    verifyChain: (caseId) => req(`/cases/${caseId}/audit/verify`),

    /* ---- intelligence (dashboard analytics) ---- */
    health: () => req('/intelligence/health'),
    activity: (limit = 20) => req(`/intelligence/activity?limit=${limit}`),
    analytics: (days = 30) => req(`/intelligence/analytics?days=${days}`),
    fraudGraph: (limit = 200) => req(`/intelligence/fraud-graph?limit=${limit}`),
  };
})();
