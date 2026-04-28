import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile, mkdtemp, writeFile } from 'node:fs/promises'
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

test('getCategoryDescription uses backend category description before fallback', async () => {
  const { getCategoryDescription } = await importTsModule('src/lib/categoryDescriptions.ts')

  assert.equal(
    getCategoryDescription({ slug: 'economy', name: '경제', description: '서버가 내려준 경제 설명', subcategories: [] }),
    '서버가 내려준 경제 설명',
  )
})

test('getSubcategoryDescription uses backend subcategory description before fallback', async () => {
  const { getSubcategoryDescription } = await importTsModule('src/lib/categoryDescriptions.ts')

  assert.equal(
    getSubcategoryDescription({ slug: 'stocks', name: '주식시장', description: '서버가 내려준 주식 설명', category_slug: 'economy' }),
    '서버가 내려준 주식 설명',
  )
})

test('OnboardingScreen does not carry local mock description maps', async () => {
  const source = await readFile(path.join(projectRoot, 'src/components/screens/OnboardingScreen.tsx'), 'utf8')

  assert.doesNotMatch(source, /CATEGORY_DESCRIPTIONS/)
  assert.doesNotMatch(source, /SUBCATEGORY_DESCRIPTIONS/)
  assert.match(source, /getCategoryDescription\(category\)/)
  assert.match(source, /getSubcategoryDescription\(sub\)/)
})
