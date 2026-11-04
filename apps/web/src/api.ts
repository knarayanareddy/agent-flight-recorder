import type {
  Problem,
  RunSummary,
  RunDetail,
  Replay,
  CaseCreate,
  Case,
} from './types'

declare global {
  interface ImportMetaEnv {
    VITE_API_BASE?: string
  }
  interface ImportMeta {
    env: ImportMetaEnv
  }
}

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api/v1'

class AfrApiError extends Error {
  constructor(public problem: Problem) {
    super(problem.title || 'AfrApiError')
    this.name = 'AfrApiError'
  }
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    let problem: Problem = { type: 'about:blank', title: res.statusText, status: res.status }
    try {
      problem = (await res.json()) as Problem
    } catch {
      // ignore malformed error bodies
    }
    throw new AfrApiError(problem)
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return res
  }
  return res
}

export { AfrApiError }

export async function listRuns(params?: {
  org_id?: string
  project_id?: string
  limit?: number
}): Promise<RunSummary[]> {
  const q = new URLSearchParams()
  if (params?.org_id) q.set('org_id', params.org_id)
  if (params?.project_id) q.set('project_id', params.project_id)
  if (params?.limit) q.set('limit', String(params.limit))
  const res = await request(`/afr/runs?${q.toString()}`)
  return (await res.json()) as RunSummary[]
}

export async function getRun(runId: string): Promise<RunDetail> {
  const res = await request(`/afr/runs/${encodeURIComponent(runId)}`)
  return (await res.json()) as RunDetail
}

export async function getReplay(replayId: string): Promise<Replay> {
  const res = await request(`/afr/replays/${encodeURIComponent(replayId)}`)
  return (await res.json()) as Replay
}

export async function createCase(body: CaseCreate): Promise<Case> {
  const res = await request('/afr/cases', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return (await res.json()) as Case
}
