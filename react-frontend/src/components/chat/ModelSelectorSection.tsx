import { Card, Select, Space, Typography } from 'antd'
import type { ModelOption } from './types'

const { Text } = Typography

interface ModelSelectorSectionProps {
  value: ModelOption
  onChange: (value: ModelOption) => void
}

const OPTIONS: Array<{ label: string; value: ModelOption }> = [
  { label: '自动', value: 'auto' },
  { label: '云端', value: 'cloud' },
  { label: '本地', value: 'local' },
]

const MODE_LABELS: Record<ModelOption, string> = {
  auto: '自动',
  cloud: '云端',
  local: '本地',
}

export function ModelSelectorSection({
  value,
  onChange,
}: ModelSelectorSectionProps) {
  return (
    <Card title="模型模式" size="small">
      <Space direction="vertical" className="control-section__stack">
        <Select<ModelOption>
          value={value}
          options={OPTIONS}
          onChange={onChange}
          className="control-section__full-width"
        />
        <Text type="secondary">当前模式：{MODE_LABELS[value]}</Text>
      </Space>
    </Card>
  )
}
