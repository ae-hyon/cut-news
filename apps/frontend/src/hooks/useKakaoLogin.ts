'use client';

import { useState, useCallback } from 'react';
import { getKakaoStart } from '@/services/authApi';
import { getErrorMessage } from '@/lib/api';

export type KakaoLoginStatus = 'idle' | 'waiting' | 'error';

export function useKakaoLogin() {
  const [status, setStatus] = useState<KakaoLoginStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const startLogin = useCallback(async () => {
    try {
      setStatus('waiting');
      setError(null);
      const { authorization_url } = await getKakaoStart();
      window.location.href = authorization_url;
    } catch (err) {
      setStatus('error');
      setError(getErrorMessage(err));
    }
  }, []);

  return {
    startLogin,
    status,
    error,
    isLoading: status === 'waiting',
  };
}
