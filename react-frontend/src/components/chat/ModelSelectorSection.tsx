import { Card, Select, Space, Typography } from 'antd'
import type { ModelOption } from './types'

const { Text } = Typography

interface ModelSelectorSectionProps {
  value: ModelOption
  onChange: (value: ModelOption) => void
}

const OPTIONS: Array<{ label: string; value: ModelOption }> = [
  { label: '自动', value: '自动' },
  { label: '云端', value: '云端' },
  { label: '本地', value: '本地' },
]

export function ModelSelectorSection({
  value,
  onChange,
}: ModelSelectorSectionProps) {
  return (
    <Card title="模型选择" size="small">
      <Space direction="vertical" className="control-section__stack">
        <Select<ModelOption>
          value={value}
          options={OPTIONS}
          onChange={onChange}
          className="control-section__full-width"
        />
        <Text type="secondary">当前模式：{value}</Text>
      </Space>
    </Card>
  )
}
