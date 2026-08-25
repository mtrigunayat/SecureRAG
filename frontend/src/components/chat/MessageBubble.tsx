/**
 * Message Bubble Component
 */

import type { ChatMessage } from '../../types/chat';
import { SourceList } from './SourceList';
import './MessageBubble.css';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`message-bubble ${isUser ? 'message-user' : 'message-assistant'}`}>
      <div className="message-header">
        <span className="message-role">
          {isUser ? 'You' : 'Assistant'}
        </span>
        <span className="message-time">
          {new Date(message.createdAt).toLocaleTimeString()}
        </span>
      </div>
      
      <div className="message-content">
        {message.content}
      </div>

      {!isUser && message.sources && message.sources.length > 0 && (
        <SourceList sources={message.sources} />
      )}
    </div>
  );
}
