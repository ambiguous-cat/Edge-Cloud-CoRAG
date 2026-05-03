import { Descriptions, List, Modal, Progress, Space, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { RagPaper, RetrievedDocument } from '../../services'
import type { ResponseDetailState } from './types'

const { Text } = Typography

interface ResponseDetailModalProps {
  open: boolean
  detail: ResponseDetailState | null
  onClose: () => void
}

function formatNumber(value?: number): string {
  return value === undefined ? '未返回' : value.toLocaleString('zh-CN')
}

function formatDecimal(value?: number): string {
  return value === undefined ? '未返回' : value.toFixed(3)
}

function formatScore(value?: number): string {
  return value === undefined ? '未返回' : value.toFixed(2)
}

function formatPrivacyStatus(detail: ResponseDetailState): string {
  if (!detail.privacyChecked) {
    return '未检测'
  }

  return detail.privacyRisk ? '命中隐私保护' : '未命中隐私保护'
}

function toPercent(value: number): number {
  return Math.round(Math.max(0, Math.min(1, value)) * 100)
}

const ANALYSIS_LABELS: Record<string, string> = {
  total_complexity: '总复杂度',
  query_length: '查询长度',
  keyword_richness: '关键词丰富度',
  semantic_depth: '语义深度',
  domain_specificity: '领域特定性',
  reasoning_requirements: '推理需求',
}

const documentColumns: ColumnsType<RetrievedDocument> = [
  {
    title: '标题',
    dataIndex: 'title',
    key: 'title',
    width: 180,
  },
  {
    title: '相似度',
    dataIndex: 'similarityScore',
    key: 'similarityScore',
    width: 96,
    render: (value?: number) => formatDecimal(value),
  },
  {
    title: '分块',
    dataIndex: 'chunkIndex',
    key: 'chunkIndex',
    width: 76,
    render: (value?: number) => formatNumber(value),
  },
  {
    title: '内容预览',
    dataIndex: 'content',
    key: 'content',
    render: (value: string) => (
      <span className="response-modal__document-preview">{value}</span>
    ),
  },
]

const paperColumns: ColumnsType<RagPaper> = [
  {
    title: '标题',
    dataIndex: 'title',
    key: 'title',
    width: 220,
    render: (value: string, record) =>
      record.url ? (
        <a href={record.url} target="_blank" rel="noreferrer">
          {value}
        </a>
      ) : (
        value
      ),
  },
  {
    title: '作者',
    dataIndex: 'authors',
    key: 'authors',
    width: 180,
    render: (value: string[]) => (value.length > 0 ? value.join(', ') : '未返回'),
  },
  {
    title: '发表时间',
    dataIndex: 'published',
    key: 'published',
    width: 120,
    render: (value?: string) => value?.slice(0, 10) ?? '未返回',
  },
  {
    title: '匹配检索词',
    dataIndex: 'matchedQuery',
    key: 'matchedQuery',
    width: 180,
    render: (value?: string) => value ?? '未返回',
  },
  {
    title: '摘要',
    dataIndex: 'summary',
    key: 'summary',
    render: (value: string) => (
      <span className="response-modal__document-preview">{value}</span>
    ),
  },
]

export function ResponseDetailModal({
  open,
  detail,
  onClose,
}: ResponseDetailModalProps) {
  return (
    <Modal
      title="响应详情"
      open={open}
      onCancel={onClose}
      footer={null}
      width={840}
      destroyOnHidden
    >
      {detail ? (
        <Space direction="vertical" size={16} className="response-modal__stack">
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="首字响应">
              {detail.responseTime === undefined
                ? '未返回'
                : `${detail.responseTime.toFixed(2)} 秒`}
            </Descriptions.Item>
            <Descriptions.Item label="分片数量">
              {formatNumber(detail.chunkCount)}
            </Descriptions.Item>
            <Descriptions.Item label="回答字符数">
              {formatNumber(detail.charCount)}
            </Descriptions.Item>
            <Descriptions.Item label="估算 Token">
              {formatNumber(detail.estimatedTokens)}
            </Descriptions.Item>
            <Descriptions.Item label="上下文长度">
              {formatNumber(detail.contextLength)}
            </Descriptions.Item>
            <Descriptions.Item label="引用文档">
              {formatNumber(detail.retrievedDocuments.length)}
            </Descriptions.Item>
          </Descriptions>

          {detail.routeLabel || detail.reasonLabel || detail.privacyScore !== undefined ? (
            <Descriptions title="路由与隐私" size="small" column={2} bordered>
              <Descriptions.Item label="实际路由">
                {detail.routeLabel ?? '未返回'}
              </Descriptions.Item>
              <Descriptions.Item label="隐私状态">
                {formatPrivacyStatus(detail)}
              </Descriptions.Item>
              <Descriptions.Item label="隐私分">
                {formatScore(detail.privacyScore)}
              </Descriptions.Item>
              <Descriptions.Item label="路由原因">
                {detail.reasonLabel ?? '未返回'}
              </Descriptions.Item>
            </Descriptions>
          ) : null}

          {detail.complexityDetail ? (
            <Space direction="vertical" size={12} className="response-modal__stack">
              <Descriptions title="复杂度" size="small" column={2} bordered>
                <Descriptions.Item label="当前模式">
                  {detail.complexityDetail.model === 'auto'
                    ? '自动'
                    : detail.complexityDetail.model === 'cloud'
                      ? '云端'
                      : '本地'}
                </Descriptions.Item>
                <Descriptions.Item label="复杂度">
                  {formatScore(detail.complexityDetail.score)}
                </Descriptions.Item>
                <Descriptions.Item label="阈值">
                  {detail.complexityDetail.threshold.toFixed(2)}
                </Descriptions.Item>
                <Descriptions.Item label="置信度">
                  {formatScore(detail.complexityDetail.confidence)}
                </Descriptions.Item>
                <Descriptions.Item label="后端路由">
                  {detail.complexityDetail.route ?? '未返回'}
                </Descriptions.Item>
                <Descriptions.Item label="基础路由">
                  {detail.complexityDetail.baseRoute ?? '未返回'}
                </Descriptions.Item>
              </Descriptions>

              {Object.entries(detail.complexityDetail.analysis).length > 0 ? (
                <List
                  size="small"
                  header={<Text strong>维度评分</Text>}
                  dataSource={Object.entries(detail.complexityDetail.analysis)}
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

              <List
                size="small"
                header={<Text strong>解析后的聊天历史</Text>}
                dataSource={detail.complexityDetail.historyPreview}
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
          ) : null}

          {detail.paperSearch ? (
            <Space direction="vertical" size={12} className="response-modal__stack">
              <Descriptions title="论文检索" size="small" column={2} bordered>
                <Descriptions.Item label="状态">
                  {detail.paperSearch.status === 'running'
                    ? '检索中'
                    : detail.paperSearch.status === 'completed'
                      ? '已完成'
                      : detail.paperSearch.status === 'failed'
                        ? '失败'
                        : '未开始'}
                </Descriptions.Item>
                <Descriptions.Item label="耗时">
                  {detail.paperSearch.elapsed === undefined
                    ? '未返回'
                    : `${detail.paperSearch.elapsed.toFixed(1)} 秒`}
                </Descriptions.Item>
                <Descriptions.Item label="论文数量">
                  {formatNumber(
                    detail.paperSearch.paperCount ?? detail.paperSearch.papers.length,
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="检索方向">
                  {detail.paperSearch.reason ?? '未返回'}
                </Descriptions.Item>
                <Descriptions.Item label="检索关键词" span={2}>
                  {detail.paperSearch.queries.length > 0
                    ? detail.paperSearch.queries.join('，')
                    : '未返回'}
                </Descriptions.Item>
                {detail.paperSearch.errors.length > 0 ? (
                  <Descriptions.Item label="错误" span={2}>
                    {detail.paperSearch.errors.join('；')}
                  </Descriptions.Item>
                ) : null}
              </Descriptions>

              <Table
                className="response-modal__document-table"
                columns={paperColumns}
                dataSource={detail.paperSearch.papers}
                rowKey={(record, index) => record.id ?? record.url ?? `${index}`}
                size="small"
                pagination={false}
                scroll={{ x: 900 }}
                locale={{ emptyText: '本次响应未返回论文结果' }}
              />
            </Space>
          ) : null}

          {detail.filterStats ? (
            <Descriptions
              title="检索过滤"
              size="small"
              column={2}
              bordered
            >
              <Descriptions.Item label="相似度阈值">
                {formatDecimal(detail.filterStats.similarityThreshold)}
              </Descriptions.Item>
              <Descriptions.Item label="原始数量">
                {formatNumber(detail.filterStats.originalCount)}
              </Descriptions.Item>
              <Descriptions.Item label="过滤数量">
                {formatNumber(detail.filterStats.filteredCount)}
              </Descriptions.Item>
              <Descriptions.Item label="通过数量">
                {formatNumber(detail.filterStats.acceptedCount)}
              </Descriptions.Item>
            </Descriptions>
          ) : null}

          <div>
            <Text strong>检索文档</Text>
            <Table
              className="response-modal__document-table"
              columns={documentColumns}
              dataSource={detail.retrievedDocuments}
              rowKey={(record, index) =>
                `${record.documentId ?? 'doc'}-${record.chunkId ?? index}`
              }
              size="small"
              pagination={false}
              scroll={{ x: 720 }}
              locale={{ emptyText: '本次响应未返回检索文档' }}
            />
          </div>

          {detail.localRetrieval ? (
            <div>
              <Text strong>本地 RAG 检索结果</Text>
              <Table
                className="response-modal__document-table"
                columns={documentColumns}
                dataSource={detail.localRetrieval.retrievedDocuments}
                rowKey={(record, index) =>
                  `${record.documentId ?? 'doc'}-${record.chunkId ?? index}`
                }
                size="small"
                pagination={false}
                scroll={{ x: 720 }}
                locale={{ emptyText: '本次响应未返回本地 RAG 检索结果' }}
              />
            </div>
          ) : null}
        </Space>
      ) : (
        <List
          size="small"
          dataSource={['发送消息并收到流式统计后可查看响应详情。']}
          renderItem={(item) => (
            <List.Item>
              <Text type="secondary">{item}</Text>
            </List.Item>
          )}
        />
      )}
    </Modal>
  )
}
