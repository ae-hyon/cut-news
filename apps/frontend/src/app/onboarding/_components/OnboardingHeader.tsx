'use client';

import { useEffect } from 'react';
import Image from 'next/image';
import { motion } from 'motion/react';
import { showToast } from '@/components/Toast';
import { useKakaoLogin } from '@/hooks/useKakaoLogin';

export default function OnboardingHeader() {
  const { startLogin, error, isLoading } = useKakaoLogin({
    handleCallback: false,
  });

  useEffect(() => {
    if (error) showToast(error);
  }, [error]);

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="flex items-center justify-between px-3 py-4"
    >
      <div className="flex items-center gap-5">
        <Image
          src="/logo.png"
          alt="Annoying Cap"
          width={102}
          height={46}
          className="object-contain h-auto"
          priority
        />
        <div className="flex items-center gap-2 text-[16px] font-medium text-white/80 px-1">
          <span>스크랩</span>
          <span>아카이브</span>
        </div>
      </div>
      <div className="px-1">
        <button
          type="button"
          onClick={startLogin}
          disabled={isLoading}
          className="text-[14px] font-bold text-white underline disabled:opacity-60"
        >
          {isLoading ? '로그인 중...' : '로그인'}
        </button>
      </div>
    </motion.div>
  );
}
