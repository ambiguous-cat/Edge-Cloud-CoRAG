export type ApiTarget = 'local' | 'cloud'
export type RouteMode = 'auto' | ApiTarget

const DEFAULT_LOCAL_API_BASE_URL = 'http://localhost:8005'
const DEFAULT_CLOUD_API_BASE_URL = 'http://localhost:8005'
const DEFAULT_TIMEOUT_MS = 20_000
const LEGACY_BASE_URL = import.meta.env.VITE_API_BASE_URL

function sanitizeBaseUrl(value: string, fallback: string): string {
  const trimmed = value.trim()
  if (!trimmed) {
    return fallback
  }

  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed
}

function parseTimeoutMs(rawValue: string | undefined): number {
  if (!rawValue) {
    return DEFAULT_TIMEOUT_MS
  }

  const parsed = Number(rawValue)
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return DEFAULT_TIMEOUT_MS
  }

  return parsed
}

function parseAutoTarget(rawValue: string | undefined): ApiTarget {
  if (rawValue === 'cloud') {
    return 'cloud'
  }

  return 'local'
}

const localBaseUrl = sanitizeBaseUrl(
  import.meta.env.VITE_LOCAL_API_BASE_URL ??
    LEGACY_BASE_URL ??
    DEFAULT_LOCAL_API_BASE_URL,
  DEFAULT_LOCAL_API_BASE_URL,
)

const cloudBaseUrl = sanitizeBaseUrl(
  import.meta.env.VITE_CLOUD_API_BASE_URL ??
    LEGACY_BASE_URL ??
    DEFAULT_CLOUD_API_BASE_URL,
  DEFAULT_CLOUD_API_BASE_URL,
)

const autoRouteTarget = parseAutoTarget(import.meta.env.VITE_AUTO_ROUTE_TARGET)

export const API_TIMEOUT_MS = parseTimeoutMs(import.meta.env.VITE_API_TIMEOUT_MS)

export const API_BASE_URLS: Record<ApiTarget, string> = {
  local: localBaseUrl,
  cloud: cloudBaseUrl,
}

export function getApiBaseUrl(target: ApiTarget): string {
  return API_BASE_URLS[target]
}

export function resolveApiTarget(mode: RouteMode): ApiTarget {
  if (mode === 'local' || mode === 'cloud') {
    return mode
  }

  return autoRouteTarget
}
