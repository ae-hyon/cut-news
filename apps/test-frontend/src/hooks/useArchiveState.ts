import React from 'react'
import type { ArchiveDateResponse, ArchiveDay, ArchiveMonthResponse, FeedResponse } from '../lib/types'
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
  }
}

export type ArchiveState = ReturnType<typeof useArchiveState>
