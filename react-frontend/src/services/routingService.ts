import type { ApiTarget, RouteMode } from './apiConfig'
import { fetchApiHealthSnapshot } from './systemService'
import type { ChatHistoryMessage } from './chatService'
import { getHttpClient } from './httpClient'

const LOCAL_LABEL = '本地'
const CLOUD_LABEL = '云端'

const ROUTE_CACHE = new Map<string, ApiTarget>()

interface PrivacyCheckResponse {
  privacy_score?: unknown
  is_privacy_risk?: unknown
}

interface ComplexityRouteResponse {
  success?: unknown
  routing_result?: {
    route?: unknown
    base_route?: unknown
    explanation?: unknown
    confidence?: unknown
    recommendations?: unknown
    complexity_analysis?: {
      [key: string]: unknown
    }
  }
}

interface ComplexityRouteRequest {
  query: string
  complexity_threshold: number
}

export interface RoutingSettings {
  enableCacheCheck: boolean
  enableNetworkCheck: boolean
  enableComplexityCheck: boolean
  enablePrivacyCheck: boolean
  complexityThreshold: number
}

export interface RoutingDecision {
  target: ApiTarget
  fallbackTarget?: ApiTarget
  reason: string
  reasonLabel: string
  mode: 'manual' | 'auto'
  localAvailable: boolean
  cloudAvailable: boolean
  complexityScore?: number
  complexityAnalysis?: Record<string, number>
  complexityRoute?: string
  complexityBaseRoute?: string
  complexityExplanation?: string
  complexityConfidence?: number
  complexityRecommendations?: string[]
  privacyScore?: number
  fromCache: boolean
}

export interface DecideRouteRequest {
  routeMode: RouteMode
  query: string
  history: ChatHistoryMessage[]
  settings: RoutingSettings
}

function normalizeScore(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function normalizeString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }

  return value.filter(
    (item): item is string => typeof item === 'string' && item.trim().length > 0,
  )
}

function normalizeScoreRecord(value: unknown): Record<string, number> | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined
  }

  const result: Record<string, number> = {}
  for (const [key, score] of Object.entries(value)) {
    if (typeof score === 'number' && Number.isFinite(score)) {
      result[key] = score
    }
  }

  return Object.keys(result).length > 0 ? result : undefined
}

function normalizeRouteToTarget(route: unknown): ApiTarget | null {
  if (typeof route !== 'string') {
    return null
  }

  if (route.startsWith('cloud')) {
    return 'cloud'
  }

  if (route.startsWith('local')) {
    return 'local'
  }

  return null
}

function cacheKey(query: string): string {
  return query.trim().toLowerCase()
}

function getCacheTarget(query: string): ApiTarget | null {
  const key = cacheKey(query)
  return ROUTE_CACHE.get(key) ?? null
}

function isTargetAvailable(
  target: ApiTarget,
  localAvailable: boolean,
  cloudAvailable: boolean,
): boolean {
  return target === 'local' ? localAvailable : cloudAvailable
}

function getAlternateTarget(target: ApiTarget): ApiTarget {
  return target === 'local' ? 'cloud' : 'local'
}

function selectFallbackTarget(
  target: ApiTarget,
  localAvailable: boolean,
  cloudAvailable: boolean,
): ApiTarget | undefined {
  const alternate = getAlternateTarget(target)
  return isTargetAvailable(alternate, localAvailable, cloudAvailable)
    ? alternate
    : undefined
}

function finalizeDecision(
  target: ApiTarget,
  reason: string,
  reasonLabel: string,
  localAvailable: boolean,
  cloudAvailable: boolean,
  mode: 'manual' | 'auto',
  options?: {
    complexityScore?: number
    complexityAnalysis?: Record<string, number>
    complexityRoute?: string
    complexityBaseRoute?: string
    complexityExplanation?: string
    complexityConfidence?: number
    complexityRecommendations?: string[]
    privacyScore?: number
    fromCache?: boolean
  },
): RoutingDecision {
  return {
    target,
    fallbackTarget: selectFallbackTarget(target, localAvailable, cloudAvailable),
    reason,
    reasonLabel,
    mode,
    localAvailable,
    cloudAvailable,
    complexityScore: options?.complexityScore,
    complexityAnalysis: options?.complexityAnalysis,
    complexityRoute: options?.complexityRoute,
    complexityBaseRoute: options?.complexityBaseRoute,
    complexityExplanation: options?.complexityExplanation,
    complexityConfidence: options?.complexityConfidence,
    complexityRecommendations: options?.complexityRecommendations,
    privacyScore: options?.privacyScore,
    fromCache: options?.fromCache === true,
  }
}

async function evaluatePrivacyRisk(
  query: string,
  history: ChatHistoryMessage[],
): Promise<{ risk: boolean; score?: number }> {
  const chatHistory = [...history, { role: 'user', content: query }]
  try {
    const { data } = await getHttpClient('local').post<PrivacyCheckResponse>(
      '/privacy_check',
      {
        chat_history: chatHistory,
        get_details: false,
      },
    )

    const score = normalizeScore(data?.privacy_score)
    return {
      risk: data?.is_privacy_risk === true,
      score,
    }
  } catch {
    return { risk: false }
  }
}

async function evaluateComplexityRoute(
  query: string,
  complexityThreshold: number,
): Promise<{
  target: ApiTarget | null
  score?: number
  analysis?: Record<string, number>
  route?: string
  baseRoute?: string
  explanation?: string
  confidence?: number
  recommendations?: string[]
}> {
  try {
    const { data } = await getHttpClient('local').post<ComplexityRouteResponse>(
      '/complexity/route',
      {
        query,
        complexity_threshold: complexityThreshold,
      } satisfies ComplexityRouteRequest,
    )

    const routingResult = data?.routing_result
    const route = normalizeString(routingResult?.route)
    const analysis = normalizeScoreRecord(routingResult?.complexity_analysis)
    const routeTarget = normalizeRouteToTarget(route)
    const score = normalizeScore(analysis?.total_complexity)

    return {
      target: routeTarget,
      score,
      analysis,
      route,
      baseRoute: normalizeString(routingResult?.base_route),
      explanation: normalizeString(routingResult?.explanation),
      confidence: normalizeScore(routingResult?.confidence),
      recommendations: normalizeStringList(routingResult?.recommendations),
    }
  } catch {
    return {
      target: null,
    }
  }
}

function chooseByAvailability(
  preferred: ApiTarget,
  localAvailable: boolean,
  cloudAvailable: boolean,
): ApiTarget {
  if (isTargetAvailable(preferred, localAvailable, cloudAvailable)) {
    return preferred
  }

  const alternate = getAlternateTarget(preferred)
  if (isTargetAvailable(alternate, localAvailable, cloudAvailable)) {
    return alternate
  }

  return preferred
}

function targetLabel(target: ApiTarget): string {
  return target === 'local' ? LOCAL_LABEL : CLOUD_LABEL
}

function buildFallbackReasonLabel(preferred: ApiTarget, actual: ApiTarget): string {
  return `目标 ${targetLabel(preferred)} 不可用，自动回退到 ${targetLabel(actual)}`
}

export function rememberRouteDecision(query: string, target: ApiTarget): void {
  const key = cacheKey(query)
  if (!key) {
    return
  }
  ROUTE_CACHE.set(key, target)
}

export async function decideRoute({
  routeMode,
  query,
  history,
  settings,
}: DecideRouteRequest): Promise<RoutingDecision> {
  if (routeMode === 'local' || routeMode === 'cloud') {
    return finalizeDecision(
      routeMode,
      'manual_selected',
      `手动选择${targetLabel(routeMode)}模式`,
      true,
      true,
      'manual',
    )
  }

  let localAvailable = true
  let cloudAvailable = true

  if (settings.enableNetworkCheck) {
    const networkSnapshot = await fetchApiHealthSnapshot()
    localAvailable = networkSnapshot.localApiOnline
    cloudAvailable = networkSnapshot.cloudApiOnline
  }

  if (settings.enableCacheCheck) {
    const cachedTarget = getCacheTarget(query)
    if (cachedTarget) {
      const actualTarget = chooseByAvailability(
        cachedTarget,
        localAvailable,
        cloudAvailable,
      )
      const reasonLabel =
        actualTarget === cachedTarget
          ? `命中缓存路由：${targetLabel(actualTarget)}`
          : buildFallbackReasonLabel(cachedTarget, actualTarget)
      return finalizeDecision(
        actualTarget,
        'cache_hit',
        reasonLabel,
        localAvailable,
        cloudAvailable,
        'auto',
        { fromCache: true },
      )
    }
  }

  if (settings.enablePrivacyCheck) {
    const privacy = await evaluatePrivacyRisk(query, history)
    if (privacy.risk) {
      const actualTarget = chooseByAvailability(
        'local',
        localAvailable,
        cloudAvailable,
      )
      const reasonLabel =
        actualTarget === 'local'
          ? '命中隐私保护策略，优先本地处理'
          : buildFallbackReasonLabel('local', actualTarget)
      return finalizeDecision(
        actualTarget,
        'privacy_protection',
        reasonLabel,
        localAvailable,
        cloudAvailable,
        'auto',
        { privacyScore: privacy.score },
      )
    }
  }

  if (settings.enableComplexityCheck) {
    const complexity = await evaluateComplexityRoute(
      query,
      settings.complexityThreshold,
    )
    let preferredTarget: ApiTarget = 'cloud'
    if (complexity.score !== undefined) {
      preferredTarget =
        complexity.score > settings.complexityThreshold ? 'cloud' : 'local'
    } else if (complexity.target) {
      preferredTarget = complexity.target
    }

    const actualTarget = chooseByAvailability(
      preferredTarget,
      localAvailable,
      cloudAvailable,
    )
    const scoreDetail =
      complexity.score !== undefined
        ? `（复杂度 ${complexity.score.toFixed(2)}，阈值 ${settings.complexityThreshold.toFixed(2)}）`
        : ''
    const reasonLabel =
      actualTarget === preferredTarget
        ? `复杂度策略建议${targetLabel(actualTarget)}处理${scoreDetail}`
        : `${buildFallbackReasonLabel(preferredTarget, actualTarget)}${scoreDetail}`
    return finalizeDecision(
      actualTarget,
      'complexity_routing',
      reasonLabel,
      localAvailable,
      cloudAvailable,
      'auto',
      {
        complexityScore: complexity.score,
        complexityAnalysis: complexity.analysis,
        complexityRoute: complexity.route,
        complexityBaseRoute: complexity.baseRoute,
        complexityExplanation: complexity.explanation,
        complexityConfidence: complexity.confidence,
        complexityRecommendations: complexity.recommendations,
      },
    )
  }

  const defaultPreferredTarget: ApiTarget = cloudAvailable ? 'cloud' : 'local'
  const defaultTarget = chooseByAvailability(
    defaultPreferredTarget,
    localAvailable,
    cloudAvailable,
  )
  const reasonLabel =
    defaultTarget === defaultPreferredTarget
      ? `默认策略：优先${targetLabel(defaultTarget)}`
      : buildFallbackReasonLabel(defaultPreferredTarget, defaultTarget)

  return finalizeDecision(
    defaultTarget,
    'default_auto',
    reasonLabel,
    localAvailable,
    cloudAvailable,
    'auto',
  )
}
