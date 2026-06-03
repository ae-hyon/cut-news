'use client';

import { motion } from 'motion/react';
import type { NewsItem } from '@/types';

interface HomeNewsCardProps {
  news: NewsItem;
  index: number;
  color: string;
  onClick: (id: string) => void;
}

export default function HomeNewsCard({
  news,
  index,
  color,
  onClick,
}: HomeNewsCardProps) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onClick(news.id)}
      style={{ backgroundColor: color }}
      className="w-full flex-1 text-left p-[24px] rounded-[24px] overflow-hidden flex flex-col items-start justify-start"
    >
      <p className="font-semibold text-base leading-[1.5] text-[#101010] break-words">
        {news.title}
      </p>
    </motion.button>
  );
}
