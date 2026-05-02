import { Descriptions, List, Modal, Space, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { RetrievedDocument } from '../../services'
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

const columns: ColumnsType<RetrievedDocument> = [
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
              columns={columns}
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
