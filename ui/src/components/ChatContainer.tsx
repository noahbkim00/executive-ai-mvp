import { useState } from 'react';
import { Message } from '../types/chat';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { chatApi, ApiError } from '../services/api';
import './ChatContainer.css';

export function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await chatApi.sendMessage(content);
      
      const assistantMessage: Message = {
        id: response.id,
        role: response.role,
        content: response.content,
        timestamp: new Date(response.timestamp), // Convert ISO string to Date
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      
      let errorMessage = 'Something went wrong. Please try again.';
      
      if (error instanceof ApiError) {
        if (error.status === 500) {
          errorMessage = 'The AI service is currently unavailable. Please try again later.';
        } else if (error.status === 0) {
          errorMessage = error.message; // Network error message
        } else {
          errorMessage = error.message;
        }
      }
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearError = () => {
    setError(null);
  };

  return (
    <div className="chat-container">
      <MessageList messages={messages} isLoading={isLoading} error={error} onClearError={handleClearError} />
      <MessageInput onSendMessage={handleSendMessage} disabled={isLoading} />
    </div>
  );
}