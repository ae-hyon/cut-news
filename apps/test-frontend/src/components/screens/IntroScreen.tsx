import React from 'react'
import type { PreferenceMode } from '../../lib/types'
import { formatDateLabel } from '../../lib/dateLabel'

interface IntroScreenProps {
  loading: boolean
  mode: PreferenceMode
  onSelectMode: (mode: PreferenceMode) => void
  onContinue: () => void
  onBeginKakaoLogin?: () => void
}

export default function IntroScreen({ loading, mode, onSelectMode, onContinue, onBeginKakaoLogin }: IntroScreenProps) {
  return (
    <section className="screen intro-screen pdf-intro">
      <header className="pdf-topbar intro-topbar">
        <div className="brand-block static">
          <strong>Annoying Cap</strong>
          <span>{formatDateLabel()}</span>
        </div>
        <div className="pdf-nav"><span>스크랩</span></div>
      </header>

      <h1 className="pdf-question">관심있는 분야를 최소 3개 이상 선택해서<br />하루에 한번씩 요약해서 받아보세요</h1>
      <p className="screen-helper-text intro-helper-text">처음 쓰는 분은 관심사부터 고르고, 기존 사용자는 바로 카카오 로그인으로 이어서 볼 수 있어요.</p>

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

      <button className="primary-cta pdf-bottom-cta" onClick={onContinue} disabled={loading}>처음 쓰는 분: 관심사 고르기</button>
      <button className="secondary-cta intro-returning-cta" onClick={onBeginKakaoLogin} disabled={loading || !onBeginKakaoLogin}>기존 사용자는 카카오 로그인</button>
    </section>
  )
}
