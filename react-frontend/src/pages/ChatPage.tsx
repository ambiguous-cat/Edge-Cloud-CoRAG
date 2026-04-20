import { Layout, Typography } from 'antd'
import { useMemo, useState } from 'react'
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
import '../styles/chat-page.css'

const { Sider, Content } = Layout
const { Title } = Typography

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
    content:
      '欢迎使用端云协同 RAG 聊天界面。当前是布局阶段，后续会接入流式对话和路由策略。',
    createdAt: '09:30:00',
  },
]

function nowTime() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

export function ChatPage() {
  const [model, setModel] = useState<ModelOption>('自动')
  const [networkStatus, setNetworkStatus] = useState<NetworkState>({
    localApiOnline: true,
    cloudApiOnline: true,
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

  const canSend = useMemo(() => composerText.trim().length > 0, [composerText])

  const refreshNetworkStatus = () => {
    setNetworkStatus((current) => ({
      ...current,
      lastChecked: nowTime(),
    }))
  }

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
    setPrivacyStatusText(`已刷新关键词列表（${nowTime()}）`)
  }

  const sendMessage = () => {
    if (!canSend) {
      return
    }

    const content = composerText.trim()
    const sentAt = nowTime()

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      createdAt: sentAt,
    }
    const assistantMessage: ChatMessage = {
      id: `assistant-${Date.now() + 1}`,
      role: 'assistant',
      content: `已收到你的消息（当前模式：${model}）。后续任务会接入真实流式响应。`,
      createdAt: nowTime(),
    }

    setMessages((current) => [...current, userMessage, assistantMessage])
    setComposerText('')
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
            onRefresh={refreshNetworkStatus}
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
          </div>

          <ChatMessageList messages={messages} />

          <ChatComposer
            value={composerText}
            onChange={setComposerText}
            onSend={sendMessage}
          />
        </div>
      </Content>
    </Layout>
  )
}
