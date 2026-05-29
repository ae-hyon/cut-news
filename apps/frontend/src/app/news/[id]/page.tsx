'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'motion/react';
import { addMyScrap, getMyArticle, removeMyScrap } from '@/services/contentApi';
import type { ArticleDetail } from '@/lib/types';

export default function NewsDetail() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = params.id as string;
  const snapshotId = searchParams.get('snapshot_id') ?? undefined;
  const [news, setNews] = useState<ArticleDetail | null>(null);
  const [scrapped, setScrapped] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    getMyArticle(id, snapshotId)
      .then((article) => {
        if (!active) return;
        setNews(article);
        setScrapped(article.is_scrapped);
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
  }, [id, snapshotId]);

  const toggleScrap = async () => {
    if (!news) return;
    const nextScrapped = !scrapped;
    setScrapped(nextScrapped);
    try {
      if (nextScrapped) {
        await addMyScrap(news.id);
      } else {
        await removeMyScrap(news.id);
      }
    } catch (err) {
      setScrapped(!nextScrapped);
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center px-6">
        <p className="text-text-tertiary text-sm animate-pulse">
          뉴스를 불러오는 중...
        </p>
      </div>
    );
  }

  if (error && !news) {
    return (
      <div className="min-h-dvh flex flex-col items-center justify-center px-6 text-center">
        <p className="text-red-400 text-sm">뉴스를 불러오지 못했어요</p>
        <p className="text-text-tertiary text-xs mt-2">{error}</p>
      </div>
    );
  }

  if (!news) {
    return (
      <div className="min-h-dvh flex items-center justify-center px-6">
        <p className="text-text-secondary">뉴스를 찾을 수 없습니다</p>
      </div>
    );
  }

  return (
    <div className="min-h-dvh max-w-lg mx-auto px-6 py-8">
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        onClick={() => router.back()}
        className="mb-8 text-text-secondary text-sm hover:text-text-primary transition-colors flex items-center gap-1"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M15 18l-6-6 6-6" />
        </svg>
        뒤로
      </motion.button>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="flex items-center gap-3 mb-4"
      >
        <span className="text-accent text-xs font-bold uppercase tracking-widest">
          {news.primary_category}
        </span>
        <span className="text-text-tertiary text-xs">{news.published_at}</span>
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="font-[family-name:var(--font-display)] text-2xl font-bold leading-tight mb-8"
      >
        {news.title}
      </motion.h1>

      <motion.div
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ delay: 0.25, duration: 0.4 }}
        className="h-px bg-border-default mb-8 origin-left"
      />

      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="text-text-primary text-base leading-relaxed mb-4"
      >
        {news.summary}
      </motion.p>

      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="text-text-secondary text-sm leading-relaxed mb-12 whitespace-pre-wrap"
      >
        {news.content}
      </motion.p>

      {error && (
        <p className="text-red-400 text-xs text-center mb-4">{error}</p>
      )}

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="flex gap-3"
      >
        <a
          href={news.original_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 py-3.5 rounded-lg text-sm font-bold border border-border-default bg-bg-elevated text-text-secondary hover:border-text-tertiary transition-all text-center"
        >
          원문보기
        </a>
        <button
          onClick={toggleScrap}
          className={`flex-1 py-3.5 rounded-lg text-sm font-bold transition-all duration-200 flex items-center justify-center gap-2 ${
            scrapped
              ? 'bg-accent text-bg'
              : 'border border-accent text-accent hover:bg-accent hover:text-bg'
          }`}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill={scrapped ? 'currentColor' : 'none'}
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z" />
          </svg>
          {scrapped ? '스크랩됨' : '스크랩'}
        </button>
      </motion.div>
    </div>
  );
}
