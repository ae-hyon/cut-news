export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const message = typeof data === 'object' && data !== null
      ? ((data as { message?: string; detail?: string }).message || (data as { message?: string; detail?: string }).detail || JSON.stringify(data))
      : String(data)
    throw new Error(message)
  }

  return data as T
}

export function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}
