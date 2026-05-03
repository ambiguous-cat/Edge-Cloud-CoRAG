import { getHttpClient } from './httpClient'

interface PrivacyKeywordsResponse {
  success?: unknown
  total?: unknown
  keywords?: unknown
}

interface AddPrivacyKeywordResponse {
  success?: unknown
  message?: unknown
  keyword?: unknown
}

interface DeletePrivacyKeywordResponse {
  success?: unknown
  message?: unknown
  keyword?: unknown
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }

  return value
    .map((item) => {
      if (typeof item === 'string') {
        return item
      }

      if (item && typeof item === 'object' && !Array.isArray(item)) {
        const keyword = (item as { keyword?: unknown }).keyword
        return typeof keyword === 'string' ? keyword : ''
      }

      return ''
    })
    .filter((item) => item.trim().length > 0)
}

function toMessage(value: unknown, fallback: string): string {
  if (typeof value === 'string' && value.trim()) {
    return value
  }
  return fallback
}

export async function fetchPrivacyKeywords(): Promise<string[]> {
  const { data } = await getHttpClient('local').get<PrivacyKeywordsResponse>(
    '/privacy/keywords',
  )
  if (data?.success !== true) {
    throw new Error('获取隐私关键词列表失败。')
  }
  return toStringArray(data?.keywords)
}

export async function createPrivacyKeyword(keyword: string): Promise<string> {
  const { data } = await getHttpClient('local').post<AddPrivacyKeywordResponse>(
    '/privacy/keywords/add',
    { keyword },
  )

  if (data?.success !== true) {
    throw new Error(toMessage(data?.message, `关键词“${keyword}”新增失败。`))
  }

  return toMessage(data?.message, `关键词“${keyword}”添加成功。`)
}

export async function deletePrivacyKeyword(keyword: string): Promise<string> {
  const { data } = await getHttpClient('local').delete<DeletePrivacyKeywordResponse>(
    `/privacy/keywords/${encodeURIComponent(keyword)}`,
  )

  if (data?.success !== true) {
    throw new Error(toMessage(data?.message, `关键词“${keyword}”删除失败。`))
  }

  return toMessage(data?.message, `关键词“${keyword}”删除成功。`)
}
