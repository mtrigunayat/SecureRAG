/**
 * Chat API service
 */

import { apiClient } from './apiClient';
import { handleResponse } from '../utils/api';
import type { ChatRequest, ChatResponse } from '../types/chat';

export const chatApi = {
  /**
   * Send a question and get an answer with sources
   * 
   * POST /api/chat
   * 
   * Requires authentication token.
   * Backend determines department from authenticated user.
   * Client sends ONLY the question.
   */
  async sendMessage(
    question: string,
    token: string
  ): Promise<ChatResponse> {
    const request: ChatRequest = { question };
    const response = await apiClient.post('/api/chat', request, token);
    return handleResponse<ChatResponse>(response as Response);
  },
};
