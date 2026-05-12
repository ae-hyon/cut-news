'use client'

import { motion } from 'motion/react'

export default function ProfilePage() {
  return (
    <div className="px-6 pt-6">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center justify-center py-20"
      >
        <div className="w-16 h-16 rounded-full bg-bg-elevated border border-border-default flex items-center justify-center mb-4">
          <span className="text-2xl">&#x1f9d1;</span>
        </div>
        <h2 className="font-[family-name:var(--font-display)] text-lg font-bold mb-1">
          선우
        </h2>
        <p className="text-text-secondary text-sm">프로필 및 설정 (TBD)</p>
      </motion.div>
    </div>
  )
}
