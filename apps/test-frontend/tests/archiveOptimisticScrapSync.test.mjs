import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('archive state applies scrap updates to visible month/date panels before reload completes', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/useArchiveState.ts'), 'utf8')

  assert.match(source, /const applyScrapState = React\.useCallback\(\(articleId: string, nextScrapped: boolean\) => \{/)
  assert.match(source, /setArchiveMonthData\(\(currentMonthData\) => currentMonthData \? \{/)
  assert.match(source, /days: currentMonthData\.days\s*\.map\(\(day\) => updateArchiveDay\(day, articleId, nextScrapped\)\)\s*\.filter\(\(day\) => day\.items\.length > 0\)/s)
  assert.match(source, /setArchiveDateData\(\(currentDateData\) => currentDateData \? \{/)
  assert.match(source, /items: nextScrapped\s*\? currentDateData\.items\.map\(\(article\) => updateArticle\(article, articleId, nextScrapped\)\)\s*:\s*currentDateData\.items\.filter\(\(article\) => article\.id !== articleId\)/s)
})
