import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import { mkdtemp, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import ts from 'typescript'

const projectRoot = path.resolve(import.meta.dirname, '..')

async function importTsModule(relativePath) {
  const sourcePath = path.join(projectRoot, relativePath)
  const source = await readFile(sourcePath, 'utf8')
  const transpiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2020,
      jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText
  const tempDir = await mkdtemp(path.join(tmpdir(), 'annoying-cap-test-'))
  const tempPath = path.join(tempDir, path.basename(relativePath).replace(/\.ts$/, '.mjs'))
  await writeFile(tempPath, transpiled)
  return import(tempPath)
}

test('formatPreferenceSummary labels narrow subcategory slugs with subcategory names', async () => {
  const { formatPreferenceSummary } = await importTsModule('src/lib/preferenceLabels.ts')
  const categories = [
    {
      slug: 'economy',
      name: '경제',
      subcategories: [
        { slug: 'stocks', name: '주식시장' },
        { slug: 'real-estate', name: '부동산' },
      ],
    },
  ]

  assert.equal(
    formatPreferenceSummary('narrow', { primary_categories: ['economy'], subcategories: ['stocks'] }, categories),
    '주식시장',
  )
})

test('formatPreferenceSummary labels wide category slugs with category names', async () => {
  const { formatPreferenceSummary } = await importTsModule('src/lib/preferenceLabels.ts')
  const categories = [
    { slug: 'economy', name: '경제', subcategories: [] },
    { slug: 'politics', name: '정치', subcategories: [] },
    { slug: 'entertainment', name: '연예', subcategories: [] },
  ]

  assert.equal(
    formatPreferenceSummary('wide', { primary_categories: ['economy', 'politics', 'entertainment'], subcategories: [] }, categories),
    '경제 · 정치 · 연예',
  )
})

test('onboarding complete chips route mode editing and selection editing separately', async () => {
  const completeScreen = await readFile(path.join(projectRoot, 'src/components/screens/OnboardingCompleteScreen.tsx'), 'utf8')
  const app = await readFile(path.join(projectRoot, 'src/App.tsx'), 'utf8')

  assert.match(completeScreen, /onEditMode: \(\) => void/)
  assert.match(completeScreen, /onEditSelection: \(\) => void/)
  assert.match(completeScreen, /onClick=\{onEditMode\}>\{mode === 'wide'/)
  assert.match(completeScreen, /onClick=\{onEditSelection\}>\{summaryChip\}/)
  assert.match(app, /onEditMode=\{app\.restartIntroFlow\}/)
  assert.match(app, /onEditSelection=\{app\.editCompletedPreferences\}/)
})
