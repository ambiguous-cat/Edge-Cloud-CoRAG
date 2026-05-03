import type {
  ChatHistoryMessage,
  RagPaper,
  RetrievedDocument,
  RetrievalFilterStats,
} from '../../services'

export type ModelOption = 'auto' | 'cloud' | 'local'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
  complexityDetail?: ComplexityDetailState
  responseDetail?: ResponseDetailState
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

export interface ComplexityDetailState {
  query: string
  model: ModelOption
  routeLabel: string
  reasonLabel: string
  threshold: number
  score?: number
  confidence?: number
  route?: string
  baseRoute?: string
  explanation?: string
  recommendations: string[]
  analysis: Record<string, number>
  historyPreview: ChatHistoryMessage[]
}

export interface ResponseDetailState {
  responseTime?: number
  charCount?: number
  estimatedTokens?: number
  chunkCount?: number
  contextLength?: number
  retrievedDocuments: RetrievedDocument[]
  filterStats?: RetrievalFilterStats
  routeLabel?: string
  reasonLabel?: string
  privacyScore?: number
  privacyChecked?: boolean
  privacyRisk?: boolean
  complexityDetail?: ComplexityDetailState
  paperSearch?: PaperSearchDetailState
  localRetrieval?: LocalRetrievalDetailState
}

export interface PaperSearchDetailState {
  status: 'idle' | 'running' | 'completed' | 'failed'
  elapsed?: number
  queries: string[]
  reason?: string
  papers: RagPaper[]
  paperCount?: number
  errors: string[]
}

export interface LocalRetrievalDetailState {
  query?: string
  retrievedDocuments: RetrievedDocument[]
}
