import { Layout, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { ChatComposer } from '../components/chat/ChatComposer'
import { ChatMessageList } from '../components/chat/ChatMessageList'
import { ModelSelectorSection } from '../components/chat/ModelSelectorSection'
import { NetworkStatusSection } from '../components/chat/NetworkStatusSection'
import { PrivacySection } from '../components/chat/PrivacySection'
import { SettingsSection } from '../components/chat/SettingsSection'
import type {
  ChatMessage,
  ModelOption,
  NetworkState,
  SettingsState,
} from '../components/chat/types'
import {
  ApiClientError,
  RagStreamError,
  createPrivacyKeyword,
  decideRoute,
  fetchApiHealthSnapshot,
  fetchPrivacyKeywords,
  rememberRouteDecision,
  streamRagChat,
  type ApiTarget,
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

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'assistant-0',
    role: 'assistant',
    content: '欢迎使用端云协同 RAG 聊天系统，当前前端已支持流式增量输出。',
    createdAt: '09:30:00',
  },
]

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

function toRouteMode(model: ModelOption): RouteMode {
  if (model === 'cloud') {
    return 'cloud'
  }

  if (model === 'local') {
    return 'local'
  }

  return 'auto'
}

function buildHistory(messages: ChatMessage[]) {
  return messages.map(({ role, content }) => ({ role, content }))
}

function getErrorMessage(error: unknown): string {
  if (error instanceof RagStreamError) {
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
  const [isPrivacyRefreshing, setIsPrivacyRefreshing] = useState<boolean>(false)
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES)
  const [composerText, setComposerText] = useState<string>('')
  const [routeStatusText, setRouteStatusText] = useState<string>('')
  const [streamInfoText, setStreamInfoText] = useState<string>('')
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

    const history = buildHistory([...messages, userMessage])

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
          setStreamInfoText(
            toStreamInfoText(event.responseTime, event.charCount, event.chunkCount),
          )
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

      setRouteStatusText(toRouteStatusText(routeDecision))

      const primaryResult = await consumeStream(routeDecision.target)
      if (primaryResult.serverErrorMessage) {
        throw new RagStreamError(
          primaryResult.serverErrorMessage,
          'network',
          routeDecision.target,
        )
      }
      if (!primaryResult.receivedDone) {
        throw new RagStreamError(
          '未收到完成事件，流式响应可能已中断。',
          'unexpected_end',
          routeDecision.target,
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

      rememberRouteDecision(content, routeDecision.target)
    } catch (error) {
      const canFallback =
        routeDecision !== null &&
        routeDecision.fallbackTarget !== undefined &&
        routeDecision.fallbackTarget !== routeDecision.target &&
        shouldRetryInAutoMode(routeMode, error)

      if (canFallback && routeDecision && routeDecision.fallbackTarget) {
        const fallbackTarget = routeDecision.fallbackTarget
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
                      ? `${message.content}\n\n[自动回退] 主路由中断，切换到${toTargetLabel(
                          fallbackTarget,
                        )}重试。`
                      : `[自动回退] 主路由中断，切换到${toTargetLabel(
                          fallbackTarget,
                        )}重试。`,
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
          appendAssistantError(getErrorMessage(fallbackError))
          setStreamInfoText('')
        }
      } else {
        appendAssistantError(getErrorMessage(error))
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
            refreshingKeywords={isPrivacyRefreshing}
            onToggle={() => setPrivacyOpen((current) => !current)}
            onKeywordInputChange={setKeywordInput}
            onAddKeyword={() => void addPrivacyKeyword()}
            onRefreshKeywords={handleRefreshPrivacyKeywords}
          />
        </div>
      </Sider>

      <Content className="chat-layout__content">
        <div className="chat-area">
          <div className="chat-area__header">
            <Title level={4} className="chat-area__title">
              聊天区
            </Title>
            {routeStatusText ? <Text type="secondary">{routeStatusText}</Text> : null}
            {streamInfoText ? <Text type="secondary">{streamInfoText}</Text> : null}
          </div>

          <ChatMessageList messages={messages} />

          <ChatComposer
            value={composerText}
            onChange={setComposerText}
            onSend={() => void sendMessage()}
            disabled={isSending}
            loading={isSending}
          />
        </div>
      </Content>
    </Layout>
  )
}
