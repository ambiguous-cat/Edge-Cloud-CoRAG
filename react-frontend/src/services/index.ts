export {
  API_BASE_URLS,
  API_TIMEOUT_MS,
  getApiBaseUrl,
  resolveApiTarget,
} from './apiConfig'
export type { ApiTarget, RouteMode } from './apiConfig'

export { ApiClientError, getHttpClient } from './httpClient'

export { RagStreamError, sendRagChat, streamRagChat } from './chatService'
export type {
  ChatHistoryMessage,
  RagStreamEvent,
  SendRagChatRequest,
} from './chatService'

export { fetchApiHealthSnapshot } from './systemService'
export type { ApiHealthSnapshot } from './systemService'
