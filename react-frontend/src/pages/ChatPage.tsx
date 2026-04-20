import { Layout, Typography } from 'antd'
import { useCallback, useMemo, useState } from 'react'
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
  RagStreamError,
  fetchApiHealthSnapshot,
  streamRagChat,
  type RouteMode,
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

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'assistant-0',
    role: 'assistant',
    content: '欢迎使用端云协同 RAG 聊天系统，当前前端已支持流式增量输出。',
    createdAt: '09:30:00',
  },
]

function nowTime() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
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

export function ChatPage() {
  const [model, setModel] = useState<ModelOption>('auto')
  const [networkStatus, setNetworkStatus] = useState<NetworkState>({
    localApiOnline: false,
    cloudApiOnline: false,
    lastChecked: nowTime(),
  })
  const [settingsOpen, setSettingsOpen] = useState<boolean>(true)
  const [privacyOpen, setPrivacyOpen] = useState<boolean>(true)
  const [settings, setSettings] = useState<SettingsState>(INITIAL_SETTINGS)
  const [keywordInput, setKeywordInput] = useState<string>('')
  const [keywords, setKeywords] = useState<string[]>(['身份证号', '手机号'])
  const [privacyStatusText, setPrivacyStatusText] = useState<string>('')
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES)
  const [composerText, setComposerText] = useState<string>('')
  const [streamInfoText, setStreamInfoText] = useState<string>('')
  const [isSending, setIsSending] = useState<boolean>(false)

  const canSend = useMemo(
    () => composerText.trim().length > 0 && !isSending,
    [composerText, isSending],
  )

  const refreshNetworkStatus = useCallback(async () => {
    const snapshot = await fetchApiHealthSnapshot()
    setNetworkStatus({
      ...snapshot,
      lastChecked: nowTime(),
    })
  }, [])

  const addPrivacyKeyword = () => {
    const trimmed = keywordInput.trim()
    if (!trimmed) {
      setPrivacyStatusText('请输入关键词后再提交。')
      return
    }

    if (keywords.includes(trimmed)) {
      setPrivacyStatusText('该关键词已存在。')
      return
    }

    setKeywords((current) => [...current, trimmed])
    setKeywordInput('')
    setPrivacyStatusText(`已新增关键词：${trimmed}`)
  }

  const refreshPrivacyKeywords = () => {
    setPrivacyStatusText(`关键词列表已刷新（${nowTime()}）。`)
  }

  const sendMessage = async () => {
    if (!canSend) {
      return
    }

    const content = composerText.trim()
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
    const routeMode = toRouteMode(model)

    setMessages((current) => [...current, userMessage, pendingAssistantMessage])
    setComposerText('')
    setStreamInfoText('')
    setIsSending(true)

    let receivedContent = false
    let receivedDone = false
    let serverErrorMessage = ''

    try {
      for await (const event of streamRagChat({
        query: content,
        routeMode,
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

      if (serverErrorMessage) {
        throw new Error(serverErrorMessage)
      }

      if (!receivedDone) {
        throw new Error('未收到完成事件，流式响应可能已中断。')
      }

      if (!receivedContent) {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantMessageId
              ? { ...message, content: '（本次回答无文本内容）' }
              : message,
          ),
        )
      }
    } catch (error) {
      const errorMessage = getErrorMessage(error)
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
      setStreamInfoText('')
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
            onToggle={() => setPrivacyOpen((current) => !current)}
            onKeywordInputChange={setKeywordInput}
            onAddKeyword={addPrivacyKeyword}
            onRefreshKeywords={refreshPrivacyKeywords}
          />
        </div>
      </Sider>

      <Content className="chat-layout__content">
        <div className="chat-area">
          <div className="chat-area__header">
            <Title level={4} className="chat-area__title">
              聊天区
            </Title>
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
