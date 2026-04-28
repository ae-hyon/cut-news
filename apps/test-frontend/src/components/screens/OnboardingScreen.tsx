import React from 'react'
import type { Category, PreferenceMode, Subcategory } from '../../lib/types'
import { getCategoryDescription, getSubcategoryDescription } from '../../lib/categoryDescriptions'
import { formatDateLabel } from '../../lib/dateLabel'
import type { NarrowStep, SubcategoryMap } from '../../hooks/usePrototypeApp'

type SelectorCardProps = {
  title: string
  description: string
  active: boolean
  onClick: () => void
}

function SelectorCard({ title, description, active, onClick }: SelectorCardProps) {
  return (
    <button className={active ? 'selector-card active' : 'selector-card'} onClick={onClick}>
      <strong>{title}</strong>
      <span>{description}</span>
    </button>
  )
}

interface WideSelectorProps {
  categories: Category[]
  selectedCategories: string[]
  onToggleWideCategory: (slug: string) => void
}

function WideSelector({ categories, selectedCategories, onToggleWideCategory }: WideSelectorProps) {
  return (
    <div className="selector-grid wide-selector-grid">
      {categories.map((category) => (
        <SelectorCard
          key={category.slug}
          title={category.name}
          description={getCategoryDescription(category)}
          active={selectedCategories.includes(category.slug)}
          onClick={() => onToggleWideCategory(category.slug)}
        />
      ))}
    </div>
  )
}

interface NarrowSelectorProps {
  categories: Category[]
  selectedPrimary: string
  selectedSubs: string[]
  subcategoryMap: SubcategoryMap
  narrowStep: NarrowStep
  onSetSelectedPrimary: (slug: string) => void
  onSetNarrowStep: (step: NarrowStep) => void
  onToggleSubcategory: (slug: string) => void
}

function NarrowSelector({ categories, selectedPrimary, selectedSubs, subcategoryMap, narrowStep, onSetSelectedPrimary, onSetNarrowStep, onToggleSubcategory }: NarrowSelectorProps) {
  const selectedPrimaryLabel = categories.find((category) => category.slug === selectedPrimary)?.name || '대분류 없음'
  const subcategories: Subcategory[] = subcategoryMap[selectedPrimary] || []

  if (narrowStep === 1) {
    return (
      <div className="selector-grid narrow-primary-grid">
        {categories.map((category) => (
          <SelectorCard
            key={category.slug}
            title={category.name}
            description={getCategoryDescription(category)}
            active={selectedPrimary === category.slug}
            onClick={() => onSetSelectedPrimary(category.slug)}
          />
        ))}
      </div>
    )
  }

  return (
    <>
      <div className="narrow-selected-primary">{selectedPrimaryLabel}</div>
      <div className="selector-grid narrow-secondary-grid">
        {subcategories.map((sub) => (
          <SelectorCard
            key={sub.slug}
            title={sub.name}
            description={getSubcategoryDescription(sub)}
            active={selectedSubs.includes(sub.slug)}
            onClick={() => onToggleSubcategory(sub.slug)}
          />
        ))}
      </div>
      <button className="back-link narrow-back-link" onClick={() => onSetNarrowStep(1)}>← 대분류 다시 고르기</button>
    </>
  )
}

interface OnboardingScreenProps {
  mode: PreferenceMode
  categories: Category[]
  selectedCategories: string[]
  selectedPrimary: string
  selectedSubs: string[]
  subcategoryMap: SubcategoryMap
  narrowStep: NarrowStep
  isSelectionValid: boolean
  loading: boolean
  onToggleWideCategory: (slug: string) => void
  onSetSelectedPrimary: (slug: string) => void
  onSetNarrowStep: (step: NarrowStep) => void
  onToggleSubcategory: (slug: string) => void
  onBackToIntro: () => void
  onSubmit: () => void
}

export default function OnboardingScreen(props: OnboardingScreenProps) {
  const {
    mode, categories, selectedCategories, selectedPrimary, selectedSubs, subcategoryMap,
    narrowStep, isSelectionValid, loading, onToggleWideCategory, onSetSelectedPrimary,
    onSetNarrowStep, onToggleSubcategory, onBackToIntro, onSubmit,
  } = props

  const isWide = mode === 'wide'
  const stepLeft = '2번째'
  const stepRight = isWide ? '다됐어요!' : narrowStep === 1 ? '대분류' : '소분류'
  const title = isWide ? '관심있는 분야를 최소 3개 이상 선택해서' : '집중해서 볼 분야를 하나 고르고'
  const subtitle = isWide ? '하루에 한번씩 요약해서 받아보세요' : narrowStep === 1 ? '세부 관심사까지 이어서 골라보세요' : '원하는 소분류를 여러 개 골라보세요'
  const note = isWide
    ? `${selectedCategories.length}/5 선택`
    : narrowStep === 1
      ? (selectedPrimary ? `${categories.find((c) => c.slug === selectedPrimary)?.name} 선택됨` : '대분류 1개를 골라주세요')
      : `소분류 ${selectedSubs.length}개 선택됨`
  const submitLabel = isWide ? `${Math.max(selectedCategories.length, 3)}개 선택 완료` : narrowStep === 1 ? '소분류 고르기' : '다음'
  const primaryButtonDisabled = loading || (isWide ? !isSelectionValid : narrowStep === 1 ? !selectedPrimary : !isSelectionValid)

  return (
    <section className="screen onboarding-screen pdf-intro">
      <header className="pdf-topbar intro-topbar onboarding-topbar">
        <div className="brand-block static">
          <strong>Annoying Cap</strong>
          <span>{formatDateLabel()}</span>
        </div>
        <div className="pdf-nav"><span>스크랩</span><span>|</span><span>아카이브</span></div>
      </header>

      <h1 className="pdf-question onboarding-question">{title}<br />{subtitle}</h1>

      <div className="pdf-progress-row onboarding-progress-row">
        <span>{stepLeft}</span>
        <span>{stepRight}</span>
      </div>
      <div className="onboarding-progress-bar">
        <div className={isWide ? 'onboarding-progress-fill wide' : narrowStep === 1 ? 'onboarding-progress-fill narrow-step-one' : 'onboarding-progress-fill narrow-step-two'} />
      </div>

      {isWide ? (
        <WideSelector categories={categories} selectedCategories={selectedCategories} onToggleWideCategory={onToggleWideCategory} />
      ) : (
        <NarrowSelector
          categories={categories}
          selectedPrimary={selectedPrimary}
          selectedSubs={selectedSubs}
          subcategoryMap={subcategoryMap}
          narrowStep={narrowStep}
          onSetSelectedPrimary={onSetSelectedPrimary}
          onSetNarrowStep={onSetNarrowStep}
          onToggleSubcategory={onToggleSubcategory}
        />
      )}

      <div className="onboarding-footer pdf-flow-footer">
        <div className="selection-note pdf-flow-note">{note}</div>
        <div className="onboarding-actions-row">
          <button className="secondary-cta" onClick={isWide || narrowStep === 1 ? onBackToIntro : () => onSetNarrowStep(1)}>이전</button>
          <button className="primary-cta" onClick={isWide ? onSubmit : narrowStep === 1 ? () => onSetNarrowStep(2) : onSubmit} disabled={primaryButtonDisabled}>{submitLabel}</button>
        </div>
      </div>
    </section>
  )
}
