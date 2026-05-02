import { Button } from 'antd'
import type { ChatMessage } from './types'
import type { ComplexityDetailState, ResponseDetailState } from './types'

interface ChatMessageListProps {
  messages: ChatMessage[]
  onOpenComplexityDetail: (detail: ComplexityDetailState) => void
  onOpenResponseDetail: (detail: ResponseDetailState) => void
}

export function ChatMessageList({
  messages,
  onOpenComplexityDetail,
  onOpenResponseDetail,
}: ChatMessageListProps) {
  return (
    <div className="message-list">
      {messages.map((message) => {
        const complexityDetail = message.complexityDetail
        const responseDetail = message.responseDetail
        const shouldShowActions =
          message.role === 'assistant' && (complexityDetail || responseDetail)

        return (
          <div
            key={message.id}
            className={
              message.role === 'user'
                ? 'message-item message-item--user'
                : 'message-item message-item--assistant'
            }
          >
            <div className="message-item__header">
              <span>{message.role === 'user' ? '你' : '助手'}</span>
              <span>{message.createdAt}</span>
            </div>
            <div>{message.content}</div>
            {shouldShowActions ? (
              <div className="message-item__actions">
                {complexityDetail ? (
                  <Button
                    size="small"
                    onClick={() => onOpenComplexityDetail(complexityDetail)}
                  >
                    复杂度详情
                  </Button>
                ) : null}
                {responseDetail ? (
                  <Button
                    size="small"
                    onClick={() => onOpenResponseDetail(responseDetail)}
                  >
                    响应详情
                  </Button>
                ) : null}
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
