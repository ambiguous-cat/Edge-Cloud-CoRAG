import { Button, Input, Space } from 'antd'

const { TextArea } = Input

interface ChatComposerProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled?: boolean
  loading?: boolean
}

export function ChatComposer({
  value,
  onChange,
  onSend,
  disabled = false,
  loading = false,
}: ChatComposerProps) {
  return (
    <Space direction="vertical" className="composer" size={10}>
      <TextArea
        value={value}
        rows={4}
        placeholder="请输入你的问题..."
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
      />
      <div className="composer__actions">
        <Button type="primary" onClick={onSend} disabled={disabled} loading={loading}>
          发送
        </Button>
      </div>
    </Space>
  )
}
