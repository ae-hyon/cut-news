'use client'

import { useState, useCallback, useEffect } from 'react'
import { getKakaoStart } from '@/services/authApi'
import { useAuthStore } from '@/stores/auth'
import { getErrorMessage } from '@/lib/api'

export type KakaoLoginStatus = 'idle' | 'waiting' | 'checking' | 'confirmed' | 'error'

interface UseKakaoLoginOptions {
  onSuccess?: (userId: string) => void
}

export function useKakaoLogin({ onSuccess }: UseKakaoLoginOptions = {}) {
  const [status, setStatus] = useState<KakaoLoginStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const checkSession = useAuthStore((s) => s.checkSession)

  const startLogin = useCallback(async () => {
    try {
      setStatus('waiting')
      setError(null)
      const { authorization_url } = await getKakaoStart()
      window.location.href = authorization_url
    } catch (err) {
      setStatus('error')
      setError(getErrorMessage(err))
    }
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('auth') !== 'kakao') return

    const handleCallback = async () => {
      try {
        setStatus('checking')
        const session = await checkSession()
        if (session.user_id) {
          setStatus('confirmed')
          onSuccess?.(session.user_id)
        } else {
          setStatus('error')
          setError('로그인 세션을 찾지 못했어요. 다시 시도해주세요.')
        }
      } catch (err) {
        setStatus('error')
        setError(getErrorMessage(err))
      }
    }
    void handleCallback()
  }, [checkSession, onSuccess])

  return { startLogin, status, error, isLoading: status === 'waiting' || status === 'checking' }
}
