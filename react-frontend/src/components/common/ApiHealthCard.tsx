import { Card, Tag, Typography } from 'antd'

const { Paragraph } = Typography

export function ApiHealthCard() {
  return (
    <Card size="small" title="API 客户端配置">
      <Paragraph>
        基础地址通过 <code>VITE_LOCAL_API_BASE_URL</code> 与{' '}
        <code>VITE_CLOUD_API_BASE_URL</code> 配置，也兼容旧变量{' '}
        <code>VITE_API_BASE_URL</code>。
      </Paragraph>
      <Tag color="blue">Axios 已配置</Tag>
    </Card>
  )
}
