import { Descriptions, List, Modal, Progress, Space, Typography } from 'antd'
import type { ComplexityDetailState, ModelOption } from './types'

const { Text } = Typography

interface ComplexityDetailModalProps {
  open: boolean
  detail: ComplexityDetailState | null
  onClose: () => void
}

const MODEL_LABELS: Record<ModelOption, string> = {
  auto: '自动',
  cloud: '云端',
  local: '本地',
}

const ANALYSIS_LABELS: Record<string, string> = {
  total_complexity: '总复杂度',
  query_length: '查询长度',
  keyword_richness: '关键词丰富度',
  semantic_depth: '语义深度',
  domain_specificity: '领域特定性',
  reasoning_requirements: '语法复杂度',
}

function formatScore(value?: number): string {
  return value === undefined ? '未返回' : value.toFixed(2)
}

function toPercent(value: number): number {
  return Math.round(Math.max(0, Math.min(1, value)) * 100)
}

export function ComplexityDetailModal({
  open,
  detail,
  onClose,
}: ComplexityDetailModalProps) {
  return (
    <Modal
      title="复杂度详情"
      open={open}
      onCancel={onClose}
      footer={null}
      width={720}
      destroyOnHidden
    >
      {detail ? (
        <Space direction="vertical" size={16} className="complexity-modal__stack">
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="当前模式">
              {MODEL_LABELS[detail.model]}
            </Descriptions.Item>
            <Descriptions.Item label="实际路由">
              {detail.routeLabel}
            </Descriptions.Item>
            <Descriptions.Item label="复杂度">
              {formatScore(detail.score)}
            </Descriptions.Item>
            <Descriptions.Item label="阈值">
              {detail.threshold.toFixed(2)}
            </Descriptions.Item>
            <Descriptions.Item label="后端路由">
              {detail.route ?? '未返回'}
            </Descriptions.Item>
            <Descriptions.Item label="基础路由">
              {detail.baseRoute ?? '未返回'}
            </Descriptions.Item>
            <Descriptions.Item label="置信度">
              {formatScore(detail.confidence)}
            </Descriptions.Item>
            <Descriptions.Item label="原因" span={2}>
              {detail.reasonLabel}
            </Descriptions.Item>
          </Descriptions>

          <div>
            <Text strong>当前问题</Text>
            <div className="complexity-modal__text">{detail.query}</div>
          </div>

          {Object.entries(detail.analysis).length > 0 ? (
            <List
              size="small"
              header={<Text strong>维度评分</Text>}
              dataSource={Object.entries(detail.analysis)}
              renderItem={([key, value]) => (
                <List.Item>
                  <div className="complexity-modal__metric">
                    <span>{ANALYSIS_LABELS[key] ?? key}</span>
                    <Progress
                      percent={toPercent(value)}
                      size="small"
                      format={() => value.toFixed(2)}
                    />
                  </div>
                </List.Item>
              )}
            />
          ) : null}

          {detail.explanation ? (
            <div>
              <Text strong>路由解释</Text>
              <div className="complexity-modal__text">{detail.explanation}</div>
            </div>
          ) : null}

          {detail.recommendations.length > 0 ? (
            <List
              size="small"
              header={<Text strong>建议</Text>}
              dataSource={detail.recommendations}
              renderItem={(item) => <List.Item>{item}</List.Item>}
            />
          ) : null}

          <List
            size="small"
            header={<Text strong>解析后的聊天历史</Text>}
            dataSource={detail.historyPreview}
            locale={{ emptyText: '暂无历史消息' }}
            renderItem={(item) => (
              <List.Item>
                <Text type="secondary">
                  {item.role === 'user' ? '用户' : '助手'}：
                </Text>
                <span className="complexity-modal__history-content">
                  {item.content}
                </span>
              </List.Item>
            )}
          />
        </Space>
      ) : (
        <Text type="secondary">发送消息后可查看复杂度详情。</Text>
      )}
    </Modal>
  )
}
