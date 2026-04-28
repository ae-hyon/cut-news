import React from 'react'
import type { ArchiveDateResponse, ArchiveMonthResponse, FeedResponse } from '../lib/types'
import { getArchiveDate, getArchiveMonth } from '../services/backendApi'

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
    const firstDay = archiveData.days[0]
    setArchiveDateData(firstDay ? { user_id: userId, date: firstDay.date, items: firstDay.items } : null)
    return archiveData
  }, [])

  const loadArchiveMonth = React.useCallback(async (userId: string, nextMonth: string) => {
    setArchiveMonth(nextMonth)
    const data = await getArchiveMonth(userId, nextMonth)
    setArchiveMonthData(data)
    const firstDay = data.days[0]
    setArchiveDateData(firstDay ? { user_id: userId, date: firstDay.date, items: firstDay.items } : null)
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
    openArchiveDate,
    closeArchiveDate,
  }
}

export type ArchiveState = ReturnType<typeof useArchiveState>
