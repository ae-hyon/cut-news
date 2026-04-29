import React from 'react'
import type { ArchiveDateResponse, ArchiveDay, ArchiveMonthResponse, ArticleCard, FeedResponse } from '../lib/types'
import { getArchiveDate, getArchiveMonth } from '../services/backendApi'

function toArchiveDateResponse(userId: string, day?: ArchiveDay | null): ArchiveDateResponse | null {
  if (!day) return null
  return {
    user_id: userId,
    date: day.date,
    items: day.items,
  }
}

function pickArchiveDay(days: ArchiveDay[], preferredDate?: string | null): ArchiveDay | null {
  if (preferredDate) {
    const matched = days.find((day) => day.date === preferredDate)
    if (matched) return matched
  }
  return days[0] ?? null
}

function updateArticle(article: ArticleCard, articleId: string, nextScrapped: boolean): ArticleCard {
  if (article.id !== articleId) return article
  return { ...article, is_scrapped: nextScrapped }
}

function updateArchiveDay(day: ArchiveDay, articleId: string, nextScrapped: boolean): ArchiveDay {
  const updatedItems = day.items.map((article) => updateArticle(article, articleId, nextScrapped))
  return {
    ...day,
    items: nextScrapped ? updatedItems : updatedItems.filter((article) => article.id !== articleId),
    count: nextScrapped ? updatedItems.length : updatedItems.filter((article) => article.id !== articleId).length,
  }
}

export function useArchiveState() {
  const initialArchiveMonth = React.useMemo(() => new Date().toISOString().slice(0, 7), [])
  const [archiveMonth, setArchiveMonth] = React.useState<string>(initialArchiveMonth)
  const [archiveMonthData, setArchiveMonthData] = React.useState<ArchiveMonthResponse | null>(null)
  const [archiveDateData, setArchiveDateData] = React.useState<ArchiveDateResponse | null>(null)

  const clearArchive = React.useCallback(() => {
    setArchiveMonthData(null)
    setArchiveDateData(null)
  }, [])

  const loadArchiveForFirstFeedDate = React.useCallback(async (userId: string, feedData: FeedResponse) => {
    const firstArticleDate = feedData.blocks.flatMap((block) => block.articles)[0]?.published_at
    const derivedMonth = firstArticleDate ? firstArticleDate.slice(0, 7) : new Date().toISOString().slice(0, 7)
    setArchiveMonth(derivedMonth)
    const archiveData = await getArchiveMonth(userId, derivedMonth)
    setArchiveMonthData(archiveData)
    const selectedDay = pickArchiveDay(archiveData.days, firstArticleDate)
    setArchiveDateData(toArchiveDateResponse(userId, selectedDay))
    return archiveData
  }, [])

  const loadArchiveMonth = React.useCallback(async (userId: string, nextMonth: string) => {
    setArchiveMonth(nextMonth)
    const data = await getArchiveMonth(userId, nextMonth)
    setArchiveMonthData(data)
    const firstDay = pickArchiveDay(data.days)
    setArchiveDateData(toArchiveDateResponse(userId, firstDay))
    return data
  }, [])

  const restoreArchiveContext = React.useCallback(async (userId: string, month: string, preferredDate?: string | null) => {
    setArchiveMonth(month)
    const data = await getArchiveMonth(userId, month)
    setArchiveMonthData(data)
    const selectedDay = pickArchiveDay(data.days, preferredDate)
    setArchiveDateData(toArchiveDateResponse(userId, selectedDay))
    return data
  }, [])

  const openArchiveDate = React.useCallback(async (userId: string, date: string) => {
    const data = await getArchiveDate(userId, date)
    setArchiveDateData(data)
    return data
  }, [])

  const closeArchiveDate = React.useCallback(() => {
    setArchiveDateData(null)
  }, [])

  const applyScrapState = React.useCallback((articleId: string, nextScrapped: boolean) => {
    setArchiveMonthData((currentMonthData) => currentMonthData ? {
      ...currentMonthData,
      days: currentMonthData.days
        .map((day) => updateArchiveDay(day, articleId, nextScrapped))
        .filter((day) => day.items.length > 0),
    } : currentMonthData)

    setArchiveDateData((currentDateData) => currentDateData ? {
      ...currentDateData,
      items: nextScrapped
        ? currentDateData.items.map((article) => updateArticle(article, articleId, nextScrapped))
        : currentDateData.items.filter((article) => article.id !== articleId),
    } : currentDateData)
  }, [])

  return {
    archiveMonth,
    archiveMonthData,
    archiveDateData,
    clearArchive,
    loadArchiveForFirstFeedDate,
    loadArchiveMonth,
    restoreArchiveContext,
    openArchiveDate,
    closeArchiveDate,
    applyScrapState,
  }
}

export type ArchiveState = ReturnType<typeof useArchiveState>
