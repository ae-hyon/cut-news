import React from 'react'
import type { PreferenceMode } from '../../lib/types'
import { formatDateLabel } from '../../lib/dateLabel'

interface IntroScreenProps {
  loading: boolean
  mode: PreferenceMode
  onSelectMode: (mode: PreferenceMode) => void
  onContinue: () => void
}

export default function IntroScreen({ loading, mode, onSelectMode, onContinue }: IntroScreenProps) {
  return (
    <section className="screen intro-screen pdf-intro">
      <header className="pdf-topbar intro-topbar">
        <div className="brand-block static">
          <strong>Annoying Cap</strong>
          <span>{formatDateLabel()}</span>
        </div>
        <div className="pdf-nav"><span>스크랩</span><span>|</span><span>아카이브</span></div>
      </header>

      <h1 className="pdf-question">관심있는 분야를 최소 3개 이상 선택해서<br />하루에 한번씩 요약해서 받아보세요</h1>

      <div className="pdf-progress-row">
        <span>관심사 설정</span>
        <span>다됐어요!</span>
      </div>

      <div className="choice-grid pdf-choice-grid">
        <button className={mode === 'wide' ? 'choice-card pdf-choice-card active' : 'choice-card pdf-choice-card'} onClick={() => onSelectMode('wide')}>
          <strong>넓게 볼랭</strong>
          <span>다양한 대분류를 최대 5개까지 골라요</span>
        </button>
        <button className={mode === 'narrow' ? 'choice-card pdf-choice-card active' : 'choice-card pdf-choice-card'} onClick={() => onSelectMode('narrow')}>
          <strong>깊게 볼랭</strong>
          <span>대분류 하나를 고르고 소분류를 여러 개 골라요</span>
        </button>
      </div>

      <button className="primary-cta pdf-bottom-cta" onClick={onContinue} disabled={loading}>다음</button>
    </section>
  )
}
