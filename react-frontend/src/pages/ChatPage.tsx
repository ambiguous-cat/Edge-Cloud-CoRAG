import { Button, Layout, Space, Typography } from 'antd'
import { ApiHealthCard } from '../components/common/ApiHealthCard'
import '../styles/chat-page.css'

const { Sider, Content } = Layout
const { Title, Paragraph } = Typography

export function ChatPage() {
  return (
    <Layout className="chat-layout">
      <Sider width={320} className="chat-layout__sider">
        <Space direction="vertical" size={16} className="chat-layout__stack">
          <Title level={4} className="chat-layout__title">
            RAG Assistant
          </Title>
          <Paragraph type="secondary" className="chat-layout__text">
            React frontend scaffold is ready. Feature modules will be
            implemented in upcoming tasks.
          </Paragraph>
          <ApiHealthCard />
        </Space>
      </Sider>
      <Content className="chat-layout__content">
        <div className="chat-layout__panel">
          <Title level={4}>Main Chat Area</Title>
          <Paragraph>
            This panel is reserved for conversation flow, streaming output, and
            parameter controls.
          </Paragraph>
          <Button type="primary">Send (Placeholder)</Button>
        </div>
      </Content>
    </Layout>
  )
}
