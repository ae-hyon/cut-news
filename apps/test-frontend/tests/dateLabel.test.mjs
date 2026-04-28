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

test('formatDateLabel renders yy.mm.dd from the provided date', async () => {
  const { formatDateLabel } = await importTsModule('src/lib/dateLabel.ts')

  assert.equal(formatDateLabel(new Date(2026, 3, 28)), '26.04.28')
  assert.equal(formatDateLabel(new Date(2026, 0, 7)), '26.01.07')
})

test('top bar screens use the dynamic date label instead of the fixed PDF date', async () => {
  const files = [
    'src/components/layout/TopBar.tsx',
    'src/components/screens/IntroScreen.tsx',
    'src/components/screens/OnboardingScreen.tsx',
    'src/components/screens/OnboardingCompleteScreen.tsx',
    'src/components/screens/DetailScreen.tsx',
  ]

  for (const relativePath of files) {
    const source = await readFile(path.join(projectRoot, relativePath), 'utf8')
    assert.doesNotMatch(source, /26\.04\.07/)
    assert.match(source, /formatDateLabel\(\)/)
  }
})
