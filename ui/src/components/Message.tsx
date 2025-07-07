import { Message as MessageType } from '../types/chat';
import './Message.css';

interface MessageProps {
  message: MessageType;
  isQuestion?: boolean;
  isCompleted?: boolean;
}

export function Message({ message, isQuestion = false, isCompleted = false }: MessageProps) {
  // If it's completed, don't treat as question regardless of content
  // If explicitly marked as question, treat as question
  // Otherwise, fall back to content-based detection (but with better logic)
  const isQuestionMessage = !isCompleted && (isQuestion || (
    message.content.toLowerCase().includes('question ') && 
    !message.content.toLowerCase().includes('after answering') &&
    !message.content.toLowerCase().includes('search has begun')
  ));
  
  return (
    <div className={`message message-${message.role} ${isQuestionMessage ? 'message-question' : ''}`}>
      <div className="message-role">
        {message.role === 'user' ? 'You' : 'Executive Search AI'}
      </div>
      <div className="message-content">{message.content}</div>
      {isQuestionMessage && message.role === 'assistant' && (
        <div className="message-hint">Please provide your thoughts on this question to help us find the perfect candidate.</div>
      )}
    </div>
  );
}