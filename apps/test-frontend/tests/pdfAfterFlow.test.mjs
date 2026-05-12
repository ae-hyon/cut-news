import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

const projectRoot = path.resolve(import.meta.dirname, '..')

async function source(relativePath) {
  return readFile(path.join(projectRoot, relativePath), 'utf8')
}

test('top bar includes the PDF profile pill, active text navigation, and preference-edit entry wiring', async () => {
  const topBar = await source('src/components/layout/TopBar.tsx')
  const app = await source('src/App.tsx')

  assert.match(topBar, /profilePill\?: string/)
  assert.match(topBar, /onProfileClick\?: \(\) => void/)
  assert.match(topBar, /className="profile-pill"/)
  assert.match(topBar, /onClick=\{onProfileClick\}/)
  assert.match(topBar, /선우/)
  assert.match(app, /profilePill="선우"/)
  assert.match(app, /onProfileClick=\{app\.editCompletedPreferences\}/)
})

test('home and scraps use PDF-style masonry card boards', async () => {
  const home = await source('src/components/screens/HomeScreen.tsx')
  const app = await source('src/App.tsx')
  const scraps = await source('src/components/screens/ScrapsScreen.tsx')
  const css = await source('src/styles/screens.css')

  assert.match(home, /className="pdf-card-board home-card-board"/)
  assert.match(home, /onEditPreference: \(\) => void/)
  assert.match(home, /const emptyMessage = preference\?\.onboarding_completed/)
  assert.match(home, /선택한 관심사에 맞는 뉴스가 아직 없어요\./)
  assert.match(home, /관심사를 선택하면 뉴스가 표시됩니다\./)
  assert.match(home, /상단 선택 버튼에서 관심 분야를 다시 조정해보세요\./)
  assert.match(home, /home-empty-helper/)
  assert.match(home, /<button onClick=\{onEditPreference\}>선택<\/button>/)
  assert.match(app, /onEditPreference=\{app\.editCompletedPreferences\}/)
  assert.match(scraps, /className="pdf-card-board scraps-card-board"/)
  assert.match(scraps, /관심 분야를 바꿔도, 저장한 기사는 여기서 다시 볼 수 있어요\./)
  assert.match(css, /\.pdf-card-board/) 
  assert.match(css, /grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/)
  assert.match(css, /\.news-card\.size-feature/) 
})

test('detail screen matches PDF summary-card plus action-row structure', async () => {
  const detail = await source('src/components/screens/DetailScreen.tsx')
  const constants = await source('src/lib/constants.ts')
  const css = await source('src/styles/screens.css')

  assert.match(detail, /detail-close-button/)
  assert.match(detail, /detail-summary-card/)
  assert.match(detail, /detail-meta-row/)
  assert.match(detail, /detail-action-row/)
  assert.match(detail, /원문 보기/)
  assert.match(detail, /toSubcategoryLabel\(article\.subcategory\)/)
  assert.match(detail, /현재 관심사 밖에 있지만, 저장하거나 원문으로 계속 확인할 수 있어요\./)
  assert.match(constants, /'economy-finance': '금융'/)
  assert.match(constants, /'stock-domestic': '국내주식'/)
  assert.match(css, /\.detail-summary-card/)
  assert.match(css, /\.detail-action-row/)
  assert.match(css, /\.detail-preference-mismatch/)
})

test('archive screen renders PDF calendar first and date-specific board as a dismissible panel', async () => {
  const archive = await source('src/components/screens/ArchiveScreen.tsx')
  const css = await source('src/styles/screens.css')

  assert.match(archive, /나의 뉴스 아카이브/)
  assert.match(archive, /월간 이력/)
  assert.match(archive, /archive-calendar-grid/)
  assert.match(archive, /archive-date-panel/)
  assert.match(archive, /archive-date-close/)
  assert.match(archive, /archive-empty-state/)
  assert.match(archive, /선택한 관심사에 맞는 아카이브 뉴스가 아직 없어요\./)
  assert.match(archive, /이 날짜에는 관심사에 맞는 아카이브 뉴스가 없어요\./)
  assert.match(archive, /pdf-card-board archive-date-board/)
  assert.match(css, /\.archive-calendar-grid/)
  assert.match(css, /\.calendar-day\.has-items/)
  assert.match(css, /\.archive-date-panel/)
})
