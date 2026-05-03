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
  PaperSearchInfo,
  RagPaper,
  RagStreamEvent,
  RagStreamInfoEvent,
  RetrievedDocument,
  RetrievalFilterStats,
  SendRagChatRequest,
} from './chatService'

export { fetchApiHealthSnapshot } from './systemService'
export type { ApiHealthSnapshot } from './systemService'

export {
  createPrivacyKeyword,
  deletePrivacyKeyword,
  fetchPrivacyKeywords,
} from './privacyService'

export { clearRouteDecisionCache, decideRoute, rememberRouteDecision } from './routingService'
export type { DecideRouteRequest, RoutingDecision, RoutingSettings } from './routingService'
