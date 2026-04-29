'use client'

import { useRouter } from 'next/navigation'
import { motion } from 'motion/react'
import { useOnboardingStore } from '@/stores/onboarding'
import { CATEGORIES, MAX_WIDE_CATEGORIES } from '@/constants/categories'
import { showToast } from '@/components/Toast'

export default function OnboardingWide() {
  const router = useRouter()
  const { selectedCategories, toggleCategory } = useOnboardingStore()

  const handleToggle = (id: string) => {
    const success = toggleCategory(id)
    if (!success) {
      showToast(`대분류 ${MAX_WIDE_CATEGORIES}개까지만 선택 가능해요`)
    }
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
          2번째 다됐어요!
        </h1>
        <p className="text-text-secondary text-sm mt-2">
          관심 분야를 선택해주세요 (최대 {MAX_WIDE_CATEGORIES}개)
        </p>
      </motion.div>

      {/* Category chips */}
      <div className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-2 gap-3">
          {CATEGORIES.map((cat, i) => {
            const selected = selectedCategories.includes(cat.id)
            return (
              <motion.button
                key={cat.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.04 }}
                whileTap={{ scale: 0.96 }}
                onClick={() => handleToggle(cat.id)}
                className={`p-4 rounded-lg border text-left transition-all duration-200 ${
                  selected
                    ? 'border-accent bg-accent-muted'
                    : 'border-border-default bg-bg-elevated hover:border-text-tertiary'
                }`}
              >
                <p
                  className={`font-bold text-sm mb-1 ${selected ? 'text-accent' : ''}`}
                >
                  {cat.name}
                </p>
                <p className="text-text-tertiary text-xs leading-snug">
                  {cat.keywords.join(' · ')}
                </p>
              </motion.button>
            )
          })}
        </div>
      </div>

      {/* Navigation */}
      <div className="mt-8 pb-4 flex gap-3">
        <button
          onClick={() => router.push('/onboarding')}
          className="flex-1 py-4 rounded-lg text-base font-bold border border-border-default bg-bg-elevated text-text-secondary hover:border-text-tertiary transition-all"
        >
          이전
        </button>
        <button
          onClick={() => router.push('/onboarding/complete')}
          disabled={selectedCategories.length === 0}
          className="flex-[2] py-4 rounded-lg text-base font-bold transition-all duration-200
            bg-accent text-bg hover:bg-accent-hover
            disabled:bg-bg-elevated disabled:text-text-tertiary disabled:cursor-not-allowed"
        >
          다음
        </button>
      </div>
    </>
  )
}
