'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import NewsBlock from '@/components/NewsBlock';
import { getMyScraps, mapArticleToNewsItem } from '@/services/contentApi';
import type { NewsItem } from '@/types';

export default function ScrapPage() {
  const router = useRouter();
  const [scrappedNews, setScrappedNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    getMyScraps()
      .then((response) => {
        if (!active) return;
        setScrappedNews(
          response.items.map((item, index) =>
            mapArticleToNewsItem(item, index),
          ),
        );
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 py-20">
        <p className="text-text-tertiary text-sm animate-pulse">
          스크랩을 불러오는 중...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-20 text-center">
        <p className="text-red-400 text-sm">스크랩을 불러오지 못했어요</p>
        <p className="text-text-tertiary text-xs mt-2">{error}</p>
      </div>
    );
  }

  if (scrappedNews.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-text-tertiary)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="mx-auto mb-4"
          >
            <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z" />
          </svg>
          <p className="text-text-secondary text-sm">
            아직 스크랩한 뉴스가 없어요
          </p>
          <p className="text-text-tertiary text-xs mt-1">
            뉴스 상세에서 스크랩 버튼을 눌러보세요
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="px-4 pt-4">
      <div className="columns-2 gap-3">
        {scrappedNews.map((item, i) => (
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
