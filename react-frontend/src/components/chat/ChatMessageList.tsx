import type { ChatMessage } from './types'

interface ChatMessageListProps {
  messages: ChatMessage[]
}

export function ChatMessageList({ messages }: ChatMessageListProps) {
  return (
    <div className="message-list">
      {messages.map((message) => (
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
        </div>
      ))}
    </div>
  )
}
