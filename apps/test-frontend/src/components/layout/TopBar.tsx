import React from 'react'
import type { AppTab } from '../../hooks/usePrototypeApp'
import { formatDateLabel } from '../../lib/dateLabel'

interface TopBarProps {
  activeTab: AppTab
  onNavigate: (tab: AppTab) => void
  profilePill?: string
}

export default function TopBar({ activeTab, onNavigate, profilePill = '선우' }: TopBarProps) {
  return (
    <header className="pdf-topbar app-topbar">
      <button className="brand-block" onClick={() => onNavigate('home')}>
        <strong>Annoying Cap</strong>
        <span>{formatDateLabel()}</span>
      </button>
      <nav className="pdf-nav" aria-label="주요 화면">
        <button className={activeTab === 'scraps' ? 'active' : ''} onClick={() => onNavigate('scraps')}>스크랩</button>
        <span>|</span>
        <button className={activeTab === 'archive' ? 'active' : ''} onClick={() => onNavigate('archive')}>아카이브</button>
      </nav>
      <button className="profile-pill" type="button" aria-label="사용자 프로필">{profilePill}</button>
    </header>
  )
}
