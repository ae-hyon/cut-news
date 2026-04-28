import React from 'react'
import type { ReactNode } from 'react'

interface AppShellProps {
  children: ReactNode
  error?: string
}

export default function AppShell({ children, error }: AppShellProps) {
  return (
    <main className="stage">
      <section className="app-canvas" aria-label="Annoying Cap app screen">
        {children}
        {!!error && <div className="error-banner">{error}</div>}
      </section>
    </main>
  )
}
