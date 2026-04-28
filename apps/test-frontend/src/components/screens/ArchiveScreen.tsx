import React from 'react'
import NewsCard from '../common/NewsCard'
import type { ArchiveDateResponse, ArchiveMonthResponse, ArticleCard } from '../../lib/types'

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

interface ArchiveScreenProps {
  archiveMonth: string
  archiveMonthOptions: string[]
  archiveMonthData: ArchiveMonthResponse | null
  archiveDateData: ArchiveDateResponse | null
  onLoadArchiveMonth: (month: string) => void
  onOpenArchiveDate: (date: string) => void
  onCloseArchiveDate: () => void
  onOpenArticle: (articleId: string) => void
}

function formatMonthLabel(month: string) {
  const [year, monthNumber] = month.split('-')
  return `${year}년 ${Number(monthNumber)}월`
}

function formatDateLabel(date: string) {
  return date.replace(/-/g, '.')
}

function buildCalendarCells(month: string, days: ArchiveMonthResponse['days']) {
  const [year, monthNumber] = month.split('-').map(Number)
  const firstDate = new Date(year, monthNumber - 1, 1)
  const lastDate = new Date(year, monthNumber, 0).getDate()
  const byDay = new Map(days.map((day) => [Number(day.date.slice(-2)), day]))
  const cells: Array<{ key: string; dayNumber?: number; item?: ArchiveMonthResponse['days'][number] }> = []

  for (let i = 0; i < firstDate.getDay(); i += 1) cells.push({ key: `blank-${i}` })
  for (let dayNumber = 1; dayNumber <= lastDate; dayNumber += 1) {
    cells.push({ key: `day-${dayNumber}`, dayNumber, item: byDay.get(dayNumber) })
  }
  return cells
}

export default function ArchiveScreen({ archiveMonth, archiveMonthOptions, archiveMonthData, archiveDateData, onLoadArchiveMonth, onOpenArchiveDate, onCloseArchiveDate, onOpenArticle }: ArchiveScreenProps) {
  const archiveDays = archiveMonthData?.days || []
  const calendarCells = buildCalendarCells(archiveMonth, archiveDays)
  const noopScrap = (_article: ArticleCard) => undefined

  return (
    <section className="screen archive-screen">
      <div className="archive-title-block">
        <h2>나의 뉴스 아카이브</h2>
        <div className="archive-month-row">
          <span>월간 이력</span>
          <strong>{formatMonthLabel(archiveMonth)}</strong>
        </div>
        <div className="archive-switcher">
          {archiveMonthOptions.map((month) => (
            <button key={month} className={archiveMonth === month ? 'active' : ''} onClick={() => onLoadArchiveMonth(month)}>{month}</button>
          ))}
        </div>
      </div>

      <div className="archive-calendar-grid" aria-label={`${formatMonthLabel(archiveMonth)} 아카이브 달력`}>
        {WEEKDAYS.map((weekday) => <span key={weekday} className="calendar-weekday">{weekday}</span>)}
        {calendarCells.map((cell) => {
          if (!cell.dayNumber) return <span key={cell.key} className="calendar-empty" />
          const hasItems = Boolean(cell.item?.items.length)
          const date = `${archiveMonth}-${String(cell.dayNumber).padStart(2, '0')}`
          return (
            <button key={cell.key} className={hasItems ? 'calendar-day has-items' : 'calendar-day'} onClick={() => hasItems && onOpenArchiveDate(date)} disabled={!hasItems}>
              <span>{cell.dayNumber}</span>
              {hasItems && <em>{cell.item?.items.length}</em>}
            </button>
          )
        })}
      </div>

      {archiveDateData && (
        <div className="archive-date-panel">
          <button className="archive-date-close" onClick={onCloseArchiveDate} aria-label="날짜별 보기 닫기">×</button>
          <div className="archive-date-heading">
            <p>아카이브 뉴스 날짜별 보기</p>
            <h3>{formatDateLabel(archiveDateData.date)}</h3>
            <span>총 {archiveDateData.items.length}건</span>
          </div>
          {archiveDateData.items.length === 0 ? <p className="empty-state compact">이 날짜에는 저장된 뉴스가 없어요.</p> : (
            <div className="pdf-card-board archive-date-board">
              {archiveDateData.items.map((article, idx) => (
                <NewsCard key={article.id} article={article} index={idx} size={idx % 2 === 0 ? 'feature' : 'regular'} onOpenArticle={onOpenArticle} onToggleScrap={noopScrap} />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
