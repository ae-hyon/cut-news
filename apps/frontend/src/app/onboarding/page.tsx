'use client'

import { useRouter } from 'next/navigation'
import { motion } from 'motion/react'
import { useOnboardingStore } from '@/stores/onboarding'
import type { UserType } from '@/types'

const today = new Date().toLocaleDateString('ko-KR', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
})

export default function OnboardingStep1() {
  const router = useRouter()
  const { userType, setUserType } = useOnboardingStore()

  const handleNext = () => {
    if (!userType) return
    router.push(
      userType === 'wide' ? '/onboarding/wide' : '/onboarding/narrow'
    )
  }

  return (
    <>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-12"
      >
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-bold tracking-tight">
          Annoying Cap
        </h1>
        <p className="text-text-secondary text-sm mt-1">{today}</p>
      </motion.div>

      {/* Guide text */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
        className="mb-10"
      >
        <p className="text-lg font-medium leading-relaxed">
          관심있는 분야를 선택해서
          <br />
          <span className="text-accent">하루에 한번씩</span> 요약해서
          받아보세요
        </p>
      </motion.div>

      {/* Type selection */}
      <div className="flex flex-col gap-4 flex-1">
        <TypeCard
          type="wide"
          selected={userType === 'wide'}
          onSelect={setUserType}
          title="넓게 볼랭"
          description="다양한 분야의 뉴스를 폭넓게"
          sub="대분류 최대 5개 선택"
          delay={0.25}
        />
        <TypeCard
          type="narrow"
          selected={userType === 'narrow'}
          onSelect={setUserType}
          title="깊게 볼랭"
          description="하나의 분야를 깊이있게"
          sub="카테고리 1개 + 소분류 선택"
          delay={0.35}
        />
      </div>

      {/* Next button */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.45 }}
        className="mt-8 pb-4"
      >
        <button
          onClick={handleNext}
          disabled={!userType}
          className="w-full py-4 rounded-lg text-base font-bold transition-all duration-200
            bg-accent text-bg hover:bg-accent-hover
            disabled:bg-bg-elevated disabled:text-text-tertiary disabled:cursor-not-allowed"
        >
          다음
        </button>
      </motion.div>
    </>
  )
}

function TypeCard({
  type,
  selected,
  onSelect,
  title,
  description,
  sub,
  delay,
}: {
  type: UserType
  selected: boolean
  onSelect: (t: UserType) => void
  title: string
  description: string
  sub: string
  delay: number
}) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onSelect(type)}
      className={`relative w-full text-left p-6 rounded-lg border-2 transition-all duration-200 ${
        selected
          ? 'border-accent bg-accent-muted'
          : 'border-border-default bg-bg-elevated hover:border-text-tertiary'
      }`}
    >
      {/* selection indicator */}
      <div
        className={`absolute top-5 right-5 w-5 h-5 rounded-full border-2 transition-all duration-200 flex items-center justify-center ${
          selected ? 'border-accent bg-accent' : 'border-text-tertiary'
        }`}
      >
        {selected && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="w-2 h-2 rounded-full bg-bg"
          />
        )}
      </div>

      <h2 className="font-[family-name:var(--font-display)] text-xl font-bold mb-2">
        {title}
      </h2>
      <p className="text-text-secondary text-sm mb-1">{description}</p>
      <p className="text-text-tertiary text-xs">{sub}</p>
    </motion.button>
  )
}
