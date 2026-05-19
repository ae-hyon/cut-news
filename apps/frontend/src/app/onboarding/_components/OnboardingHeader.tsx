'use client';

import { motion } from 'motion/react';
import Image from 'next/image';

const today = new Date()
  .toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  .replace(/\. /g, '.')
  .replace(/\.$/, '');

export default function OnboardingHeader() {
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
        <span className="text-[14px] font-bold text-white underline">
          로그인
        </span>
      </div>
    </motion.div>
  );
}
