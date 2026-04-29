import React from 'react'
import { getErrorMessage } from '../lib/api'
import { DEMO_USER_ID } from '../lib/constants'
import { clearRememberedDemoUserId, getRememberedDemoUserId, rememberDemoUserId } from '../lib/devSession'
import type { ArticleCard, ArticleDetail, UserPreference } from '../lib/types'
import { getUserPreference, saveUserPreference } from '../services/backendApi'
import { useArchiveState } from './useArchiveState'
import { useAuthSession } from './useAuthSession'
import { useContentFeed } from './useContentFeed'
import { usePreferenceSelection } from './usePreferenceSelection'
import { useViewState } from './useViewState'

export type { NarrowStep, SubcategoryMap } from './usePreferenceSelection'
export type { AppTab } from './useViewState'

export function usePrototypeApp() {
  const auth = useAuthSession()
  const content = useContentFeed()
  const archive = useArchiveState()
  const view = useViewState()
  const preferenceSelection = usePreferenceSelection(auth.categories)

  const [preference, setPreference] = React.useState<UserPreference | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState('')

  const runWithLoading = React.useCallback(async (task: () => Promise<void>) => {
    setLoading(true)
    setError('')
    try {
      await task()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  const closeArticle = React.useCallback(() => {
    content.setSelectedArticle(null)
    view.closeDetail()
  }, [content.setSelectedArticle, view.closeDetail])

  const loadUserState = React.useCallback(async (nextUserId: string) => {
    let [sessionData, pref] = await Promise.all([
      auth.loadUserSession(nextUserId),
      getUserPreference(nextUserId),
    ])

    const canCarryCompletedPreference =
      preference?.onboarding_completed &&
      nextUserId !== preference.user_id &&
      (!pref.onboarding_completed || !sessionData.onboarding_completed)

    if (canCarryCompletedPreference) {
      await saveUserPreference(nextUserId, {
        mode: preference.mode,
        primary_categories: preference.primary_categories,
        subcategories: preference.subcategories,
      })
      ;[sessionData, pref] = await Promise.all([
        auth.loadUserSession(nextUserId),
        getUserPreference(nextUserId),
      ])
    }

    auth.setUserId(nextUserId)
    auth.setSession({
      ...sessionData,
      onboarding_completed: pref.onboarding_completed,
      session_state: pref.onboarding_completed ? 'onboarded' : sessionData.session_state,
    })
    setPreference(pref)
    preferenceSelection.hydratePreferenceState(pref)

    if (!pref.onboarding_completed) {
      content.clearContent()
      archive.clearArchive()
      view.resetToOnboarding()
      return
    }

    const { feed } = await content.loadContent(nextUserId)
    await archive.loadArchiveForFirstFeedDate(nextUserId, feed)
    view.resetToHome()
  }, [
    archive.clearArchive,
    archive.loadArchiveForFirstFeedDate,
    auth.loadUserSession,
    auth.setUserId,
    content.clearContent,
    content.loadContent,
    preference,
    preferenceSelection.hydratePreferenceState,
    view.resetToHome,
    view.resetToOnboarding,
  ])

  const loadBootstrap = React.useCallback(async () => {
    await runWithLoading(async () => {
      const bootstrap = await auth.loadBootstrap()
      if (bootstrap.session.user_id) {
        await loadUserState(bootstrap.session.user_id)
        return
      }

      const rememberedDemoUserId = getRememberedDemoUserId()
      if (rememberedDemoUserId) {
        await loadUserState(rememberedDemoUserId)
      }
    })
  }, [auth.loadBootstrap, loadUserState, runWithLoading])

  React.useEffect(() => {
    void loadBootstrap()
  }, [loadBootstrap])

  const startDemo = React.useCallback(async () => {
    await runWithLoading(async () => {
      rememberDemoUserId(DEMO_USER_ID)
      await loadUserState(DEMO_USER_ID)
    })
  }, [loadUserState, runWithLoading])

  const startPreferenceFlow = React.useCallback(async () => {
    await runWithLoading(async () => {
      auth.setUserId(DEMO_USER_ID)
      auth.setSession({
        user_id: DEMO_USER_ID,
        session_state: 'authenticated',
        onboarding_completed: false,
        authenticated: true,
        auth_provider: 'demo',
      })
      setPreference({
        user_id: DEMO_USER_ID,
        mode: preferenceSelection.mode,
        primary_categories: preferenceSelection.mode === 'wide' ? preferenceSelection.selectedCategories : [],
        subcategories: [],
        onboarding_completed: false,
      })
      content.clearContent()
      archive.clearArchive()
      content.setSelectedArticle(null)
      view.resetToOnboarding()
    })
  }, [
    archive.clearArchive,
    auth,
    content.clearContent,
    content.setSelectedArticle,
    preferenceSelection.mode,
    preferenceSelection.selectedCategories,
    view.resetToOnboarding,
  ])

  const restartIntroFlow = React.useCallback(() => {
    clearRememberedDemoUserId()
    auth.setUserId(null)
    auth.setSession(null)
    setPreference(null)
    content.clearContent()
    content.setSelectedArticle(null)
    archive.clearArchive()
    view.resetToHome()
  }, [archive.clearArchive, auth, content.clearContent, content.setSelectedArticle, view.resetToHome])

  const refreshCurrentState = React.useCallback(async () => {
    if (!auth.userId) return
    await runWithLoading(async () => {
      await loadUserState(auth.userId as string)
    })
  }, [auth.userId, loadUserState, runWithLoading])

  const checkKakaoSession = React.useCallback(async (silent = false) => {
    await runWithLoading(async () => {
      await auth.checkKakaoSession({
        silent,
        onAuthenticated: async (nextUserId) => {
          await loadUserState(nextUserId)
        },
      })
    })
  }, [auth.checkKakaoSession, loadUserState, runWithLoading])

  React.useEffect(() => {
    const handleKakaoMessage = (event: MessageEvent) => {
      if (event.data?.type !== 'annoyingcap:kakao-authenticated') return
      if (event.data.userId) {
        void loadUserState(event.data.userId)
        return
      }
      void checkKakaoSession(true)
    }

    window.addEventListener('message', handleKakaoMessage)
    return () => window.removeEventListener('message', handleKakaoMessage)
  }, [checkKakaoSession, loadUserState])

  React.useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search)
    if (searchParams.get('auth') !== 'kakao') return

    window.history.replaceState({}, document.title, window.location.pathname)
    void checkKakaoSession(true)
  }, [checkKakaoSession])

  React.useEffect(() => {
    if (!auth.kakaoAuthPending) return undefined

    let lastCheckAt = 0
    const maybeCheckSession = () => {
      const now = Date.now()
      if (document.visibilityState !== 'visible') return
      if (now - lastCheckAt < 1200) return
      lastCheckAt = now
      void checkKakaoSession(true)
    }

    window.addEventListener('focus', maybeCheckSession)
    document.addEventListener('visibilitychange', maybeCheckSession)
    return () => {
      window.removeEventListener('focus', maybeCheckSession)
      document.removeEventListener('visibilitychange', maybeCheckSession)
    }
  }, [auth.kakaoAuthPending, checkKakaoSession])

  const submitPreferences = React.useCallback(async () => {
    if (!auth.userId || !preferenceSelection.isSelectionValid) return
    await runWithLoading(async () => {
      await saveUserPreference(auth.userId as string, preferenceSelection.toPreferencePayload())
      if (auth.userId === DEMO_USER_ID) rememberDemoUserId(auth.userId)
      const pref = await getUserPreference(auth.userId as string)
      setPreference(pref)
      preferenceSelection.hydratePreferenceState(pref)
      auth.setSession((prev) => prev ? { ...prev, onboarding_completed: true } : prev)
      view.resetToOnboardingComplete()
    })
  }, [auth, preferenceSelection, runWithLoading, view.resetToOnboardingComplete])

  const openArticle = React.useCallback(async (articleId: string) => {
    await runWithLoading(async () => {
      await content.openArticle(articleId, auth.userId)
      view.openDetail(articleId)
    })
  }, [auth.userId, content.openArticle, runWithLoading, view.openDetail])

  const toggleScrap = React.useCallback(async (article: ArticleCard | ArticleDetail) => {
    if (!auth.userId) return
    await runWithLoading(async () => {
      await content.toggleScrap(auth.userId as string, article)
      await loadUserState(auth.userId as string)
      if (content.selectedArticle?.id === article.id) {
        await content.refreshSelectedArticle(article.id, auth.userId)
        view.openDetail(article.id)
      }
    })
  }, [auth.userId, content.refreshSelectedArticle, content.selectedArticle?.id, content.toggleScrap, loadUserState, runWithLoading, view.openDetail])

  const loadArchiveMonth = React.useCallback(async (nextMonth: string) => {
    if (!auth.userId) return
    await runWithLoading(async () => {
      await archive.loadArchiveMonth(auth.userId as string, nextMonth)
    })
  }, [archive.loadArchiveMonth, auth.userId, runWithLoading])

  const openArchiveDate = React.useCallback(async (date: string) => {
    if (!auth.userId) return
    await runWithLoading(async () => {
      await archive.openArchiveDate(auth.userId as string, date)
    })
  }, [archive.openArchiveDate, auth.userId, runWithLoading])

  const closeArchiveDate = React.useCallback(() => {
    archive.closeArchiveDate()
  }, [archive.closeArchiveDate])

  const changeTab = React.useCallback((tab: typeof view.activeTab) => {
    content.setSelectedArticle(null)
    view.changeTab(tab)
  }, [content.setSelectedArticle, view.changeTab])

  const editCompletedPreferences = React.useCallback(() => {
    view.resetToOnboarding()
  }, [view.resetToOnboarding])

  const showOnboardingScreen = Boolean(auth.userId) && (!preference?.onboarding_completed || view.activeTab === 'onboarding')
  const showOnboardingCompleteScreen = Boolean(auth.userId) && Boolean(preference?.onboarding_completed) && view.activeTab === 'onboarding-complete'
  const readyForFeed = Boolean(auth.userId) && Boolean(preference?.onboarding_completed) && !showOnboardingCompleteScreen
  const selectedArticle = view.isDetailOpen ? content.selectedArticle : null

  return {
    health: auth.health,
    categories: auth.categories,
    session: auth.session,
    userId: auth.userId,
    preference,
    feed: content.feed,
    scraps: content.scraps,
    archiveMonth: archive.archiveMonth,
    archiveMonthData: archive.archiveMonthData,
    archiveDateData: archive.archiveDateData,
    selectedArticle,
    activeTab: view.activeTab,
    isDetailOpen: view.isDetailOpen,
    ...preferenceSelection,
    kakaoStart: auth.kakaoStart,
    authNotice: auth.authNotice,
    kakaoAuthStatus: auth.kakaoAuthStatus,
    kakaoAuthPending: auth.kakaoAuthPending,
    loading,
    error,
    archiveMonthOptions: [archive.archiveMonth],
    showOnboardingScreen,
    showOnboardingCompleteScreen,
    readyForFeed,
    loadBootstrap,
    startDemo,
    startPreferenceFlow,
    restartIntroFlow,
    refreshCurrentState,
    beginKakaoStart: auth.beginKakaoStart,
    checkKakaoSession,
    submitPreferences,
    editCompletedPreferences,
    openArticle,
    closeArticle,
    toggleScrap,
    loadArchiveMonth,
    openArchiveDate,
    closeArchiveDate,
    changeTab,
  }
}

export type PrototypeAppState = ReturnType<typeof usePrototypeApp>
