export type ModelOption = 'auto' | 'cloud' | 'local'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
}

export interface SettingsState {
  similarityThreshold: number
  retrievalCount: number
  complexityThreshold: number
  enableCacheCheck: boolean
  enableNetworkCheck: boolean
  enableComplexityCheck: boolean
  enablePrivacyCheck: boolean
}

export interface NetworkState {
  localApiOnline: boolean
  cloudApiOnline: boolean
  lastChecked: string
}
