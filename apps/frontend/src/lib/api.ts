function getApiBase() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:8030`;
  }
  return 'http://127.0.0.1:8030';
}

interface ApiOptions extends RequestInit {
  retryOnUnauthorized?: boolean;
}

async function request(path: string, options: RequestInit = {}) {
  return fetch(`${getApiBase()}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
}

async function parseResponse(response: Response) {
  const contentType = response.headers.get('content-type') || '';
  return contentType.includes('application/json')
    ? await response.json()
    : await response.text();
}

function errorMessage(data: unknown): string {
  if (typeof data !== 'object' || data === null) return String(data);

  const error = data as { message?: string; detail?: string | unknown[] };
  if (error.message) return error.message;
  if (typeof error.detail === 'string') return error.detail;
  if (Array.isArray(error.detail)) {
    return error.detail
      .map((item) => {
        if (typeof item !== 'object' || item === null) return String(item);
        const validation = item as { loc?: unknown[]; msg?: string };
        const field = Array.isArray(validation.loc)
          ? validation.loc.join('.')
          : 'field';
        return validation.msg
          ? `${field}: ${validation.msg}`
          : JSON.stringify(item);
      })
      .join('\n');
  }
  return JSON.stringify(data);
}

export async function api<T>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const { retryOnUnauthorized = true, ...requestOptions } = options;
  let response = await request(path, requestOptions);

  if (
    response.status === 401 &&
    retryOnUnauthorized &&
    path !== '/v1/auth/token/refresh'
  ) {
    const refresh = await request('/v1/auth/token/refresh', { method: 'POST' });
    if (refresh.ok) {
      response = await request(path, requestOptions);
    }
  }

  const data = await parseResponse(response);

  if (!response.ok) {
    throw new Error(errorMessage(data));
  }

  return data as T;
}

export function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
