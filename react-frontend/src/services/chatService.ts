import { resolveApiTarget, type RouteMode } from './apiConfig'
import { getHttpClient } from './httpClient'

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface SendRagChatRequest {
  query: string
  routeMode: RouteMode
  topK: number
  similarityThreshold: number
  history: ChatHistoryMessage[]
}

interface RagChatResponse {
  response?: unknown
}

function normalizeTopK(value: number): number {
  const rounded = Math.floor(value)
  return rounded > 0 ? rounded : 1
}

export async function sendRagChat({
  query,
  routeMode,
  topK,
  similarityThreshold,
  history,
}: SendRagChatRequest): Promise<string> {
  const target = resolveApiTarget(routeMode)
  const payload = {
    query,
    top_k: normalizeTopK(topK),
    stream: false,
    history,
    similarity_threshold: similarityThreshold,
  }

  const { data } = await getHttpClient(target).post<RagChatResponse>(
    '/rag_chat',
    payload,
  )

  if (!data || typeof data.response !== 'string') {
    throw new Error('后端返回了无法识别的聊天响应格式。')
  }

  return data.response
}
