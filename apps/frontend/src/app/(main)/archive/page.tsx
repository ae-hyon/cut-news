'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'motion/react';
import NewsBlock from '@/components/NewsBlock';
import {
  getMyArchiveDate,
  getMyArchiveMonth,
  mapArticleToNewsItem,
} from '@/services/contentApi';
import type { ArchiveDay } from '@/lib/types';
import type { NewsItem } from '@/types';

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfWeek(year: number, month: number) {
  return new Date(year, month, 1).getDay();
}

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];

export default function ArchivePage() {
  const router = useRouter();
  const now = new Date();
  const [viewYear, setViewYear] = useState(now.getFullYear());
  const [viewMonth, setViewMonth] = useState(now.getMonth());
  const [days, setDays] = useState<ArchiveDay[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedNews, setSelectedNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const monthKey = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}`;
  const daysInMonth = getDaysInMonth(viewYear, viewMonth);
  const firstDay = getFirstDayOfWeek(viewYear, viewMonth);
  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  const dayMap = new Map(days.map((day) => [day.date, day]));

  useEffect(() => {
    let active = true;
    setLoading(true);
    setSelectedDate(null);
    setSelectedNews([]);

    getMyArchiveMonth(monthKey)
      .then((response) => {
        if (!active) return;
        setDays(response.days);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : String(err));
        setDays([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [monthKey]);

  const openDate = async (date: string) => {
    if (selectedDate === date) {
      setSelectedDate(null);
      setSelectedNews([]);
      return;
    }

    setSelectedDate(date);
    try {
      const response = await getMyArchiveDate(date);
      setSelectedNews(
        response.items.map((item, index) => mapArticleToNewsItem(item, index)),
      );
      setError(null);
    } catch (err) {
      setSelectedNews([]);
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const prevMonth = () => {
    if (viewMonth === 0) {
      setViewYear(viewYear - 1);
      setViewMonth(11);
    } else {
      setViewMonth(viewMonth - 1);
    }
  };

  const nextMonth = () => {
    if (viewMonth === 11) {
      setViewYear(viewYear + 1);
      setViewMonth(0);
    } else {
      setViewMonth(viewMonth + 1);
    }
  };

  return (
    <div className="px-6 pt-6">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
          나의 뉴스 아카이브
        </h2>
      </motion.div>

      <div className="flex items-center justify-between mb-6">
        <button
          onClick={prevMonth}
          className="text-text-secondary hover:text-text-primary p-2 transition-colors"
        >
          ‹
        </button>
        <p className="text-text-primary text-sm font-medium">
          월간 이력 — {viewYear}년 {viewMonth + 1}월
        </p>
        <button
          onClick={nextMonth}
          className="text-text-secondary hover:text-text-primary p-2 transition-colors"
        >
          ›
        </button>
      </div>

      {loading && (
        <p className="text-text-tertiary text-sm text-center py-8 animate-pulse">
          아카이브를 불러오는 중...
        </p>
      )}

      {error && !loading && (
        <p className="text-red-400 text-sm text-center py-4">{error}</p>
      )}

      <div className="grid grid-cols-7 gap-1 mb-6">
        {WEEKDAYS.map((d) => (
          <div
            key={d}
            className="text-center text-text-tertiary text-[10px] font-medium py-2"
          >
            {d}
          </div>
        ))}

        {Array.from({ length: firstDay }).map((_, i) => (
          <div key={`e-${i}`} />
        ))}

        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1;
          const dateStr = `${monthKey}-${String(day).padStart(2, '0')}`;
          const archiveDay = dayMap.get(dateStr);
          const hasNews = !!archiveDay && archiveDay.items.length > 0;
          const isFuture = dateStr > todayStr;
          const isSelected = selectedDate === dateStr;
          const disabled = loading || isFuture || !hasNews;

          return (
            <button
              key={day}
              disabled={disabled}
              onClick={() => void openDate(dateStr)}
              className={`relative py-2.5 rounded-md text-xs font-medium transition-all duration-200 ${
                isSelected
                  ? 'bg-accent text-bg'
                  : disabled
                    ? 'text-text-tertiary/30 cursor-not-allowed'
                    : 'text-text-primary hover:bg-bg-elevated'
              }`}
            >
              {day}
              {hasNews && !isSelected && (
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-accent" />
              )}
            </button>
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        {selectedDate && (
          <motion.div
            key={selectedDate}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25 }}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-text-primary">
                {selectedDate.replace(/-/g, '.')}
              </h3>
              <span className="text-xs text-text-tertiary">
                {selectedNews.length}개 기사
              </span>
            </div>
            <div className="columns-2 gap-3">
              {selectedNews.map((item, i) => (
                <NewsBlock
                  key={item.id}
                  news={item}
                  index={i}
                  onClick={(id) => router.push(`/news/${id}`)}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
