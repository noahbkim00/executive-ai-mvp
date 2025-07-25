import { useEffect, useRef } from 'react';
import { Message as MessageType } from '../types/chat';
import { Message } from './Message';
import './MessageList.css';

interface MessageListProps {
  messages: MessageType[];
  isLoading: boolean;
  error?: string | null;
  onClearError?: () => void;
  isCompleted?: boolean;
}

export function MessageList({ messages, isLoading, error, onClearError, isCompleted = false }: MessageListProps) {
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="message-list">
      {messages.length === 0 && (
        <div className="message-list-empty">
          <p>Start a conversation by typing a message below.</p>
        </div>
      )}
      
      {messages.map((message, index) => {
        // Check if this is the last assistant message and conversation is completed
        const isLastAssistantMessage = message.role === 'assistant' && 
          index === messages.length - 1;
        const isCompletionMessage = isCompleted && isLastAssistantMessage;
        
        return (
          <Message 
            key={message.id} 
            message={message} 
            isCompleted={isCompletionMessage}
          />
        );
      })}
      
      {isLoading && (
        <div className="message-list-loading">
          <div className="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      )}
      
      {error && (
        <div className="message-list-error">
          <div className="error-content">
            <span className="error-message">{error}</span>
            {onClearError && (
              <button 
                className="error-dismiss-button" 
                onClick={onClearError}
                aria-label="Dismiss error"
              >
                ×
              </button>
            )}
          </div>
        </div>
      )}
      
      <div ref={endOfMessagesRef} />
    </div>
  );
}