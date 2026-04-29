import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('archive state exposes a restore helper that can reopen a selected date after live reloads', async () => {
  const archive = await readFile(path.join(projectRoot, 'src/hooks/useArchiveState.ts'), 'utf8')

  assert.match(archive, /const restoreArchiveContext = React\.useCallback\(async \(userId: string, month: string, preferredDate\?: string \| null\) => \{/)
  assert.match(archive, /const selectedDay = pickArchiveDay\(data\.days, preferredDate\)/)
  assert.match(archive, /restoreArchiveContext,/)
})

test('archive detail scrap reload preserves month and date context instead of falling back to feed-leading day', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /preferredArchiveMonth\?: string \| null/)
  assert.match(source, /preferredArchiveDate\?: string \| null/)
  assert.match(source, /if \(options\?\.preferredTab === 'archive' && options\.preferredArchiveMonth\) \{\s*await archive\.restoreArchiveContext\(nextUserId, options\.preferredArchiveMonth, options\.preferredArchiveDate\)\s*\} else \{\s*await archive\.loadArchiveForFirstFeedDate\(nextUserId, feed\)\s*\}/s)
  assert.match(source, /const preferredArchiveMonth = view\.activeTab === 'archive' \? archive\.archiveMonth : null/)
  assert.match(source, /const preferredArchiveDate = view\.activeTab === 'archive' \? archive\.archiveDateData\?\.date \?\? null : null/)
  assert.match(source, /await loadUserState\(auth\.userId as string, \{\s*preferredTab,\s*reopenDetailArticleId,\s*preferredArchiveMonth,\s*preferredArchiveDate,\s*\}\)/s)
})
