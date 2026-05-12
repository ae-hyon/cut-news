'use client'

import { useRouter } from 'next/navigation'
import { motion } from 'motion/react'
import { useOnboardingStore } from '@/stores/onboarding'
import { CATEGORIES } from '@/constants/categories'

export default function OnboardingComplete() {
  const router = useRouter()
  const {
    userType,
    selectedCategories,
    narrowMainCategory,
    selectedSubCategories,
  } = useOnboardingStore()

  const isWide = userType === 'wide'

  const selectedNames = isWide
    ? selectedCategories.map(
        (id) => CATEGORIES.find((c) => c.id === id)?.name ?? id
      )
    : (() => {
        const main = CATEGORIES.find((c) => c.id === narrowMainCategory)
        if (!main) return []
        const subNames = selectedSubCategories.map(
          (id) =>
            main.subcategories?.find((s) => s.id === id)?.name ?? id
        )
        return [main.name, ...subNames]
      })()

  const editRoute = isWide ? '/onboarding/wide' : '/onboarding/narrow'

  const handleKakaoLogin = () => {
    // TODO: 카카오 SDK 연동
    router.push('/')
  }

  return (
    <>
      {/* Progress */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <p className="text-text-secondary text-sm mb-1">3 / 3</p>
        <h1 className="font-[family-name:var(--font-display)] text-xl font-bold">
          3번째 완료!
        </h1>
      </motion.div>

      {/* Summary */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="mb-6"
      >
        <p className="text-text-secondary text-sm mb-4">
          {isWide
            ? '선택한 관심 분야'
            : `${CATEGORIES.find((c) => c.id === narrowMainCategory)?.name} 세부 관심사`}
        </p>

        <div className="flex flex-wrap gap-2">
          {selectedNames.map((name, i) => (
            <motion.button
              key={name}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 + i * 0.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => router.push(editRoute)}
              className="px-4 py-2 rounded-full border border-accent bg-accent-muted text-accent text-sm font-medium hover:bg-accent hover:text-bg transition-all duration-200"
            >
              {name}
            </motion.button>
          ))}
        </div>

        <p className="text-text-tertiary text-xs mt-3">
          태그를 탭하면 수정할 수 있어요
        </p>
      </motion.div>

      <div className="flex-1" />

      {/* Kakao Login CTA */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="pb-4"
      >
        <button
          onClick={handleKakaoLogin}
          className="w-full py-4 rounded-lg text-base font-bold bg-[#FEE500] text-[#191919] hover:brightness-95 transition-all duration-200 flex items-center justify-center gap-2"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M9 0.6C4.029 0.6 0 3.713 0 7.551c0 2.467 1.639 4.633 4.104 5.862l-1.04 3.858c-.09.334.291.6.564.395l4.624-3.074c.247.02.498.03.748.03 4.971 0 9-3.113 9-6.951S13.971.6 9 .6z"
              fill="#191919"
            />
          </svg>
          카카오 로그인하고 매일 블록 받아보기
        </button>
      </motion.div>
    </>
  )
}
