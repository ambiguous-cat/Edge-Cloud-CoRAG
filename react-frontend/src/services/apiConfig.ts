export type ApiTarget = 'local' | 'cloud'
export type RouteMode = 'auto' | ApiTarget

// 可改配置：本地后端默认地址（未配置 VITE_LOCAL_API_BASE_URL 时生效）。
const DEFAULT_LOCAL_API_BASE_URL = 'http://localhost:8005'
// 可改配置：云端后端默认地址（未配置 VITE_CLOUD_API_BASE_URL 时生效）。
const DEFAULT_CLOUD_API_BASE_URL = 'http://localhost:8005'
// 可改配置：请求默认超时时间（毫秒，未配置或无效时生效）。
const DEFAULT_TIMEOUT_MS = 20_000
// 可改配置（旧版兼容）：单一后端地址，作为 local/cloud 的公共回退值。
const LEGACY_BASE_URL = import.meta.env.VITE_API_BASE_URL

// 清理并规范化基础地址，去掉末尾斜杠，避免后续路径拼接出错。
function sanitizeBaseUrl(value: string, fallback: string): string {
  const trimmed = value.trim()
  if (!trimmed) {
    return fallback
  }

  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed
}

// 超时环境变量必须是正数；否则回退到默认超时时间。
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

// auto 路由只有显式配置为 cloud 才走云端，其他值都回退到 local。
function parseAutoTarget(rawValue: string | undefined): ApiTarget {
  if (rawValue === 'cloud') {
    return 'cloud'
  }

  return 'local'
}

// 基础地址解析优先级：
// 1) VITE_LOCAL_API_BASE_URL / VITE_CLOUD_API_BASE_URL
// 2) VITE_API_BASE_URL（兼容旧版单地址变量）
// 3) DEFAULT_*_API_BASE_URL
// 可改配置：VITE_LOCAL_API_BASE_URL（示例：http://localhost:8005）
const localBaseUrl = sanitizeBaseUrl(
  import.meta.env.VITE_LOCAL_API_BASE_URL ??
    LEGACY_BASE_URL ??
    DEFAULT_LOCAL_API_BASE_URL,
  DEFAULT_LOCAL_API_BASE_URL,
)

// 可改配置：VITE_CLOUD_API_BASE_URL（示例：https://api.example.com）
const cloudBaseUrl = sanitizeBaseUrl(
  import.meta.env.VITE_CLOUD_API_BASE_URL ??
    LEGACY_BASE_URL ??
    DEFAULT_CLOUD_API_BASE_URL,
  DEFAULT_CLOUD_API_BASE_URL,
)

// 可改配置：VITE_AUTO_ROUTE_TARGET（可选值：local | cloud，默认 local）。
const autoRouteTarget = parseAutoTarget(import.meta.env.VITE_AUTO_ROUTE_TARGET)

// 可改配置：VITE_API_TIMEOUT_MS（毫秒，需为正数）。
export const API_TIMEOUT_MS = parseTimeoutMs(import.meta.env.VITE_API_TIMEOUT_MS)

export const API_BASE_URLS: Record<ApiTarget, string> = {
  local: localBaseUrl,
  cloud: cloudBaseUrl,
}

// 服务层统一通过这个入口读取目标基础地址。
export function getApiBaseUrl(target: ApiTarget): string {
  return API_BASE_URLS[target]
}

// 手动模式优先；auto 模式按环境变量计算默认目标。
export function resolveApiTarget(mode: RouteMode): ApiTarget {
  if (mode === 'local' || mode === 'cloud') {
    return mode
  }

  return autoRouteTarget
}
