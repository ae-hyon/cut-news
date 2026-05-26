'use client';

import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'motion/react';
import { useOnboardingStore } from '@/stores/onboarding';
import { useCategories } from '@/hooks/useCategories';
import type { Category } from '@/types';
import OnboardingHeader from '../_components/OnboardingHeader';
import OnboardingProgress from '../_components/OnboardingProgress';
import OnboardingGuide from '../_components/OnboardingGuide';

export default function OnboardingNarrow() {
  const router = useRouter();
  const {
    narrowMainCategory,
    setNarrowMainCategory,
    selectedSubCategories,
    toggleSubCategory,
  } = useOnboardingStore();
  const { categories, isLoading, error, refetch } = useCategories();

  const selectedCat = categories.find((c) => c.id === narrowMainCategory);
  const subs = selectedCat?.subcategories ?? [];
  const canProceed =
    narrowMainCategory !== null && selectedSubCategories.length > 0;

  return (
    <>
      <OnboardingHeader />

      <div className="flex flex-1 flex-col px-5 pt-6 pb-10">
        <div className="flex flex-col gap-6 pt-4">
          <OnboardingGuide />
          <OnboardingProgress step={2} label="2번째" rightLabel="다됐어요!" />

          {/* Category list with inline sub-category expansion */}
          <div className="flex flex-col gap-2 py-4 overflow-y-auto flex-1">
            {isLoading && (
              <p className="text-center text-white/60 text-[14px] py-8">
                카테고리를 불러오는 중...
              </p>
            )}
            {error && (
              <div className="flex flex-col items-center gap-3 py-8">
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
            {(() => {
              const rows: React.ReactNode[] = [];
              for (let i = 0; i < categories.length; i += 2) {
                const cat1 = categories[i];
                const cat2 = categories[i + 1];
                const selected1 = narrowMainCategory === cat1.id;
                const selected2 = cat2 && narrowMainCategory === cat2.id;
                const showSubPanel = selected1 || selected2;

                rows.push(
                  <div key={`row-${i}`} className="flex gap-2">
                    <CategoryCard
                      cat={cat1}
                      selected={selected1}
                      onSelect={setNarrowMainCategory}
                      index={i}
                    />
                    {cat2 && (
                      <CategoryCard
                        cat={cat2}
                        selected={selected2}
                        onSelect={setNarrowMainCategory}
                        index={i + 1}
                      />
                    )}
                  </div>,
                );

                {
                  /* Sub-category panel below the row containing selected category */
                }
                if (showSubPanel && subs.length > 0) {
                  const selectedIdx = selected1 ? 0 : 1;
                  rows.push(
                    <AnimatePresence key={`sub-${narrowMainCategory}`}>
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.25 }}
                        className="py-4"
                      >
                        <div className="relative bg-white/10 rounded-[16px] p-4">
                          {/* Triangle pointer */}
                          <div
                            className="absolute -top-[10px] w-0 h-0"
                            style={{
                              left:
                                selectedIdx === 0 ? '32px' : 'calc(50% + 32px)',
                              borderLeft: '10px solid transparent',
                              borderRight: '10px solid transparent',
                              borderBottom: '10px solid rgba(255,255,255,0.1)',
                            }}
                          />
                          <div className="grid grid-cols-3 gap-2.5">
                            {subs.map((sub, si) => {
                              const subSelected =
                                selectedSubCategories.includes(sub.id);
                              return (
                                <motion.button
                                  key={sub.id}
                                  initial={{ opacity: 0, scale: 0.9 }}
                                  animate={{ opacity: 1, scale: 1 }}
                                  transition={{
                                    duration: 0.2,
                                    delay: si * 0.04,
                                  }}
                                  whileTap={{ scale: 0.95 }}
                                  onClick={() => toggleSubCategory(sub.id)}
                                  className={`h-[52px] rounded-[16px] text-[12px] text-white text-center flex items-center justify-center transition-all duration-200 ${
                                    subSelected ? 'bg-[#f3782b]' : 'bg-white/10'
                                  }`}
                                >
                                  {sub.name}
                                </motion.button>
                              );
                            })}
                          </div>
                        </div>
                      </motion.div>
                    </AnimatePresence>,
                  );
                }
              }
              return rows;
            })()}
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
            다음
          </button>
        </div>
      </div>
    </>
  );
}

function CategoryCard({
  cat,
  selected,
  onSelect,
  index,
}: {
  cat: Category;
  selected: boolean;
  onSelect: (id: string) => void;
  index: number;
}) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04 }}
      whileTap={{ scale: 0.96 }}
      onClick={() => onSelect(cat.id)}
      className={`flex-1 flex flex-col gap-0.5 items-center justify-center h-[75px] rounded-[24px] px-1 py-[26px] text-center text-white overflow-hidden transition-all duration-200 ${
        selected ? 'bg-[#f3782b]' : 'bg-[#3c3c3c] border border-[#343434]'
      }`}
    >
      <p className="font-bold text-[16px] leading-[19px] w-full">{cat.name}</p>
      <p className="font-normal text-[12px] leading-[14px] w-full">
        {cat.description}
      </p>
    </motion.button>
  );
}
