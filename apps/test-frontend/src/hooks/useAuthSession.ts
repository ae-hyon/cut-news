import React from 'react'
import { getErrorMessage } from '../lib/api'
import type { AuthSessionResponse, AuthStartResponse, Category, HealthResponse } from '../lib/types'
import { getAnonymousSession, getCategories, getHealth, getKakaoStart, getUserSession, postLogout } from '../services/backendApi'

export type KakaoAuthStatus = 'idle' | 'waiting' | 'checking' | 'confirmed' | 'not_found' | 'error'

interface CheckKakaoSessionOptions {
  onAuthenticated: (userId: string, session: AuthSessionResponse) => Promise<void>
  silent?: boolean
}

export function useAuthSession() {
  const [health, setHealth] = React.useState<HealthResponse | null>(null)
  const [categories, setCategories] = React.useState<Category[]>([])
  const [session, setSession] = React.useState<AuthSessionResponse | null>(null)
  const [userId, setUserId] = React.useState<string | null>(null)
  const [kakaoStart, setKakaoStart] = React.useState<AuthStartResponse | null>(null)
  const [authNotice, setAuthNotice] = React.useState('')
  const [kakaoAuthStatus, setKakaoAuthStatus] = React.useState<KakaoAuthStatus>('idle')


  const refreshAnonymousSession = React.useCallback(async () => {
    const data = await getAnonymousSession()
    setSession(data)
    if (data.user_id) setUserId(data.user_id)
    return data
  }, [])

  const loadUserSession = React.useCallback(async (nextUserId: string) => {
    const data = await getUserSession(nextUserId)
    setSession(data)
    setUserId(nextUserId)
    return data
  }, [])

  const loadBootstrap = React.useCallback(async () => {
    const [healthData, categoriesData, sessionData, kakaoData] = await Promise.all([
      getHealth(),
      getCategories(),
      refreshAnonymousSession(),
      getKakaoStart(),
    ])
    setHealth(healthData)
    setCategories(categoriesData)
    setSession(sessionData)
    setKakaoStart(kakaoData)
    if (sessionData.user_id) setUserId(sessionData.user_id)
    return { health: healthData, categories: categoriesData, session: sessionData, kakaoStart: kakaoData }
  }, [refreshAnonymousSession])

  const beginKakaoStart = React.useCallback(() => {
    if (!kakaoStart?.authorization_url) return
    setKakaoAuthStatus('waiting')
    window.location.href = kakaoStart.authorization_url
  }, [kakaoStart])

  const logout = React.useCallback(async () => {
    const result = await postLogout()
    setSession({
      user_id: null,
      session_state: 'anonymous',
      onboarding_completed: false,
      authenticated: false,
      auth_provider: 'none',
      provider_subject: null,
    })
    setUserId(null)
    setKakaoAuthStatus('idle')
    setAuthNotice('로그아웃했어요. 다른 사용자로 다시 테스트할 수 있어요.')
    return result
  }, [])

  const checkKakaoSession = React.useCallback(async ({ onAuthenticated, silent = false }: CheckKakaoSessionOptions) => {
    try {
      setKakaoAuthStatus('checking')
      if (!silent) setAuthNotice('로그인 상태를 확인하고 있어요.')
      const sessionData = await refreshAnonymousSession()
      if (sessionData.user_id) {
        await onAuthenticated(sessionData.user_id, sessionData)
        setKakaoAuthStatus('confirmed')
        setAuthNotice(sessionData.onboarding_completed ? '로그인이 확인됐어요. 홈 피드로 이동합니다.' : '로그인이 확인됐어요. 관심사를 먼저 골라주세요.')
        return sessionData
      }
      setKakaoAuthStatus('not_found')
      if (!silent) setAuthNotice('아직 로그인 세션을 찾지 못했어요. 카카오 인증을 마친 뒤 다시 확인해주세요.')
      return sessionData
    } catch (err) {
      setKakaoAuthStatus('error')
      setAuthNotice(getErrorMessage(err))
      throw err
    }
  }, [refreshAnonymousSession])

  React.useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search)
    if (searchParams.get('auth') !== 'kakao') return

    const handleCallback = async () => {
      try {
        setKakaoAuthStatus('checking')
        const sessionData = await getAnonymousSession()
        setSession(sessionData)
        if (sessionData.user_id) {
          setUserId(sessionData.user_id)
          setKakaoAuthStatus('confirmed')
          setAuthNotice(sessionData.onboarding_completed ? '로그인이 확인됐어요.' : '로그인이 확인됐어요. 관심사를 먼저 골라주세요.')
        } else {
          setKakaoAuthStatus('not_found')
          setAuthNotice('로그인 세션을 찾지 못했어요. 다시 시도해주세요.')
        }
      } catch (err) {
        setKakaoAuthStatus('error')
        setAuthNotice(getErrorMessage(err))
      }
    }

    void handleCallback()
  }, [])

  return {
    health,
    categories,
    session,
    userId,
    kakaoStart,
    authNotice,
    kakaoAuthStatus,
    kakaoAuthPending: kakaoAuthStatus === 'waiting' || kakaoAuthStatus === 'checking' || kakaoAuthStatus === 'not_found',
    setSession,
    setUserId,
    setAuthNotice,
    loadBootstrap,
    loadUserSession,
    refreshAnonymousSession,
    beginKakaoStart,
    logout,
    checkKakaoSession,
  }
}

export type AuthSessionState = ReturnType<typeof useAuthSession>
