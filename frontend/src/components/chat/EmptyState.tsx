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
  { icon: '🚀', text: 'What is our deployment process for production releases?', category: 'Engineering' },
  { icon: '🧪', text: 'What test coverage is required for new code?', category: 'Engineering' },
  { icon: '🚨', text: 'What is the SEV-1 escalation process?', category: 'Engineering' },
  { icon: '💰', text: 'What is the standard discount I can offer without manager approval?', category: 'Sales' },
  { icon: '💵', text: 'What is the monthly price for the Growth tier?', category: 'Sales' },
  { icon: '🏖️', text: 'How many days of annual leave do employees get?', category: 'HR' },
  { icon: '🏥', text: 'What is covered under the health insurance benefit?', category: 'HR' },
];

export function EmptyState({ onSuggestionClick }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state-content">
        <div className="welcome-header">
          <div className="welcome-icon">🤖</div>
          <h2 className="empty-state-title">Welcome to Secure RAG Assistant</h2>
          <p className="empty-state-description">
            Your AI-powered knowledge assistant with department-level security.
            <br />
            Ask questions about your organization's policies, procedures, and documentation.
          </p>
        </div>

        <div className="features-highlight">
          <div className="feature-badge">
            <span className="feature-badge-icon">🔒</span>
            <span>Secure Access</span>
          </div>
          <div className="feature-badge">
            <span className="feature-badge-icon">⚡</span>
            <span>Instant Answers</span>
          </div>
          <div className="feature-badge">
            <span className="feature-badge-icon">📊</span>
            <span>Source Verified</span>
          </div>
        </div>

        <div className="mcp-info-banner">
          <div className="mcp-banner-content">
            <span className="mcp-banner-icon">🔌</span>
            <div className="mcp-banner-text">
              <div className="mcp-banner-title">MCP Server Integration Enabled</div>
              <div className="mcp-banner-description">
                This system now supports Model Context Protocol (MCP) for seamless integration with external AI models and enterprise automation tools.
              </div>
            </div>
          </div>
        </div>

        <div className="suggestions">
          <p className="suggestions-label">Try asking:</p>
          <div className="suggestions-grid">
            {EXAMPLE_QUESTIONS.map((question, index) => (
              <button
                key={index}
                className="suggestion-button"
                onClick={() => onSuggestionClick(question.text)}
              >
                <span className="suggestion-icon">{question.icon}</span>
                <div className="suggestion-content">
                  <span className="suggestion-text">{question.text}</span>
                  <span className="suggestion-category">{question.category}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
