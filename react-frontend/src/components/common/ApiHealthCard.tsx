import { Card, Tag, Typography } from 'antd'

const { Paragraph } = Typography

export function ApiHealthCard() {
  return (
    <Card size="small" title="API Client Scaffold">
      <Paragraph>
        Base URL is configured through <code>VITE_API_BASE_URL</code>.
      </Paragraph>
      <Tag color="blue">axios configured</Tag>
    </Card>
  )
}
