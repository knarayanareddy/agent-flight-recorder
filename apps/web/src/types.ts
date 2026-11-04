export interface Problem {
  type: string
  title: string
  status: number
  detail?: string
  instance?: string
}

export interface RunSummary {
  id: string
  project_id: string
  state: string
  event_count: number
  created_at: string
  updated_at: string
}

export interface RunDetail extends RunSummary {
  events: Event[]
}

export interface Event {
  id: string
  run_id: string
  seq: number
  kind: string
  actor: string | null
  summary: string | null
  metadata: unknown
  recorded_at: string
}

export interface CaseCreate {
  case_id: string
  run_id: string
  title: string
  definition: unknown
  artifacts: string[]
}

export interface Case {
  id: string
  case_id: string
  run_id: string
  project_id: string
  state: string
  title: string
  definition: unknown
  manifest_sha256: string
  created_at: string
  updated_at: string
}

export interface Replay {
  id: string
  job_id: string | null
  case_id: string
  project_id: string
  state: string
  result: unknown
  created_at: string
  updated_at: string
}

export interface ReplayResult {
  id: string
  job_id: string
  case_id: string
  state: string
  network_calls: number
  checks: Array<{ index: number; outcome: string; reason: string | null }>
  manifest_sha256: string
}
