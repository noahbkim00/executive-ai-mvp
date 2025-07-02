export type MessageRole = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
}

// Conversation types for multi-phase flow
export type ConversationPhase = 'initial' | 'questioning' | 'completed' | 'error';
export type ConversationStatus = 'active' | 'completed' | 'error';

export interface ConversationProgress {
  phase: string;
  current_question: number;
  total_questions: number;
  progress_percentage: number;
  is_complete: boolean;
}

export interface ConversationRequest {
  message: string;
  conversation_id?: string;
}

export interface ConversationResponse {
  conversation_id: string;
  phase: ConversationPhase;
  status: ConversationStatus;
  response_content: string;
  progress: ConversationProgress;
  next_question?: string;
  is_complete: boolean;
  timestamp: string;
}

export interface ConversationState {
  conversation_id: string | null;
  phase: ConversationPhase;
  status: ConversationStatus;
  messages: Message[];
  progress: ConversationProgress | null;
  current_question: string | null;
  isLoading: boolean;
  error: string | null;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
}