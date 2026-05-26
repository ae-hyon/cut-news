'use client';

import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import { useOnboardingStore } from '@/stores/onboarding';
import { MAX_WIDE_CATEGORIES } from '@/constants/categories';
import { useCategories } from '@/hooks/useCategories';
import { showToast } from '@/components/Toast';
import OnboardingHeader from '../_components/OnboardingHeader';
import OnboardingProgress from '../_components/OnboardingProgress';
import OnboardingGuide from '../_components/OnboardingGuide';

export default function OnboardingWide() {
  const router = useRouter();
  const { selectedCategories, toggleCategory } = useOnboardingStore();
  const { categories, isLoading, error, refetch } = useCategories();

  const handleToggle = (id: string) => {
    const success = toggleCategory(id);
    if (!success) {
      showToast(`대분류 ${MAX_WIDE_CATEGORIES}개까지만 선택 가능해요`);
    }
  };

  const canProceed = selectedCategories.length >= 3;

  return (
    <>
      <OnboardingHeader />

      <div className="flex flex-1 flex-col px-5 pt-6 pb-10">
        <div className="flex flex-col gap-6 pt-4">
          <OnboardingGuide />
          <OnboardingProgress step={2} label="2번째" rightLabel="다됐어요!" />

          {/* Category grid */}
          <div className="grid grid-cols-2 gap-2 py-4 overflow-y-auto flex-1">
            {isLoading && (
              <p className="col-span-2 text-center text-white/60 text-[14px] py-8">
                카테고리를 불러오는 중...
              </p>
            )}
            {error && (
              <div className="col-span-2 flex flex-col items-center gap-3 py-8">
                <p className="text-white/60 text-[14px]">
                  카테고리를 불러올 수 없어요
                </p>
                <button
                  onClick={refetch}
                  className="text-[#f3782b] text-[14px] font-medium"
                >
                  다시 시도
                </button>
              </div>
            )}
            {categories.map((cat, i) => {
              const selected = selectedCategories.includes(cat.id);
              return (
                <motion.button
                  key={cat.id}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.04 }}
                  whileTap={{ scale: 0.96 }}
                  onClick={() => handleToggle(cat.id)}
                  className={`flex flex-col gap-0.5 items-center justify-center h-[75px] rounded-[24px] px-1 py-[26px] text-center text-white overflow-hidden transition-all duration-200 ${
                    selected
                      ? 'bg-[#f3782b]'
                      : 'bg-[#3c3c3c] border border-[#343434]'
                  }`}
                >
                  <p className="font-bold text-[16px] leading-[19px] w-full">
                    {cat.name}
                  </p>
                  <p className="font-normal text-[12px] leading-[14px] w-full">
                    {cat.description}
                  </p>
                </motion.button>
              );
            })}
          </div>
        </div>

        {/* Navigation */}
        <div className="flex gap-3.5 mt-auto">
          <button
            onClick={() => router.push('/onboarding')}
            className="flex-1 py-5 rounded-[24px] text-[16px] font-bold text-[#f3782b] text-center border border-[#f3782b] bg-[#101010] transition-all"
          >
            이전
          </button>
          <button
            onClick={() => router.push('/onboarding/complete')}
            disabled={!canProceed}
            className={`flex-1 py-5 rounded-[24px] text-[16px] font-bold text-center text-white transition-all duration-200 ${
              canProceed
                ? 'bg-[#f3782b]'
                : 'bg-[#414141] opacity-50 cursor-not-allowed'
            }`}
          >
            {canProceed
              ? `${selectedCategories.length}개 선택 완료`
              : '3개 이상 선택'}
          </button>
        </div>
      </div>
    </>
  );
}
