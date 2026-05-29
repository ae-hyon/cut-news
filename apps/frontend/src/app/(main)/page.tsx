'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import NewsBlock from '@/components/NewsBlock';
import { getMyFeed, mapArticleToNewsItem } from '@/services/contentApi';
import type { NewsItem } from '@/types';

export default function NewsHome() {
  const router = useRouter();
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    getMyFeed()
      .then((feed) => {
        if (!active) return;
        const items = feed.blocks.flatMap((block) => block.articles);
        setNews(
          items.map((item, index) =>
            mapArticleToNewsItem(item, index, feed.snapshot_id),
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
          뉴스를 불러오는 중...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-20 text-center">
        <p className="text-red-400 text-sm">뉴스를 불러오지 못했어요</p>
        <p className="text-text-tertiary text-xs mt-2">{error}</p>
      </div>
    );
  }

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
            onClick={(id, snapshotId) =>
              router.push(
                snapshotId
                  ? `/news/${id}?snapshot_id=${snapshotId}`
                  : `/news/${id}`,
              )
            }
          />
        ))}
      </div>
    </div>
  );
}
