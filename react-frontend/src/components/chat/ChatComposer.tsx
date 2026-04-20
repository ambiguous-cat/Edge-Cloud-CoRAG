import { Button, Input, Space } from 'antd'

const { TextArea } = Input

interface ChatComposerProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
}

export function ChatComposer({ value, onChange, onSend }: ChatComposerProps) {
  return (
    <Space direction="vertical" className="composer" size={10}>
      <TextArea
        value={value}
        rows={4}
        placeholder="请输入问题..."
        onChange={(event) => onChange(event.target.value)}
      />
      <div className="composer__actions">
        <Button type="primary" onClick={onSend}>
          发送
        </Button>
      </div>
    </Space>
  )
}
