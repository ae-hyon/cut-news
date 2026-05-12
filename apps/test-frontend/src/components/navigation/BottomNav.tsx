import React from 'react'
import type { AppTab } from '../../hooks/usePrototypeApp'

const TABS: Array<{ key: AppTab; icon: string; label: string }> = [
  { key: 'home', icon: '⌂', label: '홈' },
  { key: 'onboarding', icon: '◎', label: '관심사' },
  { key: 'scraps', icon: '★', label: '스크랩' },
]

interface BottomNavProps {
  activeTab: AppTab
  onTabChange: (tab: AppTab) => void
}

export default function BottomNav({ activeTab, onTabChange }: BottomNavProps) {
  return (
    <nav className="bottom-nav" aria-label="하단 메뉴">
      {TABS.map((tab) => (
        <button key={tab.key} className={activeTab === tab.key ? 'active' : ''} onClick={() => onTabChange(tab.key)}>
          <span>{tab.icon}</span><small>{tab.label}</small>
        </button>
      ))}
    </nav>
  )
}
