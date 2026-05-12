import React from 'react'

export type AppTab = 'home' | 'onboarding' | 'onboarding-complete' | 'scraps'

interface ViewState {
  activeTab: AppTab
  detailArticleId: string | null
}

type ViewAction =
  | { type: 'GO_TAB'; tab: AppTab }
  | { type: 'OPEN_DETAIL'; articleId: string }
  | { type: 'CLOSE_DETAIL' }
  | { type: 'RESET_TO_HOME' }
  | { type: 'RESET_TO_ONBOARDING' }
  | { type: 'RESET_TO_ONBOARDING_COMPLETE' }

function viewReducer(state: ViewState, action: ViewAction): ViewState {
  switch (action.type) {
    case 'GO_TAB':
      return { activeTab: action.tab, detailArticleId: null }
    case 'OPEN_DETAIL':
      return { ...state, detailArticleId: action.articleId }
    case 'CLOSE_DETAIL':
      return { ...state, detailArticleId: null }
    case 'RESET_TO_HOME':
      return { activeTab: 'home', detailArticleId: null }
    case 'RESET_TO_ONBOARDING':
      return { activeTab: 'onboarding', detailArticleId: null }
    case 'RESET_TO_ONBOARDING_COMPLETE':
      return { activeTab: 'onboarding-complete', detailArticleId: null }
    default:
      return state
  }
}

export function useViewState() {
  const [view, dispatch] = React.useReducer(viewReducer, {
    activeTab: 'home',
    detailArticleId: null,
  })

  const changeTab = React.useCallback((tab: AppTab) => {
    dispatch({ type: 'GO_TAB', tab })
  }, [])

  const openDetail = React.useCallback((articleId: string) => {
    dispatch({ type: 'OPEN_DETAIL', articleId })
  }, [])

  const closeDetail = React.useCallback(() => {
    dispatch({ type: 'CLOSE_DETAIL' })
  }, [])

  const resetToHome = React.useCallback(() => {
    dispatch({ type: 'RESET_TO_HOME' })
  }, [])

  const resetToOnboarding = React.useCallback(() => {
    dispatch({ type: 'RESET_TO_ONBOARDING' })
  }, [])

  const resetToOnboardingComplete = React.useCallback(() => {
    dispatch({ type: 'RESET_TO_ONBOARDING_COMPLETE' })
  }, [])

  return {
    activeTab: view.activeTab,
    detailArticleId: view.detailArticleId,
    isDetailOpen: Boolean(view.detailArticleId),
    changeTab,
    openDetail,
    closeDetail,
    resetToHome,
    resetToOnboarding,
    resetToOnboardingComplete,
  }
}

export type ViewStateController = ReturnType<typeof useViewState>
