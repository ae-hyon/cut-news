import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

test('bootstrap restores remembered scraps or archive tab context when no explicit reload target is provided', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /const restoredViewContext: LoadUserStateOptions \| undefined = options \?\? \(\(\) => \{\s*const rememberedViewContext = getRememberedViewContext\(\)/s)
  assert.match(source, /preferredTab: rememberedViewContext\.tab/)
  assert.match(source, /preferredArchiveMonth: rememberedViewContext\.tab === 'archive' \? rememberedViewContext\.archiveMonth \?\? null : null/)
  assert.match(source, /preferredArchiveDate: rememberedViewContext\.tab === 'archive' \? rememberedViewContext\.archiveDate \?\? null : null/)
})

test('current non-detail tab context is persisted so refresh can reopen scraps or archive in place', async () => {
  const source = await readFile(path.join(projectRoot, 'src/hooks/usePrototypeApp.ts'), 'utf8')

  assert.match(source, /React\.useEffect\(\(\) => \{\s*if \(!auth\.userId \|\| !preference\?\.onboarding_completed \|\| view\.isDetailOpen\) return/s)
  assert.match(source, /rememberViewContext\(\{\s*tab: view\.activeTab === 'scraps' \|\| view\.activeTab === 'archive' \? view\.activeTab : 'home',/s)
  assert.match(source, /archiveMonth: view\.activeTab === 'archive' \? archive\.archiveMonth : null/)
  assert.match(source, /archiveDate: view\.activeTab === 'archive' \? archive\.archiveDateData\?\.date \?\? null : null/)
})

test('devSession exposes explicit helpers for remembering and clearing persisted view context', async () => {
  const source = await readFile(path.join(projectRoot, 'src/lib/devSession.ts'), 'utf8')

  assert.match(source, /const VIEW_CONTEXT_STORAGE_KEY = 'annoyingcap\.view-context'/)
  assert.match(source, /export function getRememberedViewContext\(\): RememberedViewContext \| null/)
  assert.match(source, /export function rememberViewContext\(context: RememberedViewContext\): void/)
  assert.match(source, /export function clearRememberedViewContext\(\): void/)
})
