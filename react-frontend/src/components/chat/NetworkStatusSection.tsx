import { Button, Card, Space, Tag, Typography } from 'antd'
import type { NetworkState } from './types'

const { Text } = Typography

interface NetworkStatusSectionProps {
  status: NetworkState
  onRefresh: () => void
}

function statusTag(online: boolean) {
  return online ? <Tag color="success">在线</Tag> : <Tag color="error">离线</Tag>
}

export function NetworkStatusSection({
  status,
  onRefresh,
}: NetworkStatusSectionProps) {
  return (
    <Card
      title="网络状态"
      size="small"
      extra={
        <Button size="small" onClick={onRefresh}>
          刷新
        </Button>
      }
    >
      <Space direction="vertical" className="control-section__stack">
        <div className="network-row">
          <Text>本地 API</Text>
          {statusTag(status.localApiOnline)}
        </div>
        <div className="network-row">
          <Text>云端 API</Text>
          {statusTag(status.cloudApiOnline)}
        </div>
        <Text type="secondary">最近检查：{status.lastChecked}</Text>
      </Space>
    </Card>
  )
}
