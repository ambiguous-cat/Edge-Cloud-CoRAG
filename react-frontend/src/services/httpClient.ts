import axios, { AxiosError, type AxiosInstance } from 'axios'
import { API_TIMEOUT_MS, getApiBaseUrl, type ApiTarget } from './apiConfig'

interface ErrorPayload {
  detail?: unknown
  message?: unknown
}

export class ApiClientError extends Error {
  readonly target: ApiTarget
  readonly statusCode?: number

  constructor(
    message: string,
    target: ApiTarget,
    statusCode?: number,
    cause?: unknown,
  ) {
    super(message, cause === undefined ? undefined : { cause })
    this.name = 'ApiClientError'
    this.target = target
    this.statusCode = statusCode
  }
}

function extractPayloadMessage(payload: unknown): string | null {
  if (typeof payload === 'string' && payload.trim()) {
    return payload
  }

  if (!payload || typeof payload !== 'object') {
    return null
  }

  const maybePayload = payload as ErrorPayload

  if (typeof maybePayload.detail === 'string' && maybePayload.detail.trim()) {
    return maybePayload.detail
  }

  if (typeof maybePayload.message === 'string' && maybePayload.message.trim()) {
    return maybePayload.message
  }

  return null
}

function buildAxiosErrorMessage(error: AxiosError): string {
  const payloadMessage = extractPayloadMessage(error.response?.data)
  if (payloadMessage) {
    return payloadMessage
  }

  if (error.code === 'ECONNABORTED') {
    return '请求超时，请稍后重试。'
  }

  if (error.message.trim()) {
    return error.message
  }

  return '请求失败：未知网络错误。'
}

function toApiClientError(error: unknown, target: ApiTarget): ApiClientError {
  if (error instanceof ApiClientError) {
    return error
  }

  if (axios.isAxiosError(error)) {
    return new ApiClientError(
      buildAxiosErrorMessage(error),
      target,
      error.response?.status,
      error,
    )
  }

  if (error instanceof Error) {
    return new ApiClientError(error.message, target, undefined, error)
  }

  return new ApiClientError(
    '请求失败：发生未知错误。',
    target,
    undefined,
    error,
  )
}

function createHttpClient(target: ApiTarget): AxiosInstance {
  const client = axios.create({
    baseURL: getApiBaseUrl(target),
    timeout: API_TIMEOUT_MS,
  })

  client.interceptors.response.use(
    (response) => response,
    (error: unknown) => Promise.reject(toApiClientError(error, target)),
  )

  return client
}

const httpClients: Record<ApiTarget, AxiosInstance> = {
  local: createHttpClient('local'),
  cloud: createHttpClient('cloud'),
}

export function getHttpClient(target: ApiTarget): AxiosInstance {
  return httpClients[target]
}
