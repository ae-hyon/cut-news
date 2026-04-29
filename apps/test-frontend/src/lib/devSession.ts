const DEV_DEMO_USER_STORAGE_KEY = 'annoyingcap.dev-demo-user-id'

function isDevEnvironment(): boolean {
  return (import.meta as ImportMeta & { env?: { DEV?: boolean } }).env?.DEV === true
}

export function isDevDemoEntryEnabled(search = typeof window !== 'undefined' ? window.location.search : ''): boolean {
  return isDevEnvironment() || new URLSearchParams(search).get('debug') === '1'
}

function readStorage(): Storage | null {
  if (typeof window === 'undefined') return null
  try {
    return window.localStorage
  } catch {
    return null
  }
}

export function getRememberedDemoUserId(search = typeof window !== 'undefined' ? window.location.search : ''): string | null {
  if (!isDevDemoEntryEnabled(search)) return null
  const storage = readStorage()
  return storage?.getItem(DEV_DEMO_USER_STORAGE_KEY) || null
}

export function rememberDemoUserId(userId: string, search = typeof window !== 'undefined' ? window.location.search : ''): void {
  if (!isDevDemoEntryEnabled(search)) return
  const storage = readStorage()
  storage?.setItem(DEV_DEMO_USER_STORAGE_KEY, userId)
}

export function clearRememberedDemoUserId(): void {
  const storage = readStorage()
  storage?.removeItem(DEV_DEMO_USER_STORAGE_KEY)
}
