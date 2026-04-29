import React from 'react'
import { usePrototypeApp } from './hooks/usePrototypeApp'
import AppShell from './components/layout/AppShell'
import TopBar from './components/layout/TopBar'
import DevPanel from './components/common/DevPanel'
import IntroScreen from './components/screens/IntroScreen'
import { isDevDemoEntryEnabled } from './lib/devSession'
import OnboardingScreen from './components/screens/OnboardingScreen'
import OnboardingCompleteScreen from './components/screens/OnboardingCompleteScreen'
import HomeScreen from './components/screens/HomeScreen'
import DetailScreen from './components/screens/DetailScreen'
import ScrapsScreen from './components/screens/ScrapsScreen'
import ArchiveScreen from './components/screens/ArchiveScreen'

import type { AppTab } from './hooks/usePrototypeApp'
import type { ArticleDetail } from './lib/types'

interface ScreenLabelInput {
  selectedArticle: ArticleDetail | null
  activeTab: AppTab
  showOnboardingScreen: boolean
  readyForFeed: boolean
}

function getScreenLabel({ selectedArticle, activeTab, showOnboardingScreen, readyForFeed }: ScreenLabelInput): string {
  if (selectedArticle) return '뉴스 상세'
  if (activeTab === 'scraps') return '스크랩'
  if (activeTab === 'archive') return '아카이브'
  if (showOnboardingScreen) return '관심사'
  if (activeTab === 'onboarding-complete') return '온보딩 완료'
  if (readyForFeed) return '뉴스홈'
  return '시작 화면'
}

export default function App() {
  const app = usePrototypeApp()
  getScreenLabel(app)
  const searchParams = new URLSearchParams(window.location.search)
  const showDebug = searchParams.get('debug') === '1'
  const showDevDemoEntry = isDevDemoEntryEnabled(window.location.search)

  return (
    <AppShell error={app.error}>
      {!!app.userId && !app.isDetailOpen && app.activeTab !== 'onboarding' && app.activeTab !== 'onboarding-complete' && <TopBar activeTab={app.activeTab} onNavigate={app.changeTab} onProfileClick={app.editCompletedPreferences} profilePill="선우" />}

      {!app.userId ? (
        <IntroScreen
          loading={app.loading}
          mode={app.mode}
          onSelectMode={app.setMode}
          onContinue={app.startPreferenceFlow}
        />
      ) : app.selectedArticle ? (
        <DetailScreen
          article={app.selectedArticle}
          onBack={app.closeArticle}
          onToggleScrap={app.toggleScrap}
        />
      ) : app.showOnboardingScreen ? (
        <OnboardingScreen
          mode={app.mode}
          categories={app.categories}
          selectedCategories={app.selectedCategories}
          selectedPrimary={app.selectedPrimary}
          selectedSubs={app.selectedSubs}
          subcategoryMap={app.subcategoryMap}
          narrowStep={app.narrowStep}
          isSelectionValid={app.isSelectionValid}
          loading={app.loading}
          onToggleWideCategory={app.toggleWideCategory}
          onSetSelectedPrimary={app.setSelectedPrimary}
          onSetNarrowStep={app.setNarrowStep}
          onToggleSubcategory={app.toggleSubcategory}
          onBackToIntro={app.restartIntroFlow}
          onSubmit={app.submitPreferences}
        />
      ) : app.showOnboardingCompleteScreen ? (
        <OnboardingCompleteScreen
          loading={app.loading}
          mode={app.mode}
          preference={app.preference}
          categories={app.categories}
          onEditMode={app.restartIntroFlow}
          onEditSelection={app.editCompletedPreferences}
          onStartDemo={app.startDemo}
          showDevDemoEntry={showDevDemoEntry}
          onBeginKakaoLogin={app.beginKakaoStart}
        />
      ) : (
        <>
          {app.activeTab === 'home' && (
            <HomeScreen
              preference={app.preference}
              feed={app.feed}
              onOpenArticle={app.openArticle}
              onToggleScrap={app.toggleScrap}
              onEditPreference={app.editCompletedPreferences}
            />
          )}
          {app.activeTab === 'scraps' && (
            <ScrapsScreen
              scraps={app.scraps}
              onOpenArticle={app.openArticle}
              onToggleScrap={app.toggleScrap}
            />
          )}
          {app.activeTab === 'archive' && (
            <ArchiveScreen
              archiveMonth={app.archiveMonth}
              archiveMonthOptions={app.archiveMonthOptions}
              archiveMonthData={app.archiveMonthData}
              archiveDateData={app.archiveDateData}
              onLoadArchiveMonth={app.loadArchiveMonth}
              onOpenArchiveDate={app.openArchiveDate}
              onCloseArchiveDate={app.closeArchiveDate}
              onOpenArticle={app.openArticle}
            />
          )}
        </>
      )}

      {showDebug && (
        <DevPanel
          health={app.health}
          session={app.session}
          userId={app.userId}
          loading={app.loading}
          onRefreshBootstrap={app.loadBootstrap}
          onStartDemo={app.startDemo}
          onRefreshCurrentState={app.refreshCurrentState}
        />
      )}
    </AppShell>
  )
}
