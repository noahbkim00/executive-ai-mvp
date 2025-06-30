import { Message as MessageType } from '../types/chat';
import './Message.css';

interface MessageProps {
  message: MessageType;
}

export function Message({ message }: MessageProps) {
  return (
    <div className={`message message-${message.role}`}>
      <div className="message-role">
        {message.role === 'user' ? 'You' : 'AI Assistant'}
      </div>
      <div className="message-content">{message.content}</div>
    </div>
  );
}