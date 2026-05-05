import { Button } from 'antd'
import ReactMarkdown from 'react-markdown'
import type { ChatMessage } from './types'
import type { ResponseDetailState } from './types'

interface ChatMessageListProps {
  messages: ChatMessage[]
  onOpenResponseDetail: (detail: ResponseDetailState) => void
}

export function ChatMessageList({
  messages,
  onOpenResponseDetail,
}: ChatMessageListProps) {
  return (
    <div className="message-list">
      {messages.map((message) => {
        const responseDetail = message.responseDetail
        const shouldShowActions = message.role === 'assistant' && responseDetail

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
            <div
              className={
                message.role === 'assistant'
                  ? 'message-item__content message-item__content--markdown'
                  : 'message-item__content message-item__content--plain'
              }
            >
              {message.role === 'assistant' ? (
                <ReactMarkdown>{message.content}</ReactMarkdown>
              ) : (
                message.content
              )}
            </div>
            {shouldShowActions ? (
              <div className="message-item__actions">
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
