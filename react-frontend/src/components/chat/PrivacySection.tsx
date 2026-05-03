import { Button, Card, Input, Popconfirm, Space, Typography } from 'antd'

const { Paragraph, Text } = Typography

interface PrivacySectionProps {
  open: boolean
  keywordInput: string
  keywords: string[]
  statusText: string
  addingKeyword: boolean
  deletingKeyword: string | null
  refreshingKeywords: boolean
  onToggle: () => void
  onKeywordInputChange: (value: string) => void
  onAddKeyword: () => void
  onDeleteKeyword: (keyword: string) => void
  onRefreshKeywords: () => void
}

export function PrivacySection({
  open,
  keywordInput,
  keywords,
  statusText,
  addingKeyword,
  deletingKeyword,
  refreshingKeywords,
  onToggle,
  onKeywordInputChange,
  onAddKeyword,
  onDeleteKeyword,
  onRefreshKeywords,
}: PrivacySectionProps) {
  const controlsDisabled = addingKeyword || refreshingKeywords || deletingKeyword !== null

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
            disabled={controlsDisabled}
            onChange={(event) => onKeywordInputChange(event.target.value)}
          />
          <Space>
            <Button
              type="primary"
              loading={addingKeyword}
              disabled={refreshingKeywords || deletingKeyword !== null}
              onClick={onAddKeyword}
            >
              新增关键词
            </Button>
            <Button
              loading={refreshingKeywords}
              disabled={addingKeyword || deletingKeyword !== null}
              onClick={onRefreshKeywords}
            >
              刷新列表
            </Button>
          </Space>
          {statusText ? <Text type="secondary">{statusText}</Text> : null}
          <div>
            <Text strong>当前关键词</Text>
            <ul className="keyword-list">
              {keywords.map((keyword) => (
                <li key={keyword}>
                  <span>{keyword}</span>
                  <Popconfirm
                    title="删除隐私关键词"
                    description={`确认删除“${keyword}”？`}
                    okText="删除"
                    cancelText="取消"
                    onConfirm={() => onDeleteKeyword(keyword)}
                    disabled={controlsDisabled}
                  >
                    <Button
                      size="small"
                      danger
                      loading={deletingKeyword === keyword}
                      disabled={controlsDisabled && deletingKeyword !== keyword}
                    >
                      删除
                    </Button>
                  </Popconfirm>
                </li>
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
