'use client'

import { useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'motion/react'
import NewsBlock from '@/components/NewsBlock'
import { MOCK_NEWS } from '@/constants/mock-news'

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfWeek(year: number, month: number) {
  return new Date(year, month, 1).getDay()
}

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

export default function ArchivePage() {
  const router = useRouter()
  const now = new Date()
  const [viewYear, setViewYear] = useState(now.getFullYear())
  const [viewMonth, setViewMonth] = useState(now.getMonth())
  const [selectedDate, setSelectedDate] = useState<string | null>(null)

  const daysInMonth = getDaysInMonth(viewYear, viewMonth)
  const firstDay = getFirstDayOfWeek(viewYear, viewMonth)

  // dates that have news
  const newsDates = useMemo(() => {
    const dates = new Set<string>()
    MOCK_NEWS.forEach((n) => dates.add(n.publishedAt))
    return dates
  }, [])

  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`

  const prevMonth = () => {
    if (viewMonth === 0) {
      setViewYear(viewYear - 1)
      setViewMonth(11)
    } else {
      setViewMonth(viewMonth - 1)
    }
    setSelectedDate(null)
  }

  const nextMonth = () => {
    if (viewMonth === 11) {
      setViewYear(viewYear + 1)
      setViewMonth(0)
    } else {
      setViewMonth(viewMonth + 1)
    }
    setSelectedDate(null)
  }

  const selectedNews = selectedDate
    ? MOCK_NEWS.filter((n) => n.publishedAt === selectedDate)
    : []

  return (
    <div className="px-6 pt-6">
      {/* Title */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
          나의 뉴스 아카이브
        </h2>
      </motion.div>

      {/* Month nav */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={prevMonth}
          className="text-text-secondary hover:text-text-primary p-2 transition-colors"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <p className="text-text-primary text-sm font-medium">
          월간 이력 — {viewYear}년 {viewMonth + 1}월
        </p>
        <button
          onClick={nextMonth}
          className="text-text-secondary hover:text-text-primary p-2 transition-colors"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18l6-6-6-6" />
          </svg>
        </button>
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-1 mb-6">
        {WEEKDAYS.map((d) => (
          <div
            key={d}
            className="text-center text-text-tertiary text-[10px] font-medium py-2"
          >
            {d}
          </div>
        ))}

        {/* empty cells before first day */}
        {Array.from({ length: firstDay }).map((_, i) => (
          <div key={`e-${i}`} />
        ))}

        {/* day cells */}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1
          const dateStr = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
          const hasNews = newsDates.has(dateStr)
          const isFuture = dateStr > todayStr
          const isSelected = selectedDate === dateStr
          const isToday = dateStr === todayStr

          return (
            <button
              key={day}
              disabled={isFuture || !hasNews}
              onClick={() => setSelectedDate(isSelected ? null : dateStr)}
              className={`relative py-2.5 rounded-md text-xs font-medium transition-all duration-200 ${
                isSelected
                  ? 'bg-accent text-bg'
                  : isToday
                    ? 'text-accent'
                    : isFuture
                      ? 'text-text-tertiary/30 cursor-not-allowed'
                      : hasNews
                        ? 'text-text-primary hover:bg-bg-elevated'
                        : 'text-text-tertiary cursor-not-allowed'
              }`}
            >
              {day}
              {hasNews && !isSelected && (
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-accent" />
              )}
            </button>
          )
        })}
      </div>

      {/* Selected date news */}
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
              <button
                onClick={() => setSelectedDate(null)}
                className="text-text-tertiary hover:text-text-primary text-xs transition-colors"
              >
                닫기
              </button>
            </div>
            <div className="columns-2 gap-3 pb-8">
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
  )
}
