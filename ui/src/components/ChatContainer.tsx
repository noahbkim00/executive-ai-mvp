import { useState } from 'react';
import { Message, ConversationState, ConversationPhase, ConversationStatus } from '../types/chat';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { chatApi, ApiError } from '../services/api';
import './ChatContainer.css';

export function ChatContainer() {
  const [conversationState, setConversationState] = useState<ConversationState>({
    conversation_id: null,
    phase: 'initial' as ConversationPhase,
    status: 'active' as ConversationStatus,
    messages: [],
    progress: null,
    current_question: null,
    isLoading: false,
    error: null,
  });

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setConversationState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    try {
      const response = await chatApi.sendConversationMessage({
        message: content,
        conversation_id: conversationState.conversation_id || undefined,
      });
      
      // Combine response content and question into single message
      let messageContent = response.response_content;
      if (response.next_question) {
        messageContent += '\n\n' + response.next_question;
      }

      const assistantMessage: Message = {
        id: response.conversation_id + '_' + Date.now(),
        role: 'assistant',
        content: messageContent,
        timestamp: new Date(response.timestamp),
      };

      const messages = [assistantMessage];
      
      setConversationState(prev => ({
        ...prev,
        conversation_id: response.conversation_id,
        phase: response.phase,
        status: response.status,
        messages: [...prev.messages, ...messages],
        progress: response.progress,
        current_question: response.next_question || null,
        isLoading: false,
      }));
    } catch (error) {
      console.error('Chat error:', error);
      
      let errorMessage = 'Something went wrong. Please try again.';
      
      if (error instanceof ApiError) {
        if (error.status === 500) {
          errorMessage = 'The AI service is currently unavailable. Please try again later.';
        } else if (error.status === 0) {
          errorMessage = error.message;
        } else {
          errorMessage = error.message;
        }
      }
      
      setConversationState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
    }
  };

  const handleClearError = () => {
    setConversationState(prev => ({
      ...prev,
      error: null,
    }));
  };

  return (
    <div className="chat-container">
      {conversationState.progress && conversationState.phase === 'questioning' && (
        <div className="progress-indicator">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${conversationState.progress.progress_percentage}%` }}
            />
          </div>
          <span className="progress-text">
            Question {conversationState.progress.current_question} of {conversationState.progress.total_questions}
          </span>
        </div>
      )}
      <MessageList 
        messages={conversationState.messages} 
        isLoading={conversationState.isLoading} 
        error={conversationState.error} 
        onClearError={handleClearError}
        isCompleted={conversationState.phase === 'completed'}
      />
      <MessageInput 
        onSendMessage={handleSendMessage} 
        disabled={conversationState.isLoading || conversationState.phase === 'completed'}
        placeholder={
          conversationState.phase === 'initial' 
            ? "Describe the executive role you're looking to fill..."
            : conversationState.phase === 'questioning'
            ? "Your answer..."
            : conversationState.phase === 'completed'
            ? "Conversation completed"
            : "Send a message..."
        }
      />
    </div>
  );
}