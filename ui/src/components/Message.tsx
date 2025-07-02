import { Message as MessageType } from '../types/chat';
import './Message.css';

interface MessageProps {
  message: MessageType;
  isQuestion?: boolean;
}

export function Message({ message, isQuestion = false }: MessageProps) {
  const isQuestionMessage = isQuestion || message.content.toLowerCase().includes('question');
  
  return (
    <div className={`message message-${message.role} ${isQuestionMessage ? 'message-question' : ''}`}>
      <div className="message-role">
        {message.role === 'user' ? 'You' : isQuestionMessage ? 'Executive Search AI' : 'AI Assistant'}
      </div>
      <div className="message-content">{message.content}</div>
      {isQuestionMessage && message.role === 'assistant' && (
        <div className="message-hint">Please provide your thoughts on this question to help us find the perfect candidate.</div>
      )}
    </div>
  );
}