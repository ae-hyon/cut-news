'use client'

import { useEffect } from 'react'
import { getSession } from '@/services/authApi'

export default function KakaoCallbackHandler() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('auth') !== 'kakao') return
    if (!window.opener || window.opener.closed) return

    const notifyOpener = async () => {
      const session = await getSession()
      window.opener.postMessage(
        { type: 'annoyingcap:kakao-authenticated', userId: session.user_id },
        '*'
      )
      window.close()
    }
    void notifyOpener()
  }, [])

  return null
}
