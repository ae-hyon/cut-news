import React from 'react'
import type { AppTab } from '../../hooks/usePrototypeApp'
import { formatDateLabel } from '../../lib/dateLabel'

interface TopBarProps {
  activeTab: AppTab
  onNavigate: (tab: AppTab) => void
  onProfileClick?: () => void
  onLogout?: () => void
  profilePill?: string
}

export default function TopBar({ activeTab, onNavigate, onProfileClick, onLogout, profilePill = '선우' }: TopBarProps) {
  return (
    <header className="pdf-topbar app-topbar">
      <button className="brand-block" onClick={() => onNavigate('home')}>
        <strong>Annoying Cap</strong>
        <span>{formatDateLabel()}</span>
      </button>
      <nav className="pdf-nav" aria-label="주요 화면">
        <button className={activeTab === 'scraps' ? 'active' : ''} onClick={() => onNavigate('scraps')}>스크랩</button>
      </nav>
      <div className="topbar-actions">
        <button className="profile-pill profile-pill-muted" type="button" aria-label="로그아웃" onClick={onLogout}>로그아웃</button>
        <button className="profile-pill" type="button" aria-label="사용자 프로필" onClick={onProfileClick}>{profilePill}</button>
      </div>
    </header>
  )
}
