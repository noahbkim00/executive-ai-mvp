import type { ConversationRequest, ConversationResponse } from '../types/chat';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  id: string;
  role: 'assistant';
  content: string;
  timestamp: string; // ISO string from backend
}

export interface ConversationProgress {
  phase: "initial" | "questioning" | "completed" | "error";
  status: "active" | "paused" | "completed" | "abandoned";
  current_question: number;
  total_questions: number;
  progress_percentage: number;
  is_complete: boolean;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export const chatApi = {
  async sendMessage(message: string): Promise<ChatResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorData
        );
      }

      const data: ChatResponse = await response.json();
      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      // Network or other errors
      throw new ApiError(
        'Failed to connect to the server. Please check your connection and try again.',
        0
      );
    }
  },

  async sendConversationMessage(request: ConversationRequest): Promise<ConversationResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/conversation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorData
        );
      }

      const data: ConversationResponse = await response.json();
      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      throw new ApiError(
        'Failed to connect to the server. Please check your connection and try again.',
        0
      );
    }
  },

  async getConversationProgress(conversationId: string): Promise<ConversationProgress> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/conversation/${conversationId}/progress`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorData
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      throw new ApiError(
        'Failed to connect to the server. Please check your connection and try again.',
        0
      );
    }
  }
};