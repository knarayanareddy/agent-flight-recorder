import { useEffect, useState } from 'react'
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  useParams,
  useLocation,
} from 'react-router-dom'
import {
  listRuns,
  getRun,
  getReplay,
  createCase,
  AfrApiError,
} from './api'
import type {
  RunSummary,
  RunDetail,
  Event,
  CaseCreate,
  Case,
  Replay,
  Problem,
  ReplayResult,
} from './types'

function ProblemBanner({ problem }: { problem: Problem }) {
  return (
    <div role="alert" style={problemStyle}>
      <h3 style={titleStyle}>{problem.title}</h3>
      <p style={detailStyle}>{problem.detail ?? problem.status}</p>
      <p style={instanceStyle}>{problem.instance ?? problem.type}</p>
    </div>
  )
}

const problemStyle = {
  padding: 16,
  margin: 16,
  border: '1px solid #b91c1c',
  background: '#fef2f2',
  color: '#7f1d1d',
  borderRadius: 8,
}
const titleStyle = { margin: 0, fontSize: 16, fontWeight: 600 }
const detailStyle = { margin: '6px 0 0', fontSize: 14 }
const instanceStyle = { margin: '4px 0 0', fontSize: 12, color: '#991b1b' }

function stateBadge(state: string) {
  const color =
    state === 'succeeded'
      ? '#15803d'
      : state === 'failed' || state === 'error'
        ? '#b91c1c'
        : state === 'running' || state === 'leased'
          ? '#b45309'
          : '#334155'
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        color: '#fff',
        background: color,
      }}
    >
      {state}
    </span>
  )
}

function RunsList() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Problem | null>(null)
  const search = useLocation().search
  const params = new URLSearchParams(search)

  useEffect(() => {
    setLoading(true)
    listRuns({
      org_id: params.get('org_id') || undefined,
      project_id: params.get('project_id') || undefined,
      limit: 50,
    })
      .then((data) => {
        setRuns(data)
        setError(null)
      })
      .catch((err: AfrApiError) => setError(err.problem))
      .finally(() => setLoading(false))
  }, [params.get('org_id'), params.get('project_id')])

  if (loading) return <p>Loading runs…</p>
  if (error) return <ProblemBanner problem={error} />

  const scope = params.get('project_id')
    ? ` for project ${params.get('project_id')}`
    : ''
  return (
    <div style={pageStyle}>
      <nav style={navStyle}>
        <Link to="/afr/runs" style={linkStyle}>
          Runs
        </Link>{' '}
        <Link to="/afr/cases/new" style={linkStyle}>
          New case
        </Link>{' '}
        <span style={{ color: '#64748b', fontSize: 13 }}>
          Replay: /afr/replays/:id
        </span>
      </nav>
      <h1 style={h1Style}>Flight runs{scope}</h1>
      <p style={hintStyle}>
        Filter:&nbsp;<code>?org_id=…&amp;project_id=…</code>
      </p>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>Run ID</th>
            <th style={thStyle}>Project</th>
            <th style={thStyle}>State</th>
            <th style={thStyle}>Events</th>
            <th style={thStyle}>Created</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} style={trStyle}>
              <td style={tdStyle}>
                <Link to={`/afr/runs/${run.id}`} style={cellLinkStyle}>
                  {run.id}
                </Link>
              </td>
              <td style={tdStyle}>{run.project_id}</td>
              <td style={tdStyle}>{stateBadge(run.state)}</td>
              <td style={tdStyle}>{run.event_count}</td>
              <td style={tdStyle}>{new Date(run.created_at).toISOString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {runs.length === 0 && <p style={emptyStyle}>No runs yet.</p>}
    </div>
  )
}

const pageStyle = { fontFamily: 'system-ui, sans-serif', maxWidth: 980, margin: '0 auto', padding: 24 }
const navStyle = { marginBottom: 20, paddingBottom: 12, borderBottom: '1px solid #e2e8f0' }
const linkStyle = {
  textDecoration: 'none',
  color: '#2563eb',
  marginRight: 16,
  fontWeight: 500,
}
const h1Style = { margin: '0 0 8px', fontSize: 24 }
const hintStyle = { color: '#64748b', fontSize: 14, marginBottom: 16 }
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse' }
const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '8px 10px',
  borderBottom: '1px solid #e2e8f0',
  fontSize: 13,
  color: '#475569',
}
const trStyle = { borderBottom: '1px solid #f1f5f9' }
const tdStyle = { padding: '8px 10px', fontSize: 14 }
const cellLinkStyle = { color: '#2563eb', textDecoration: 'none' }
const emptyStyle = { color: '#64748b', marginTop: 16 }

function RunDetail() {
  const { run_id } = useParams<{ run_id: string }>()
  const [run, setRun] = useState<RunDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Problem | null>(null)

  useEffect(() => {
    if (!run_id) return
    setLoading(true)
    getRun(run_id)
      .then((data) => {
        setRun(data)
        setError(null)
      })
      .catch((err: AfrApiError) => setError(err.problem))
      .finally(() => setLoading(false))
  }, [run_id])

  if (loading) return <p>Loading run…</p>
  if (error) return <ProblemBanner problem={error} />
  if (!run) return null

  const events: Event[] = run.events ?? []
  return (
    <div style={pageStyle}>
      <Link to="/afr/runs" style={linkStyle}>
        &larr; Runs
      </Link>
      <h1 style={h1Style}>Run {run.id}</h1>
      <div style={metaRowStyle}>
        <span style={metaLabelStyle}>Project:</span>{' '}
        <span style={metaValueStyle}>{run.project_id}</span>{' '}
        <span style={metaLabelStyle}>State:</span>{' '}
        {stateBadge(run.state)}{' '}
        <span style={metaLabelStyle}>Events:</span>{' '}
        <span style={metaValueStyle}>{run.event_count}</span>{' '}
        <span style={metaLabelStyle}>Created:</span>{' '}
        <span style={metaValueStyle}>{new Date(run.created_at).toISOString()}</span>
      </div>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>Seq</th>
            <th style={thStyle}>Kind</th>
            <th style={thStyle}>Actor</th>
            <th style={thStyle}>Summary</th>
            <th style={thStyle}>Recorded</th>
            <th style={thStyle}>Metadata</th>
          </tr>
        </thead>
        <tbody>
          {events.map((ev) => (
            <tr key={ev.id} style={trStyle}>
              <td style={tdStyle}>{ev.seq}</td>
              <td
                style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 13 }}
              >
                {ev.kind}
              </td>
              <td style={tdStyle}>{ev.actor ?? '—'}</td>
              <td style={tdStyle}>{ev.summary ?? '—'}</td>
              <td style={tdStyle}>{new Date(ev.recorded_at).toISOString()}</td>
              <td style={tdStyle}>
                <pre style={metaPreStyle}>{JSON.stringify(ev.metadata, null, 2)}</pre>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const metaRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: 16,
  flexWrap: 'wrap',
  marginBottom: 16,
  fontSize: 14,
  color: '#475569',
}
const metaLabelStyle = { fontWeight: 600 }
const metaValueStyle = { fontWeight: 500 }
const metaPreStyle = {
  margin: 0,
  padding: 8,
  background: '#f8fafc',
  border: '1px solid #e2e8f0',
  borderRadius: 6,
  fontSize: 12,
  overflow: 'auto',
  maxHeight: 240,
}

function CaseForm() {
  const [fields, setFields] = useState<CaseCreate>({
    case_id: '',
    run_id: '',
    title: '',
    definition: {},
    artifacts: [],
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<Problem | null>(null)
  const [created, setCreated] = useState<Case | null>(null)

  const handleChange = (key: keyof CaseCreate, value: unknown) => {
    setFields((prev) => ({ ...prev, [key]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const body: CaseCreate = {
        case_id: fields.case_id,
        run_id: fields.run_id,
        title: fields.title,
        definition: fields.definition,
        artifacts: fields.artifacts.filter(Boolean),
      }
      const caze = await createCase(body)
      setCreated(caze)
    } catch (err: unknown) {
      setError(err instanceof AfrApiError ? err.problem : { type: 'about:blank', title: 'Create failed', status: 0 })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={pageStyle}>
      <Link to="/afr/runs" style={linkStyle}>
        &larr; Runs
      </Link>
      <h1 style={h1Style}>Create frozen case</h1>
      {error && <ProblemBanner problem={error} />}
      {created && (
        <div style={okStyle}>
          <strong>Case frozen:</strong> {created.case_id}&nbsp;·&nbsp;state{' '}
          {stateBadge(created.state)}&nbsp;·&nbsp;manifest{' '}
          <code style={codeStyle}>{created.manifest_sha256}</code>
        </div>
      )}
      <form onSubmit={handleSubmit} style={formStyle}>
        <fieldset disabled={submitting}>
          <div style={fieldRowStyle}>
            <label style={labelStyle}>case_id</label>
            <input
              style={inputStyle}
              name="case_id"
              placeholder="e.g. case-2024-001"
              required
              value={fields.case_id}
              onChange={(e) => handleChange('case_id', e.target.value)}
            />
          </div>
          <div style={fieldRowStyle}>
            <label style={labelStyle}>run_id</label>
            <input
              style={inputStyle}
              name="run_id"
              placeholder="run id from /afr/runs"
              required
              value={fields.run_id}
              onChange={(e) => handleChange('run_id', e.target.value)}
            />
          </div>
          <div style={fieldRowStyle}>
            <label style={labelStyle}>title</label>
            <input
              style={inputStyle}
              name="title"
              placeholder="case title"
              required
              value={fields.title}
              onChange={(e) => handleChange('title', e.target.value)}
            />
          </div>
          <div style={fieldRowStyle}>
            <label style={labelStyle}>artifacts (comma-separated artifact ids)</label>
            <input
              style={inputStyle}
              name="artifacts"
              placeholder="art-1, art-2"
              value={fields.artifacts.join(', ')}
              onChange={(e) =>
                handleChange(
                  'artifacts',
                  e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                )
              }
            />
          </div>
          <div style={fieldRowStyle}>
            <label style={labelStyle}>definition (JSON)</label>
            <textarea
              style={textareaStyle}
              name="definition"
              placeholder='{"mode": "recorded", "checks": [...]}'
              required
              value={JSON.stringify(fields.definition, null, 2)}
              onChange={(e) => {
                try {
                  handleChange('definition', JSON.parse(e.target.value) || {})
                } catch {
                  // keep previous valid value while typing
                }
              }}
            />
          </div>
          <button style={buttonStyle} type="submit" disabled={submitting}>
            {submitting ? 'Freezing…' : 'Freeze case'}
          </button>
        </fieldset>
      </form>
    </div>
  )
}

const codeStyle = { background: '#f1f5f9', padding: '1px 6px', borderRadius: 4 }
const okStyle = {
  padding: 12,
  margin: '16px 0',
  border: '1px solid #86efac',
  background: '#ecfdf5',
  color: '#065f46',
  borderRadius: 6,
}
const formStyle: React.CSSProperties = {
  marginTop: 16,
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}
const fieldRowStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
}
const labelStyle = { fontSize: 13, fontWeight: 600, color: '#334155' }
const inputStyle = {
  padding: '6px 10px',
  fontSize: 14,
  border: '1px solid #cbd5e1',
  borderRadius: 6,
  width: 'min(100%, 420px)',
}
const textareaStyle = {
  padding: '6px 10px',
  fontSize: 13,
  fontFamily: 'ui-monospace, monospace',
  border: '1px solid #cbd5e1',
  borderRadius: 6,
  width: 'min(100%, 700px)',
  height: 160,
}
const buttonStyle = {
  padding: '8px 16px',
  fontSize: 14,
  fontWeight: 600,
  color: '#fff',
  background: '#2563eb',
  border: 'none',
  borderRadius: 6,
  cursor: 'pointer',
  width: 'fit-content',
}

function ReplayDetail() {
  const { id } = useParams<{ id: string }>()
  const [replay, setReplay] = useState<Replay | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Problem | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getReplay(id)
      .then((data) => {
        setReplay(data)
        setError(null)
      })
      .catch((err: AfrApiError) => setError(err.problem))
      .finally(() => setLoading(false))
  }, [id])

  const result = replay?.result as ReplayResult | undefined
  const terminal = replay?.state === 'succeeded' || replay?.state === 'failed' || replay?.state === 'error'

  if (loading) return <p>Loading replay…</p>
  if (error) return <ProblemBanner problem={error} />
  if (!replay) return null

  return (
    <div style={pageStyle}>
      <Link to="/afr/runs" style={linkStyle}>
        &larr; Runs
      </Link>
      <h1 style={h1Style}>Replay {replay.id}</h1>
      <div style={metaRowStyle}>
        <span style={metaLabelStyle}>Case:</span>{' '}
        <span style={metaValueStyle}>{replay.case_id}</span>{' '}
        <span style={metaLabelStyle}>Project:</span>{' '}
        <span style={metaValueStyle}>{replay.project_id}</span>{' '}
        <span style={metaLabelStyle}>State:</span>{' '}
        {stateBadge(replay.state)}
        {terminal && result ? (
          <>
            {' '}
            <span style={metaLabelStyle}>Network calls:</span>{' '}
            <span style={metaValueStyle}>{result.network_calls}</span>{' '}
            <span style={metaLabelStyle}>Checks:</span>{' '}
            <span style={metaValueStyle}>
              {result.checks.filter((c) => c.outcome === 'pass').length} /
              {result.checks.length} passed
            </span>
          </>
        ) : null}
      </div>
      {result && (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>#</th>
              <th style={thStyle}>Outcome</th>
              <th style={thStyle}>Reason</th>
            </tr>
          </thead>
          <tbody>
            {result.checks.map((c: { index: number; outcome: string; reason: string | null }) => (
              <tr key={c.index} style={trStyle}>
                <td style={tdStyle}>{c.index}</td>
                <td style={tdStyle}>{stateBadge(c.outcome)}</td>
                <td style={tdStyle}>{c.reason ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!result && terminal && <p style={emptyStyle}>No result payload recorded.</p>}
      {replay.state === 'running' && (
        <p style={hintStyle}>Replay is running; refresh to poll for the terminal result.</p>
      )}
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Link to="/afr/runs">Go to runs</Link>} />
        <Route path="/afr/runs" element={<RunsList />} />
        <Route path="/afr/runs/:run_id" element={<RunDetail />} />
        <Route path="/afr/cases/new" element={<CaseForm />} />
        <Route path="/afr/replays/:id" element={<ReplayDetail />} />
      </Routes>
    </BrowserRouter>
  )
}
