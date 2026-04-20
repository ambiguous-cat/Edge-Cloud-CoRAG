import type { ApiTarget } from './apiConfig'
import { getHttpClient } from './httpClient'

interface SystemStatusResponse {
  success?: unknown
}

export interface ApiHealthSnapshot {
  localApiOnline: boolean
  cloudApiOnline: boolean
}

async function probeSystemStatus(target: ApiTarget): Promise<boolean> {
  try {
    const { data } =
      await getHttpClient(target).get<SystemStatusResponse>('/system/status')

    return data?.success === true
  } catch {
    return false
  }
}

export async function fetchApiHealthSnapshot(): Promise<ApiHealthSnapshot> {
  const [localApiOnline, cloudApiOnline] = await Promise.all([
    probeSystemStatus('local'),
    probeSystemStatus('cloud'),
  ])

  return {
    localApiOnline,
    cloudApiOnline,
  }
}
