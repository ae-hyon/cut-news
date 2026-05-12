'use client'

import { usePathname, useRouter } from 'next/navigation'

const TABS = [
  {
    key: 'home',
    label: '홈',
    path: '/',
    icon: (active: boolean) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--color-accent)' : 'var(--color-text-tertiary)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z" />
        <path d="M9 21V12h6v9" />
      </svg>
    ),
  },
  {
    key: 'scrap',
    label: '스크랩',
    path: '/scrap',
    icon: (active: boolean) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? 'var(--color-accent)' : 'none'} stroke={active ? 'var(--color-accent)' : 'var(--color-text-tertiary)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z" />
      </svg>
    ),
  },
  {
    key: 'archive',
    label: '아카이브',
    path: '/archive',
    icon: (active: boolean) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--color-accent)' : 'var(--color-text-tertiary)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" />
        <path d="M16 2v4M8 2v4M3 10h18" />
        <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" />
      </svg>
    ),
  },
  {
    key: 'profile',
    label: '프로필',
    path: '/profile',
    icon: (active: boolean) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--color-accent)' : 'var(--color-text-tertiary)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="8" r="4" />
        <path d="M20 21a8 8 0 10-16 0" />
      </svg>
    ),
  },
]

export default function TabBar() {
  const pathname = usePathname()
  const router = useRouter()

  const handleTabClick = (path: string) => {
    if (pathname === path) {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } else {
      router.push(path)
    }
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-[800] bg-bg/80 backdrop-blur-xl border-t border-border-default">
      <div className="max-w-lg mx-auto flex items-center justify-around h-[72px] px-4 pb-[env(safe-area-inset-bottom)]">
        {TABS.map((tab) => {
          const active = tab.path === '/'
            ? pathname === '/'
            : pathname.startsWith(tab.path)
          return (
            <button
              key={tab.key}
              onClick={() => handleTabClick(tab.path)}
              className="flex flex-col items-center gap-1 py-1 px-3 transition-all duration-200"
            >
              {tab.icon(active)}
              <span
                className={`text-[10px] font-medium transition-colors duration-200 ${
                  active ? 'text-accent' : 'text-text-tertiary'
                }`}
              >
                {tab.label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
