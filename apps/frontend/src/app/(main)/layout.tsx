'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/Header';
import TabBar from '@/components/TabBar';
import Toast from '@/components/Toast';
import { useAuthStore } from '@/stores/auth';

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { session, userId, isLoading, checkSession } = useAuthStore();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    checkSession()
      .then((s) => {
        if (!s.authenticated) {
          router.replace('/onboarding');
        } else if (!s.onboarding_completed) {
          router.replace('/onboarding');
        } else {
          setReady(true);
        }
      })
      .catch(() => {
        // 백엔드 미실행 시 mock 모드로 진행
        setReady(true);
      });
  }, [checkSession, router]);

  if (!ready || isLoading) {
    return (
      <div className="min-h-dvh flex items-center justify-center">
        <div className="text-text-tertiary text-sm animate-pulse">
          로딩 중...
        </div>
      </div>
    );
  }

  const userName = session?.provider_subject ? undefined : undefined;
  // TODO: 유저 닉네임은 향후 프로필 API에서 가져올 예정

  return (
    <div className="min-h-dvh flex flex-col max-w-lg mx-auto">
      <Toast />
      <Header userName={userId ? '사용자' : undefined} />
      <main className="flex-1 pb-[72px]">{children}</main>
      <TabBar />
    </div>
  );
}
