'use client';

import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import { useOnboardingStore } from '@/stores/onboarding';
import { useCategories } from '@/hooks/useCategories';

export default function OnboardingNarrowSub() {
  const router = useRouter();
  const { narrowMainCategory, selectedSubCategories, toggleSubCategory } =
    useOnboardingStore();
  const { categories, isLoading, error, refetch } = useCategories();

  const mainCat = categories.find((c) => c.id === narrowMainCategory);
  const subs = mainCat?.subcategories ?? [];

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-white/60 text-[14px]">카테고리를 불러오는 중...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3">
        <p className="text-white/60 text-[14px]">카테고리를 불러올 수 없어요</p>
        <button
          onClick={refetch}
          className="text-[#f3782b] text-[14px] font-medium"
        >
          다시 시도
        </button>
      </div>
    );
  }

  if (!mainCat) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-text-secondary">먼저 대카테고리를 선택해주세요</p>
      </div>
    );
  }

  return (
    <>
      {/* Progress */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <p className="text-text-secondary text-sm mb-1">2 / 3</p>
        <h1 className="font-[family-name:var(--font-display)] text-xl font-bold">
          <span className="text-accent">{mainCat.name}</span>에서
          <br />
          세부 관심사를 골라주세요
        </h1>
        <p className="text-text-secondary text-sm mt-2">
          여러 개 선택할 수 있어요
        </p>
      </motion.div>

      {/* Sub-category chips */}
      <div className="flex-1 overflow-y-auto">
        <div className="flex flex-wrap gap-3">
          {subs.map((sub, i) => {
            const selected = selectedSubCategories.includes(sub.id);
            return (
              <motion.button
                key={sub.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.25, delay: i * 0.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => toggleSubCategory(sub.id)}
                className={`px-5 py-3 rounded-full border text-sm font-medium transition-all duration-200 ${
                  selected
                    ? 'border-accent bg-accent text-bg'
                    : 'border-border-default bg-bg-elevated text-text-secondary hover:border-text-tertiary'
                }`}
              >
                {sub.name}
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* Navigation */}
      <div className="mt-8 pb-4 flex gap-3">
        <button
          onClick={() => router.push('/onboarding/narrow')}
          className="flex-1 py-4 rounded-lg text-base font-bold border border-border-default bg-bg-elevated text-text-secondary hover:border-text-tertiary transition-all"
        >
          이전
        </button>
        <button
          onClick={() => router.push('/onboarding/complete')}
          disabled={selectedSubCategories.length === 0}
          className="flex-[2] py-4 rounded-lg text-base font-bold transition-all duration-200
            bg-accent text-bg hover:bg-accent-hover
            disabled:bg-bg-elevated disabled:text-text-tertiary disabled:cursor-not-allowed"
        >
          다음
        </button>
      </div>
    </>
  );
}
