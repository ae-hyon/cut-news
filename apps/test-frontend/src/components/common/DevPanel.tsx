import React from 'react'
import type { AuthSessionResponse, HealthResponse } from '../../lib/types'

interface DevPanelProps {
  health: HealthResponse | null
  session: AuthSessionResponse | null
  userId: string | null
  loading: boolean
  onRefreshBootstrap: () => void
  onStartDemo: () => void
  onRefreshCurrentState: () => void
  onLogout?: () => void
}

export default function DevPanel({ health, session, userId, loading, onRefreshBootstrap, onStartDemo, onRefreshCurrentState, onLogout }: DevPanelProps) {
  return (
    <details className="dev-panel">
      <summary>debug</summary>
      <div className="dev-grid">
        <span>API {health?.status || 'checking'}</span>
        <span>{session?.session_state || 'anonymous'}</span>
        <span>{userId || 'guest'}</span>
      </div>
      <div className="dev-actions">
        <button onClick={onRefreshBootstrap} disabled={loading}>API</button>
        <button onClick={onStartDemo} disabled={loading}>Demo</button>
        <button onClick={onRefreshCurrentState} disabled={loading || !userId}>Reload</button>
        <button onClick={onLogout} disabled={loading || !userId}>Logout</button>
      </div>
    </details>
  )
}
