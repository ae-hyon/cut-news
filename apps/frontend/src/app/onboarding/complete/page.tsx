'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import { useOnboardingStore } from '@/stores/onboarding';
import { useKakaoLogin } from '@/hooks/useKakaoLogin';
import { saveUserPreference } from '@/services/authApi';
import { CATEGORIES } from '@/constants/categories';
import { showToast } from '@/components/Toast';
import type { PreferenceMode } from '@/lib/types';
import OnboardingHeader from '../_components/OnboardingHeader';
import OnboardingProgress from '../_components/OnboardingProgress';

export default function OnboardingComplete() {
  const router = useRouter();
  const {
    userType,
    selectedCategories,
    narrowMainCategory,
    selectedSubCategories,
  } = useOnboardingStore();

  const isWide = userType === 'wide';

  const handleLoginSuccess = useCallback(
    async (userId: string) => {
      try {
        const payload = {
          mode: (userType ?? 'wide') as PreferenceMode,
          primary_categories: isWide
            ? selectedCategories
            : narrowMainCategory
              ? [narrowMainCategory]
              : [],
          subcategories: isWide ? [] : selectedSubCategories,
        };
        await saveUserPreference(userId, payload);
        router.push('/');
      } catch {
        showToast('설정 저장에 실패했어요. 다시 시도해주세요.');
      }
    },
    [
      userType,
      isWide,
      selectedCategories,
      narrowMainCategory,
      selectedSubCategories,
      router,
    ],
  );

  const { startLogin, status, error, isLoading } = useKakaoLogin({
    onSuccess: handleLoginSuccess,
  });

  const selectedNames = isWide
    ? selectedCategories.map(
        (id) => CATEGORIES.find((c) => c.id === id)?.name ?? id,
      )
    : (() => {
        const main = CATEGORIES.find((c) => c.id === narrowMainCategory);
        if (!main) return [];
        const subNames = selectedSubCategories.map(
          (id) => main.subcategories?.find((s) => s.id === id)?.name ?? id,
        );
        return [main.name, ...subNames];
      })();

  const editRoute = isWide ? '/onboarding/wide' : '/onboarding/narrow';

  return (
    <>
      <OnboardingHeader />

      <div className="flex flex-1 flex-col px-5 pt-6 pb-10">
        <div className="flex flex-col gap-6 pt-4">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="text-center text-[20px] font-semibold text-white leading-[32px] w-full"
          >
            <p>선택이 완료되었어요!</p>
            <p>로그인하고 매일 뉴스를 받아보세요</p>
          </motion.div>

          <OnboardingProgress step={3} label="완료!" rightLabel="🎉" />

          {/* Selected categories summary */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="flex flex-col gap-3 py-4"
          >
            <p className="text-[14px] text-white/60 text-center">
              {isWide
                ? '선택한 관심 분야'
                : `${CATEGORIES.find((c) => c.id === narrowMainCategory)?.name} 세부 관심사`}
            </p>

            <div className="flex flex-wrap gap-2 justify-center">
              {selectedNames.map((name, i) => (
                <motion.button
                  key={name}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.3 + i * 0.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => router.push(editRoute)}
                  className="px-4 py-2 rounded-full border border-[#f3782b] bg-[#f3782b]/15 text-[#f3782b] text-[14px] font-medium transition-all duration-200 hover:bg-[#f3782b] hover:text-white"
                >
                  {name}
                </motion.button>
              ))}
            </div>

            <p className="text-[12px] text-white/40 text-center mt-1">
              태그를 탭하면 수정할 수 있어요
            </p>
          </motion.div>
        </div>

        <div className="flex-1" />

        {/* Error message */}
        {error && status === 'error' && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-red-400 text-[14px] text-center mb-4"
          >
            {error}
          </motion.p>
        )}

        {/* Kakao Login CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="flex gap-3.5"
        >
          <button
            onClick={() => router.push(editRoute)}
            className="flex-shrink-0 py-5 px-6 rounded-[24px] text-[16px] font-bold text-[#f3782b] text-center border border-[#f3782b] bg-[#101010] transition-all"
          >
            이전
          </button>
          <button
            onClick={startLogin}
            disabled={isLoading}
            className="flex-1 py-5 rounded-[24px] text-[16px] font-bold bg-[#FEE500] text-[#191919] transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <span>로그인 중...</span>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M9 0.6C4.029 0.6 0 3.713 0 7.551c0 2.467 1.639 4.633 4.104 5.862l-1.04 3.858c-.09.334.291.6.564.395l4.624-3.074c.247.02.498.03.748.03 4.971 0 9-3.113 9-6.951S13.971.6 9 .6z"
                    fill="#191919"
                  />
                </svg>
                카카오 로그인
              </>
            )}
          </button>
        </motion.div>
      </div>
    </>
  );
}
