import { Button, Layout, Popconfirm, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { ChatComposer } from '../components/chat/ChatComposer'
import { ChatMessageList } from '../components/chat/ChatMessageList'
import { ModelSelectorSection } from '../components/chat/ModelSelectorSection'
import { NetworkStatusSection } from '../components/chat/NetworkStatusSection'
import { PrivacySection } from '../components/chat/PrivacySection'
import { ResponseDetailModal } from '../components/chat/ResponseDetailModal'
import { SettingsSection } from '../components/chat/SettingsSection'
import type {
  ChatMessage,
  ComplexityDetailState,
  ModelOption,
  NetworkState,
  ResponseDetailState,
  SettingsState,
} from '../components/chat/types'
import {
  ApiClientError,
  RagStreamError,
  clearRouteDecisionCache,
  createPrivacyKeyword,
  deletePrivacyKeyword,
  decideRoute,
  fetchApiHealthSnapshot,
  fetchPrivacyKeywords,
  rememberRouteDecision,
  streamRagChat,
  type ApiTarget,
  type ChatHistoryMessage,
  type RagStreamInfoEvent,
  type RouteMode,
  type RoutingDecision,
} from '../services'
import '../styles/chat-page.css'

const { Sider, Content } = Layout
const { Title, Text } = Typography

const INITIAL_SETTINGS: SettingsState = {
  similarityThreshold: 0.75,
  retrievalCount: 3,
  complexityThreshold: 0.65,
  enableCacheCheck: true,
  enableNetworkCheck: true,
  enableComplexityCheck: true,
  enablePrivacyCheck: true,
}

const SETTINGS_SESSION_KEY = 'rag_settings_v1'
const MESSAGES_STORAGE_KEY = 'rag_chat_messages_v1'

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'assistant-0',
    role: 'assistant',
    content: '欢迎使用端云协同 RAG 聊天系统，当前前端已支持流式增量输出。',
    createdAt: '09:30:00',
  },
]

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isChatMessage(value: unknown): value is ChatMessage {
  if (!isPlainRecord(value)) {
    return false
  }

  return (
    typeof value.id === 'string' &&
    (value.role === 'user' || value.role === 'assistant') &&
    typeof value.content === 'string' &&
    typeof value.createdAt === 'string'
  )
}

const RECOVERABLE_STREAM_ERROR_CODES = new Set([
  'http',
  'network',
  'timeout',
  'unexpected_end',
])

function nowTime() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

function normalizeThreshold(value: unknown, fallback: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback
  }

  if (value < 0) {
    return 0
  }

  if (value > 1) {
    return 1
  }

  return value
}

function normalizeRetrievalCount(value: unknown, fallback: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback
  }

  const rounded = Math.round(value)
  if (rounded < 1) {
    return 1
  }
  if (rounded > 10) {
    return 10
  }
  return rounded
}

function normalizeBoolean(value: unknown, fallback: boolean): boolean {
  return typeof value === 'boolean' ? value : fallback
}

function loadSettingsFromSession(): SettingsState {
  if (typeof window === 'undefined') {
    return INITIAL_SETTINGS
  }

  const rawValue = window.sessionStorage.getItem(SETTINGS_SESSION_KEY)
  if (!rawValue) {
    return INITIAL_SETTINGS
  }

  try {
    const parsed = JSON.parse(rawValue) as unknown
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return INITIAL_SETTINGS
    }

    const value = parsed as Record<string, unknown>
    return {
      similarityThreshold: normalizeThreshold(
        value.similarityThreshold,
        INITIAL_SETTINGS.similarityThreshold,
      ),
      retrievalCount: normalizeRetrievalCount(
        value.retrievalCount,
        INITIAL_SETTINGS.retrievalCount,
      ),
      complexityThreshold: normalizeThreshold(
        value.complexityThreshold,
        INITIAL_SETTINGS.complexityThreshold,
      ),
      enableCacheCheck: normalizeBoolean(
        value.enableCacheCheck,
        INITIAL_SETTINGS.enableCacheCheck,
      ),
      enableNetworkCheck: normalizeBoolean(
        value.enableNetworkCheck,
        INITIAL_SETTINGS.enableNetworkCheck,
      ),
      enableComplexityCheck: normalizeBoolean(
        value.enableComplexityCheck,
        INITIAL_SETTINGS.enableComplexityCheck,
      ),
      enablePrivacyCheck: normalizeBoolean(
        value.enablePrivacyCheck,
        INITIAL_SETTINGS.enablePrivacyCheck,
      ),
    }
  } catch {
    return INITIAL_SETTINGS
  }
}

function loadMessagesFromStorage(): ChatMessage[] {
  if (typeof window === 'undefined') {
    return INITIAL_MESSAGES
  }

  const rawValue = window.localStorage.getItem(MESSAGES_STORAGE_KEY)
  if (!rawValue) {
    return INITIAL_MESSAGES
  }

  try {
    const parsed = JSON.parse(rawValue) as unknown
    if (!Array.isArray(parsed)) {
      return INITIAL_MESSAGES
    }

    const storedMessages = parsed.filter(isChatMessage)
    return storedMessages.length > 0 ? storedMessages : INITIAL_MESSAGES
  } catch {
    return INITIAL_MESSAGES
  }
}

function toRouteMode(model: ModelOption): RouteMode {
  if (model === 'cloud') {
    return 'cloud'
  }

  if (model === 'local') {
    return 'local'
  }

  return 'auto'
}

function buildHistory(messages: ChatMessage[]): ChatHistoryMessage[] {
  return messages
    .filter((message) => message.id !== 'assistant-0')
    .filter((message) => message.content.trim().length > 0)
    .map(({ role, content }) => ({ role, content }))
}

function getErrorMessage(error: unknown, routeMode?: RouteMode): string {
  if (error instanceof RagStreamError) {
    if (routeMode === 'cloud' && error.target === 'cloud') {
      if (error.code === 'timeout') {
        return `${error.message} 当前为手动云端模式，不会自动切换到本地；可切换为自动模式或本地模式后重试。`
      }

      if (error.code === 'network') {
        return `${error.message} 当前为手动云端模式，请先刷新网络状态或切换为自动/本地模式。`
      }

      return `${error.message} 当前为手动云端模式，请确认云端服务可用后重试。`
    }

    if (routeMode === 'local' && error.target === 'local') {
      return `${error.message} 当前为手动本地模式，请确认本地后端可用后重试。`
    }

    return error.message
  }

  if (error instanceof Error && error.message.trim()) {
    return `请求失败：${error.message}`
  }

  return '请求失败，请稍后重试。'
}

function getApiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiClientError) {
    return error.message
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message
  }

  return fallback
}

function shouldRetryInAutoMode(routeMode: RouteMode, error: unknown): boolean {
  if (routeMode !== 'auto') {
    return false
  }

  if (!(error instanceof RagStreamError)) {
    return false
  }

  return RECOVERABLE_STREAM_ERROR_CODES.has(error.code)
}

function getAutoFallbackNotice(error: unknown, fallbackTarget: ApiTarget): string {
  if (error instanceof RagStreamError) {
    const source = toTargetLabel(error.target)
    const fallback = toTargetLabel(fallbackTarget)
    if (error.code === 'timeout') {
      return `[自动回退] ${source}请求超时，切换到${fallback}继续处理。`
    }

    if (error.code === 'network') {
      return `[自动回退] ${source}连接中断，切换到${fallback}继续处理。`
    }

    if (error.code === 'http') {
      return `[自动回退] ${source}服务返回错误，切换到${fallback}继续处理。`
    }
  }

  return `[自动回退] 主路由中断，切换到${toTargetLabel(fallbackTarget)}重试。`
}

function toTargetLabel(target: ApiTarget): string {
  return target === 'local' ? '本地' : '云端'
}

function toRouteStatusText(decision: RoutingDecision): string {
  const details: string[] = []
  details.push(`路由：${toTargetLabel(decision.target)}`)
  details.push(`原因：${decision.reasonLabel}`)

  if (decision.privacyScore !== undefined) {
    details.push(`隐私分：${decision.privacyScore.toFixed(2)}`)
  }

  if (decision.complexityScore !== undefined) {
    details.push(`复杂度：${decision.complexityScore.toFixed(2)}`)
  }

  return details.join(' ｜ ')
}

function buildComplexityDetail(
  query: string,
  model: ModelOption,
  decision: RoutingDecision,
  threshold: number,
  historyPreview: ChatHistoryMessage[],
): ComplexityDetailState {
  return {
    query,
    model,
    routeLabel: toTargetLabel(decision.target),
    reasonLabel: decision.reasonLabel,
    threshold,
    score: decision.complexityScore,
    confidence: decision.complexityConfidence,
    route: decision.complexityRoute,
    baseRoute: decision.complexityBaseRoute,
    explanation: decision.complexityExplanation,
    recommendations: decision.complexityRecommendations ?? [],
    analysis: decision.complexityAnalysis ?? {},
    historyPreview,
  }
}

function toStreamInfoText(
  responseTime?: number,
  charCount?: number,
  chunkCount?: number,
) {
  const parts: string[] = []
  if (responseTime !== undefined) {
    parts.push(`首字响应 ${responseTime.toFixed(2)} 秒`)
  }
  if (charCount !== undefined) {
    parts.push(`输出 ${charCount} 字`)
  }
  if (chunkCount !== undefined) {
    parts.push(`分片 ${chunkCount}`)
  }
  return parts.length > 0 ? `流式统计：${parts.join('，')}` : ''
}

function buildResponseDetail(event: RagStreamInfoEvent): ResponseDetailState {
  return {
    responseTime: event.responseTime,
    charCount: event.charCount,
    estimatedTokens: event.estimatedTokens,
    chunkCount: event.chunkCount,
    retrievedDocuments: event.retrievedDocuments,
    contextLength: event.contextLength,
    filterStats: event.filterStats,
    paperSearch: event.paperSearch
      ? {
          status: event.paperSearch.errors.length > 0 ? 'failed' : 'completed',
          queries: event.paperSearch.queries,
          papers: event.paperSearch.papers,
          paperCount: event.paperSearch.paperCount,
          errors: event.paperSearch.errors,
        }
      : undefined,
    localRetrieval:
      event.paperSearch && event.paperSearch.localDocuments.length > 0
        ? {
            retrievedDocuments: event.paperSearch.localDocuments,
          }
        : undefined,
  }
}

function mergeUniqueStrings(current: string[], next: string[]): string[] {
  return Array.from(new Set([...current, ...next]))
}

function mergePaperSearch(
  current: ResponseDetailState['paperSearch'],
  next: NonNullable<ResponseDetailState['paperSearch']>,
): NonNullable<ResponseDetailState['paperSearch']> {
  const paperMap = new Map<string, NonNullable<ResponseDetailState['paperSearch']>['papers'][number]>()

  for (const paper of [...(current?.papers ?? []), ...next.papers]) {
    const key = paper.id ?? paper.url ?? paper.title
    paperMap.set(key, paper)
  }

  return {
    status: next.status,
    elapsed: next.elapsed ?? current?.elapsed,
    queries: mergeUniqueStrings(current?.queries ?? [], next.queries),
    reason: next.reason ?? current?.reason,
    papers: Array.from(paperMap.values()),
    paperCount: next.paperCount ?? current?.paperCount,
    errors: mergeUniqueStrings(current?.errors ?? [], next.errors),
  }
}

function buildInitialResponseDetail(
  decision: RoutingDecision,
  complexityDetail: ComplexityDetailState,
): ResponseDetailState {
  return {
    retrievedDocuments: [],
    routeLabel: toTargetLabel(decision.target),
    reasonLabel: decision.reasonLabel,
    privacyScore: decision.privacyScore,
    privacyChecked: decision.privacyChecked,
    privacyRisk: decision.reason === 'privacy_protection',
    complexityDetail,
  }
}

function buildNetworkStatusText(status: {
  localApiOnline: boolean
  cloudApiOnline: boolean
}): string {
  if (status.localApiOnline && status.cloudApiOnline) {
    return '本地与云端 API 连接正常。'
  }

  if (status.localApiOnline && !status.cloudApiOnline) {
    return '云端 API 当前不可用，请检查云端服务。'
  }

  if (!status.localApiOnline && status.cloudApiOnline) {
    return '本地 API 当前不可用，请检查本地后端。'
  }

  return '本地与云端 API 均不可用，请检查服务或网络后重试。'
}

interface StreamConsumeResult {
  receivedContent: boolean
  receivedDone: boolean
  serverErrorMessage: string
}

export function ChatPage() {
  const [model, setModel] = useState<ModelOption>('auto')
  const [networkStatus, setNetworkStatus] = useState<NetworkState>({
    localApiOnline: false,
    cloudApiOnline: false,
    lastChecked: '未检查',
  })
  const [networkStatusText, setNetworkStatusText] = useState<string>(
    '点击刷新以检测连接状态。',
  )
  const [isNetworkRefreshing, setIsNetworkRefreshing] = useState<boolean>(false)
  const [settingsOpen, setSettingsOpen] = useState<boolean>(true)
  const [privacyOpen, setPrivacyOpen] = useState<boolean>(true)
  const [settings, setSettings] = useState<SettingsState>(() =>
    loadSettingsFromSession(),
  )
  const [keywordInput, setKeywordInput] = useState<string>('')
  const [keywords, setKeywords] = useState<string[]>([])
  const [privacyStatusText, setPrivacyStatusText] = useState<string>('')
  const [isPrivacyAdding, setIsPrivacyAdding] = useState<boolean>(false)
  const [deletingKeyword, setDeletingKeyword] = useState<string | null>(null)
  const [isPrivacyRefreshing, setIsPrivacyRefreshing] = useState<boolean>(false)
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    loadMessagesFromStorage(),
  )
  const [composerText, setComposerText] = useState<string>('')
  const [routeStatusText, setRouteStatusText] = useState<string>('')
  const [streamInfoText, setStreamInfoText] = useState<string>('')
  const [selectedResponseDetail, setSelectedResponseDetail] =
    useState<ResponseDetailState | null>(null)
  const [responseModalOpen, setResponseModalOpen] = useState<boolean>(false)
  const [isSending, setIsSending] = useState<boolean>(false)

  const canSend = useMemo(
    () => composerText.trim().length > 0 && !isSending,
    [composerText, isSending],
  )

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    try {
      window.sessionStorage.setItem(SETTINGS_SESSION_KEY, JSON.stringify(settings))
    } catch {
      // Ignore storage failures and keep in-memory settings available.
    }
  }, [settings])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    try {
      window.localStorage.setItem(MESSAGES_STORAGE_KEY, JSON.stringify(messages))
    } catch {
      // Ignore storage failures; the in-memory chat still remains usable.
    }
  }, [messages])

  const refreshNetworkStatus = useCallback(async () => {
    setIsNetworkRefreshing(true)
    setNetworkStatusText('正在检查本地与云端 API 状态...')

    try {
      const snapshot = await fetchApiHealthSnapshot()
      const checkedAt = nowTime()

      setNetworkStatus({
        ...snapshot,
        lastChecked: checkedAt,
      })
      setNetworkStatusText(`${buildNetworkStatusText(snapshot)}（${checkedAt}）`)
    } catch {
      setNetworkStatusText('刷新失败：无法获取网络状态，请稍后重试。')
    } finally {
      setIsNetworkRefreshing(false)
    }
  }, [])

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      void refreshNetworkStatus()
    }, 0)

    return () => {
      window.clearTimeout(timerId)
    }
  }, [refreshNetworkStatus])

  const refreshPrivacyKeywords = useCallback(
    async (customSuccessMessage?: string) => {
      setIsPrivacyRefreshing(true)
      setPrivacyStatusText('正在刷新关键词列表...')

      try {
        const nextKeywords = await fetchPrivacyKeywords()
        setKeywords(nextKeywords)
        setPrivacyStatusText(
          customSuccessMessage ??
            `关键词列表已刷新，共 ${nextKeywords.length} 项（${nowTime()}）。`,
        )
      } catch (error) {
        setPrivacyStatusText(
          `刷新失败：${getApiErrorMessage(error, '请检查本地服务后重试。')}`,
        )
      } finally {
        setIsPrivacyRefreshing(false)
      }
    },
    [],
  )

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      void refreshPrivacyKeywords()
    }, 0)

    return () => {
      window.clearTimeout(timerId)
    }
  }, [refreshPrivacyKeywords])

  const addPrivacyKeyword = async () => {
    const trimmed = keywordInput.trim()
    if (!trimmed) {
      setPrivacyStatusText('请输入关键词后再提交。')
      return
    }

    if (keywords.includes(trimmed)) {
      setPrivacyStatusText('该关键词已存在。')
      return
    }

    setIsPrivacyAdding(true)
    try {
      const successMessage = await createPrivacyKeyword(trimmed)
      setKeywordInput('')
      await refreshPrivacyKeywords(`${successMessage}（${nowTime()}）`)
    } catch (error) {
      setPrivacyStatusText(
        `新增失败：${getApiErrorMessage(error, '请检查服务状态后重试。')}`,
      )
    } finally {
      setIsPrivacyAdding(false)
    }
  }

  const handleRefreshPrivacyKeywords = () => {
    void refreshPrivacyKeywords()
  }

  const removePrivacyKeyword = async (keyword: string) => {
    setDeletingKeyword(keyword)
    setPrivacyStatusText(`正在删除关键词“${keyword}”...`)

    try {
      const successMessage = await deletePrivacyKeyword(keyword)
      await refreshPrivacyKeywords(`${successMessage}（${nowTime()}）`)
    } catch (error) {
      setPrivacyStatusText(
        `删除失败：${getApiErrorMessage(error, '请检查服务状态后重试。')}`,
      )
    } finally {
      setDeletingKeyword(null)
    }
  }

  const clearMessages = () => {
    setMessages(INITIAL_MESSAGES)
    setRouteStatusText('')
    setStreamInfoText('')
    setSelectedResponseDetail(null)
    setResponseModalOpen(false)
    clearRouteDecisionCache()

    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(MESSAGES_STORAGE_KEY)
    }
  }

  const sendMessage = async () => {
    if (!canSend) {
      return
    }

    const content = composerText.trim()
    const routeMode = toRouteMode(model)
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      createdAt: nowTime(),
    }
    const assistantMessageId = `assistant-${Date.now() + 1}`
    const pendingAssistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      createdAt: nowTime(),
    }

    const history = buildHistory(messages)
    const historyPreview: ChatHistoryMessage[] = [
      ...history,
      { role: 'user', content },
    ]

    setMessages((current) => [...current, userMessage, pendingAssistantMessage])
    setComposerText('')
    setRouteStatusText('')
    setStreamInfoText('')
    setIsSending(true)

    const appendAssistantError = (errorMessage: string) => {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                content:
                  message.content.trim().length > 0
                    ? `${message.content}\n\n[流式中断] ${errorMessage}`
                    : errorMessage,
                createdAt: nowTime(),
              }
            : message,
        ),
      )
    }

    const updateAssistantResponseDetail = (
      updater: (current: ResponseDetailState | undefined) => ResponseDetailState,
    ) => {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                responseDetail: updater(message.responseDetail),
              }
            : message,
        ),
      )
    }

    const consumeStream = async (target: ApiTarget): Promise<StreamConsumeResult> => {
      let receivedContent = false
      let receivedDone = false
      let serverErrorMessage = ''

      for await (const event of streamRagChat({
        query: content,
        routeMode,
        target,
        topK: settings.retrievalCount,
        similarityThreshold: settings.similarityThreshold,
        history,
      })) {
        if (event.type === 'content') {
          if (!event.content) {
            continue
          }

          receivedContent = true
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, content: `${message.content}${event.content}` }
                : message,
            ),
          )
          continue
        }

        if (event.type === 'info') {
          const nextResponseDetail = buildResponseDetail(event)
          setStreamInfoText(
            toStreamInfoText(event.responseTime, event.charCount, event.chunkCount),
          )
          updateAssistantResponseDetail((current) => ({
            ...current,
            ...nextResponseDetail,
            paperSearch: nextResponseDetail.paperSearch
              ? mergePaperSearch(current?.paperSearch, nextResponseDetail.paperSearch)
              : current?.paperSearch,
            localRetrieval:
              nextResponseDetail.localRetrieval ?? current?.localRetrieval,
          }))
          continue
        }

        if (event.type === 'tool_start') {
          setStreamInfoText('正在检索论文...')
          updateAssistantResponseDetail((current) => ({
            retrievedDocuments: current?.retrievedDocuments ?? [],
            ...current,
            paperSearch: mergePaperSearch(current?.paperSearch, {
              status: 'running',
              queries: [],
              papers: [],
              errors: [],
            }),
          }))
          continue
        }

        if (event.type === 'tool_progress') {
          const elapsedText =
            event.elapsed === undefined ? '' : `（${event.elapsed.toFixed(0)} 秒）`
          setStreamInfoText(`正在检索论文${elapsedText}...`)
          updateAssistantResponseDetail((current) => ({
            retrievedDocuments: current?.retrievedDocuments ?? [],
            ...current,
            paperSearch: mergePaperSearch(current?.paperSearch, {
              status: 'running',
              elapsed: event.elapsed,
              queries: [],
              papers: [],
              errors: [],
            }),
          }))
          continue
        }

        if (event.type === 'tool_query') {
          setStreamInfoText(
            event.queries.length > 0
              ? `论文检索关键词：${event.queries.join('，')}`
              : '已生成论文检索方向',
          )
          updateAssistantResponseDetail((current) => ({
            retrievedDocuments: current?.retrievedDocuments ?? [],
            ...current,
            paperSearch: mergePaperSearch(current?.paperSearch, {
              status: event.errors.length > 0 ? 'failed' : 'running',
              queries: event.queries,
              reason: event.reason,
              papers: [],
              errors: event.errors,
            }),
          }))
          continue
        }

        if (event.type === 'tool_result') {
          setStreamInfoText(`论文检索完成，找到 ${event.papers.length} 篇论文`)
          updateAssistantResponseDetail((current) => ({
            retrievedDocuments: current?.retrievedDocuments ?? [],
            ...current,
            paperSearch: mergePaperSearch(current?.paperSearch, {
              status: 'completed',
              queries: [],
              papers: event.papers,
              paperCount: event.papers.length,
              errors: [],
            }),
          }))
          continue
        }

        if (event.type === 'retrieval_result') {
          updateAssistantResponseDetail((current) => ({
            retrievedDocuments: current?.retrievedDocuments ?? [],
            ...current,
            localRetrieval: {
              query: event.query,
              retrievedDocuments: event.retrievedDocuments,
            },
          }))
          continue
        }

        if (event.type === 'error') {
          serverErrorMessage = event.content || '服务端返回错误。'
          break
        }

        if (event.type === 'done') {
          receivedDone = true
        }
      }

      return {
        receivedContent,
        receivedDone,
        serverErrorMessage,
      }
    }

    let routeDecision: RoutingDecision | null = null

    try {
      routeDecision = await decideRoute({
        routeMode,
        query: content,
        history,
        settings: {
          enableCacheCheck: settings.enableCacheCheck,
          enableNetworkCheck: settings.enableNetworkCheck,
          enableComplexityCheck: settings.enableComplexityCheck,
          enablePrivacyCheck: settings.enablePrivacyCheck,
          complexityThreshold: settings.complexityThreshold,
        },
      })
      const currentRouteDecision = routeDecision

      setRouteStatusText(toRouteStatusText(currentRouteDecision))
      const nextComplexityDetail = buildComplexityDetail(
        content,
        model,
        currentRouteDecision,
        settings.complexityThreshold,
        historyPreview,
      )
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                responseDetail: buildInitialResponseDetail(
                  currentRouteDecision,
                  nextComplexityDetail,
                ),
              }
            : message,
        ),
      )

      const primaryResult = await consumeStream(currentRouteDecision.target)
      if (primaryResult.serverErrorMessage) {
        throw new RagStreamError(
          primaryResult.serverErrorMessage,
          'network',
          currentRouteDecision.target,
        )
      }
      if (!primaryResult.receivedDone) {
        throw new RagStreamError(
          '未收到完成事件，流式响应可能已中断。',
          'unexpected_end',
          currentRouteDecision.target,
        )
      }

      if (!primaryResult.receivedContent) {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantMessageId
              ? { ...message, content: '（本次回答无文本内容）' }
              : message,
          ),
        )
      }

      rememberRouteDecision(content, currentRouteDecision.target)
    } catch (error) {
      const canFallback =
        routeDecision !== null &&
        routeDecision.fallbackTarget !== undefined &&
        routeDecision.fallbackTarget !== routeDecision.target &&
        shouldRetryInAutoMode(routeMode, error)

      if (canFallback && routeDecision && routeDecision.fallbackTarget) {
        const fallbackTarget = routeDecision.fallbackTarget
        const fallbackNotice = getAutoFallbackNotice(error, fallbackTarget)
        setRouteStatusText(
          `主路由失败，已回退到${toTargetLabel(fallbackTarget)}继续处理`,
        )
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantMessageId
              ? {
                  ...message,
                  content:
                    message.content.trim().length > 0
                      ? `${message.content}\n\n${fallbackNotice}`
                      : fallbackNotice,
                }
              : message,
          ),
        )

        try {
          const fallbackResult = await consumeStream(fallbackTarget)
          if (fallbackResult.serverErrorMessage) {
            throw new RagStreamError(
              fallbackResult.serverErrorMessage,
              'network',
              fallbackTarget,
            )
          }
          if (!fallbackResult.receivedDone) {
            throw new RagStreamError(
              '回退路由未收到完成事件，流式响应可能已中断。',
              'unexpected_end',
              fallbackTarget,
            )
          }
          if (!fallbackResult.receivedContent) {
            appendAssistantError('回退路由无可用响应，请稍后重试。')
          } else {
            rememberRouteDecision(content, fallbackTarget)
          }
        } catch (fallbackError) {
          appendAssistantError(getErrorMessage(fallbackError, routeMode))
          setStreamInfoText('')
        }
      } else {
        appendAssistantError(getErrorMessage(error, routeMode))
        setStreamInfoText('')
      }
    } finally {
      setIsSending(false)
    }
  }

  return (
    <Layout className="chat-layout">
      <Sider width={360} className="chat-layout__sider">
        <div className="chat-layout__sider-content">
          <Title level={4} className="chat-layout__title">
            端云协同 RAG 控制台
          </Title>

          <ModelSelectorSection value={model} onChange={setModel} />

          <NetworkStatusSection
            status={networkStatus}
            statusText={networkStatusText}
            refreshing={isNetworkRefreshing}
            onRefresh={() => void refreshNetworkStatus()}
          />

          <SettingsSection
            open={settingsOpen}
            settings={settings}
            onToggle={() => setSettingsOpen((current) => !current)}
            onChange={setSettings}
          />

          <PrivacySection
            open={privacyOpen}
            keywordInput={keywordInput}
            keywords={keywords}
            statusText={privacyStatusText}
            addingKeyword={isPrivacyAdding}
            deletingKeyword={deletingKeyword}
            refreshingKeywords={isPrivacyRefreshing}
            onToggle={() => setPrivacyOpen((current) => !current)}
            onKeywordInputChange={setKeywordInput}
            onAddKeyword={() => void addPrivacyKeyword()}
            onDeleteKeyword={(keyword) => void removePrivacyKeyword(keyword)}
            onRefreshKeywords={handleRefreshPrivacyKeywords}
          />
        </div>
      </Sider>

      <Content className="chat-layout__content">
        <div className="chat-area">
          <div className="chat-area__header">
            <div className="chat-area__header-row">
              <Title level={4} className="chat-area__title">
                聊天区
              </Title>
              <Popconfirm
                title="清空聊天记录"
                description="清空后会同时重置本轮隐私上下文和路由缓存。"
                okText="清空"
                cancelText="取消"
                onConfirm={clearMessages}
                disabled={isSending}
              >
                <Button size="small" danger disabled={isSending}>
                  清空记录
                </Button>
              </Popconfirm>
            </div>
            {routeStatusText ? <Text type="secondary">{routeStatusText}</Text> : null}
            {streamInfoText ? <Text type="secondary">{streamInfoText}</Text> : null}
          </div>

          <ChatMessageList
            messages={messages}
            onOpenResponseDetail={(detail) => {
              setSelectedResponseDetail(detail)
              setResponseModalOpen(true)
            }}
          />

          <ChatComposer
            value={composerText}
            onChange={setComposerText}
            onSend={() => void sendMessage()}
            disabled={isSending}
            loading={isSending}
          />
        </div>
      </Content>

      <ResponseDetailModal
        open={responseModalOpen}
        detail={selectedResponseDetail}
        onClose={() => setResponseModalOpen(false)}
      />
    </Layout>
  )
}
