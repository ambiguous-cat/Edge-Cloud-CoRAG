import { Button, Card, Checkbox, InputNumber, Slider, Space, Typography } from 'antd'
import type { SettingsState } from './types'

const { Text } = Typography

interface SettingsSectionProps {
  open: boolean
  settings: SettingsState
  onToggle: () => void
  onChange: (nextSettings: SettingsState) => void
}

export function SettingsSection({
  open,
  settings,
  onToggle,
  onChange,
}: SettingsSectionProps) {
  const update = <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => {
    onChange({ ...settings, [key]: value })
  }

  const toNumber = (value: number | [number, number]) =>
    Array.isArray(value) ? value[0] : value

  return (
    <Card
      title="设置区"
      size="small"
      extra={
        <Button size="small" onClick={onToggle}>
          {open ? '收起' : '展开'}
        </Button>
      }
    >
      {open ? (
        <Space direction="vertical" className="control-section__stack" size={12}>
          <div>
            <Text>相似度阈值</Text>
            <Slider
              min={0}
              max={1}
              step={0.01}
              value={settings.similarityThreshold}
              onChange={(value) =>
                update('similarityThreshold', toNumber(value))
              }
            />
          </div>

          <div>
            <Text>检索数量</Text>
            <InputNumber
              min={1}
              max={10}
              value={settings.retrievalCount}
              onChange={(value) => update('retrievalCount', value ?? 3)}
              className="control-section__full-width"
            />
          </div>

          <div>
            <Text>复杂度阈值</Text>
            <Slider
              min={0}
              max={1}
              step={0.01}
              value={settings.complexityThreshold}
              onChange={(value) =>
                update('complexityThreshold', toNumber(value))
              }
            />
          </div>

          <Checkbox
            checked={settings.enableCacheCheck}
            onChange={(event) => update('enableCacheCheck', event.target.checked)}
          >
            启用缓存检测
          </Checkbox>
          <Checkbox
            checked={settings.enableNetworkCheck}
            onChange={(event) => update('enableNetworkCheck', event.target.checked)}
          >
            启用网络检测
          </Checkbox>
          <Checkbox
            checked={settings.enableComplexityCheck}
            onChange={(event) =>
              update('enableComplexityCheck', event.target.checked)
            }
          >
            启用复杂度检测
          </Checkbox>
          <Checkbox
            checked={settings.enablePrivacyCheck}
            onChange={(event) => update('enablePrivacyCheck', event.target.checked)}
          >
            启用隐私检测
          </Checkbox>
        </Space>
      ) : (
        <Text type="secondary">点击“展开”查看和调整高级参数。</Text>
      )}
    </Card>
  )
}
