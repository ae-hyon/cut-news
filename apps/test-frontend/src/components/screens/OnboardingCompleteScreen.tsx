import React from 'react'
import type { PreferenceMode, UserPreference } from '../../lib/types'
import type { Category } from '../../lib/types'
import { formatPreferenceSummary } from '../../lib/preferenceLabels'
import { formatDateLabel } from '../../lib/dateLabel'

interface OnboardingCompleteScreenProps {
  loading: boolean
  mode: PreferenceMode
  preference: UserPreference | null
  categories: Category[]
  onEditMode: () => void
  onEditSelection: () => void
  onBeginKakaoLogin: () => void
  onStartDemo?: () => void
  showDevDemoEntry?: boolean
}

export default function OnboardingCompleteScreen({ loading, mode, preference, categories, onEditMode, onEditSelection, onBeginKakaoLogin, onStartDemo, showDevDemoEntry = false }: OnboardingCompleteScreenProps) {
  const summaryChip = formatPreferenceSummary(mode, preference, categories)

  return (
    <section className="screen onboarding-complete-screen pdf-intro">
      <header className="pdf-topbar intro-topbar">
        <div className="brand-block static">
          <strong>Annoying Cap</strong>
          <span>{formatDateLabel()}</span>
        </div>
        <div className="pdf-nav"><span>스크랩</span></div>
      </header>

      <h1 className="pdf-question complete-question">관심있는 분야를 최소 3개 이상 선택해서<br />하루에 한번씩 요약해서 받아보세요</h1>

      <div className="pdf-progress-row complete-progress-row">
        <span>3번째</span>
        <span>완료!</span>
      </div>

      <div className="complete-chip-stack">
        <button className="chip static-chip" onClick={onEditMode}>{mode === 'wide' ? 'Wide 유저' : 'Narrow 유저'}</button>
        {!!summaryChip && <button className="chip static-chip" onClick={onEditSelection}>{summaryChip}</button>}
      </div>

      {showDevDemoEntry && !!onStartDemo && (
        <button className="secondary-cta pdf-bottom-cta" onClick={onStartDemo} disabled={loading}>로컬 데모 피드로 바로 보기</button>
      )}
      <button className="primary-cta pdf-bottom-cta" onClick={onBeginKakaoLogin} disabled={loading}>카카오 로그인하고 매일 블록 받아보기</button>
    </section>
  )
}
