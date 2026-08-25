/**
 * Chat Window Component
 * 
 * Main chat interface that orchestrates the chat experience.
 */

import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { chatApi } from '../../services/chatApi';
import { APIError } from '../../utils/api';
import type { ChatMessage } from '../../types/chat';
import { EmptyState } from './EmptyState';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import './ChatWindow.css';

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { token, logout } = useAuth();
  const navigate = useNavigate();

  const handleSendMessage = async (question: string) => {
    if (!token) {
      logout();
      navigate('/login');
      return;
    }

    setError(null);

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    setIsLoading(true);

    try {
      // Call backend RAG API
      const response = await chatApi.sendMessage(question, token);

      // Add assistant response with sources
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      if (err instanceof APIError) {
        if (err.status === 401) {
          // Unauthorized - redirect to login
          logout();
          navigate('/login');
          return;
        }
        
        setError(
          err.status === 429
            ? 'Too many requests. Please wait a moment and try again.'
            : 'Something went wrong while processing your question. Please try again.'
        );
      } else {
        setError('An unexpected error occurred');
      }

      // Remove user message on error
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (question: string) => {
    handleSendMessage(question);
  };

  return (
    <div className="chat-window">
      {error && (
        <div className="chat-error">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Close error">
            ✕
          </button>
        </div>
      )}

      {messages.length === 0 ? (
        <EmptyState onSuggestionClick={handleSuggestionClick} />
      ) : (
        <MessageList messages={messages} isLoading={isLoading} />
      )}

      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}
