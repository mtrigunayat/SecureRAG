/**
 * Empty State Component
 * 
 * Shown when there are no messages in the chat.
 */

import './EmptyState.css';

interface EmptyStateProps {
  onSuggestionClick: (question: string) => void;
}

const EXAMPLE_QUESTIONS = [
  'What is the deployment process?',
  'What is the leave policy?',
  'What are the working hours?',
];

export function EmptyState({ onSuggestionClick }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state-content">
        <h2 className="empty-state-title">Welcome to Secure RAG Assistant</h2>
        <p className="empty-state-description">
          Ask questions about your organization's knowledge base.
          <br />
          Only information from your department will be retrieved.
        </p>

        <div className="suggestions">
          <p className="suggestions-label">Try asking:</p>
          <div className="suggestions-grid">
            {EXAMPLE_QUESTIONS.map((question) => (
              <button
                key={question}
                className="suggestion-button"
                onClick={() => onSuggestionClick(question)}
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
