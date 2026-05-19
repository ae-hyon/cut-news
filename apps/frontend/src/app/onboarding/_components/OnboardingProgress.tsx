'use client';

import { motion } from 'motion/react';

const TOTAL_STEPS = 3;

interface OnboardingProgressProps {
  step: number;
  label?: string;
  rightLabel?: string;
}

export default function OnboardingProgress({
  step,
  label,
  rightLabel,
}: OnboardingProgressProps) {
  const progressWidth = `${(step / TOTAL_STEPS) * 100}%`;

  // Step 1 uses badge style, steps 2+ use text labels
  const isBadgeStyle = step === 1;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="flex flex-col gap-3 px-1"
    >
      {isBadgeStyle ? (
        <div className="flex items-end h-[33px]">
          <div className="relative">
            <div className="bg-[#f07426] rounded-full px-2 py-1 text-[12px] font-semibold text-white text-center">
              {label || '시작'}
            </div>
            <div
              className="absolute left-1/2 -translate-x-1/2 -bottom-[5px] w-0 h-0"
              style={{
                borderLeft: '4px solid transparent',
                borderRight: '4px solid transparent',
                borderTop: '5px solid #f07426',
              }}
            />
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between text-[12px] text-white leading-[14px]">
          <span>{label}</span>
          <span>{rightLabel}</span>
        </div>
      )}
      <div className="bg-white/15 h-1 rounded-full w-full">
        <div
          className="bg-[#f3782b] h-1 rounded-full transition-all duration-300"
          style={{ width: progressWidth }}
        />
      </div>
    </motion.div>
  );
}
