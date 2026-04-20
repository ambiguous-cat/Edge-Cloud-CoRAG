import { Button, Card, Input, Space, Typography } from 'antd'

const { Paragraph, Text } = Typography

interface PrivacySectionProps {
  open: boolean
  keywordInput: string
  keywords: string[]
  statusText: string
  onToggle: () => void
  onKeywordInputChange: (value: string) => void
  onAddKeyword: () => void
  onRefreshKeywords: () => void
}

export function PrivacySection({
  open,
  keywordInput,
  keywords,
  statusText,
  onToggle,
  onKeywordInputChange,
  onAddKeyword,
  onRefreshKeywords,
}: PrivacySectionProps) {
  return (
    <Card
      title="隐私管理区"
      size="small"
      extra={
        <Button size="small" onClick={onToggle}>
          {open ? '收起' : '展开'}
        </Button>
      }
    >
      {open ? (
        <Space direction="vertical" className="control-section__stack">
          <Input
            value={keywordInput}
            placeholder="输入隐私关键词"
            onChange={(event) => onKeywordInputChange(event.target.value)}
          />
          <Space>
            <Button type="primary" onClick={onAddKeyword}>
              新增关键词
            </Button>
            <Button onClick={onRefreshKeywords}>刷新列表</Button>
          </Space>
          {statusText ? <Text type="secondary">{statusText}</Text> : null}
          <div>
            <Text strong>当前关键词</Text>
            <ul className="keyword-list">
              {keywords.map((keyword) => (
                <li key={keyword}>{keyword}</li>
              ))}
            </ul>
          </div>
        </Space>
      ) : (
        <Paragraph type="secondary">
          点击“展开”进行隐私关键词管理和状态查看。
        </Paragraph>
      )}
    </Card>
  )
}
