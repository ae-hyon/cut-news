'use client';

import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import NewsBlock from '@/components/NewsBlock';
import { MOCK_NEWS } from '@/constants/mock-news';

export default function NewsHome() {
  const router = useRouter();
  const news = MOCK_NEWS;

  if (news.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <p className="text-text-tertiary text-4xl mb-4">---</p>
          <p className="text-text-secondary text-sm">
            오늘은 발행된 뉴스가 없어요
          </p>
          <p className="text-text-tertiary text-xs mt-1">
            내일 아침에 다시 확인해주세요
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="px-4 pt-4">
      <div className="columns-2 gap-3">
        {news.map((item, i) => (
          <NewsBlock
            key={item.id}
            news={item}
            index={i}
            onClick={(id) => router.push(`/news/${id}`)}
          />
        ))}
      </div>
    </div>
  );
}
