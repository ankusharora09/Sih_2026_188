/** Typed API client for the SIH 26188 backend (all routes under /api/v1). */

const BASE = '/api/v1'

let token = sessionStorage.getItem('is_token') || ''
let role = sessionStorage.getItem('is_role') || 'officer'

export function setToken(t: string, r?: string) {
  token = t
  role = r || role
  if (t) {
    sessionStorage.setItem('is_token', t)
    sessionStorage.setItem('is_role', r || role)
  } else {
    sessionStorage.removeItem('is_token')
    sessionStorage.removeItem('is_role')
  }
}
export function getToken() { return token }
export function getRole() { return role }

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(opts.headers as any) }
  if (token) headers.Authorization = `Bearer ${token}`
  if (opts.body && !(opts.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const res = await fetch(BASE + path, { ...opts, headers })
  if (!res.ok) {
    let msg = `${res.status}`
    try { msg = (await res.json())?.detail ?? msg } catch { /* keep status */ }
    throw new ApiError(res.status, msg)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

/** Authorized blob download (for images that need the bearer header). */
export async function fetchBlob(path: string): Promise<string> {
  const res = await fetch(BASE + path, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!res.ok) throw new ApiError(res.status, `fetch failed: ${res.status}`)
  return URL.createObjectURL(await res.blob())
}

export const api = {
  devToken: (officerId: string, role: string) =>
    req<{ access_token: string; token_type: string }>('/auth/dev-token', {
      method: 'POST',
      body: JSON.stringify({ user_id: officerId, role }),
    }),
  health: () => req<any>('/intelligence/health'),
  analytics: (days = 30) => req<any>(`/intelligence/analytics?days=${days}`),
  activity: (limit = 40) => req<any[]>(`/intelligence/activity?limit=${limit}`),
  graph: () => req<any>('/intelligence/fraud-graph'),
  cases: () => req<any[]>('/cases'),
  caseDetail: (id: string) => req<any>(`/cases/${id}`),
  caseFiles: (caseId: string) => req<any[]>(`/cases/${caseId}/files`),
  fileContentUrl: (caseId: string, fileId: string) => `/cases/${caseId}/files/${fileId}/content`,
  createCase: (subject_name: string | null) =>
    req<{ case_id: string }>('/cases', { method: 'POST', body: JSON.stringify({ subject_name }) }),
  uploadFile: (caseId: string, file: File, fileType = 'document') => {
    const fd = new FormData()
    fd.append('upload', file, file.name)
    fd.append('file_type', fileType)
    return req<any>(`/cases/${caseId}/files`, { method: 'POST', body: fd })
  },
  startScreening: (caseId: string) => req<any>(`/cases/${caseId}/screen`, { method: 'POST' }),
  latestRun: (caseId: string) => req<any>(`/cases/${caseId}/screening`),
  decision: (caseId: string, action: string, note: string) =>
    req<any>(`/cases/${caseId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ action, note }),
    }),
  verifyChain: (caseId: string) => req<any>(`/cases/${caseId}/audit/verify`),
  caseAudit: (caseId: string) => req<any[]>(`/cases/${caseId}/audit`),
}
