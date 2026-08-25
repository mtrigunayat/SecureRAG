/**
 * Chat types matching backend Phase 9 schema
 */

export interface ChatRequest {
  question: string;
}

export interface ChatSource {
  document_id: number;
  document_name: string;
  department_name: string;
  sensitivity: string;
  page_start: number;
  page_end: number;
  score: number;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  retrieved_count: number;
  user_department_name: string;
  model: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
  createdAt: string;
}

export interface ChatError {
  detail: string;
}
