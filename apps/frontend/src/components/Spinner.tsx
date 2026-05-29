'use client';

import { motion } from 'motion/react';

interface SpinnerProps {
  size?: number;
}

export default function Spinner({ size = 40 }: SpinnerProps) {
  return (
    <div className="flex items-center justify-center">
      <motion.svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      >
        <circle
          cx="20"
          cy="20"
          r="16"
          stroke="#5a5751"
          strokeWidth="3.6"
          strokeLinecap="round"
        />
        <circle
          cx="20"
          cy="20"
          r="16"
          stroke="#ff6b2c"
          strokeWidth="3.6"
          strokeLinecap="round"
          strokeDasharray="75 100"
        />
      </motion.svg>
    </div>
  );
}
