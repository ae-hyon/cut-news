'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import Spinner from '@/components/Spinner';
import HomeNewsCard from '@/components/HomeNewsCard';
import { getMyFeed, mapArticleToNewsItem } from '@/services/contentApi';
import { getCardColor } from '@/constants/card-colors';
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
      <div className="flex-1 flex items-center justify-center px-5 py-10">
        <Spinner />
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
    const today = new Date()
      .toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      })
      .replace(/\. /g, '.')
      .replace(/\.$/, '');

    return (
      <div className="flex-1 flex flex-col items-center justify-center px-5 py-10 text-center h-[420px]">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col gap-4 w-full"
        >
          <p className="text-[#ff873c] text-2xl font-bold opacity-80">
            {today}
          </p>
          <div className="flex flex-col gap-2 w-full">
            <p className="text-2xl font-bold">너무 일찍 오셨네요!</p>
            <div className="text-base opacity-70 leading-6">
              <p>오늘의 한 컷이 아직 생성되지 않았어요.</p>
              <p>오전 9시 이후에 다시 와주세요.</p>
            </div>
          </div>
        </motion.div>
      </div>
    );
  }

  const leftColumn = news.filter((_, i) => i % 2 === 0);
  const rightColumn = news.filter((_, i) => i % 2 !== 0);

  const today = new Date()
    .toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
    .replace(/\. /g, '.')
    .replace(/\.$/, '');

  return (
    <div className="px-5 pt-[10px] pb-10">
      <p className="text-sm font-bold opacity-80 mb-4">{today}</p>
      <div className="flex gap-[2px]">
        <div className="flex-1 flex flex-col gap-[2px] min-w-0">
          {leftColumn.map((item, i) => (
            <HomeNewsCard
              key={item.id}
              news={item}
              index={i * 2}
              color={getCardColor(i * 2)}
              onClick={(id) =>
                router.push(
                  item.snapshotId
                    ? `/news/${id}?snapshot_id=${item.snapshotId}`
                    : `/news/${id}`,
                )
              }
            />
          ))}
        </div>
        <div className="flex-1 flex flex-col gap-[2px] min-w-0">
          {rightColumn.map((item, i) => (
            <HomeNewsCard
              key={item.id}
              news={item}
              index={i * 2 + 1}
              color={getCardColor(i * 2 + 1)}
              onClick={(id) =>
                router.push(
                  item.snapshotId
                    ? `/news/${id}?snapshot_id=${item.snapshotId}`
                    : `/news/${id}`,
                )
              }
            />
          ))}
        </div>
      </div>
    </div>
  );
}
