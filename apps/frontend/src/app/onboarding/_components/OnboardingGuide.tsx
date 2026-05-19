'use client';

import { motion } from 'motion/react';

export default function OnboardingGuide() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.15 }}
      className="text-center text-[20px] font-semibold text-white leading-[32px] w-full"
    >
      <p>관심있는 분야를 최소 3개 이상 선택해서</p>
      <p>하루에 한번씩 요약해서 받아보세요</p>
    </motion.div>
  );
}
