/**
 * Chat Sidebar Component
 * 
 * Provides helpful information and quick actions for users.
 */

import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import './ChatSidebar.css';

export function ChatSidebar() {
  const { user } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const tips = [
    {
      icon: '💡',
      title: 'Be Specific',
      description: 'Ask specific questions for more accurate answers.'
    },
    {
      icon: '📝',
      title: 'Use Keywords',
      description: 'Include relevant keywords related to your question.'
    },
    {
      icon: '🔍',
      title: 'Check Sources',
      description: 'Review source documents and relevance scores.'
    },
    {
      icon: '⚡',
      title: 'Quick Queries',
      description: 'Short, focused questions work best.'
    }
  ];

  const quickQuestions = [
    'What is the deployment process?',
    'What are the working hours?',
    'What is the leave policy?',
    'How do I submit expenses?'
  ];

  return (
    <aside className={`chat-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <button 
        className="sidebar-toggle"
        onClick={() => setIsCollapsed(!isCollapsed)}
        aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {isCollapsed ? '→' : '←'}
      </button>

      {!isCollapsed && (
        <div className="sidebar-content">
          {/* User Info Card */}
          {user && (
            <div className="sidebar-card user-card">
              <div className="user-avatar">
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="user-info-text">
                <div className="user-full-name">{user.full_name}</div>
                <div className="user-department-badge">{user.department.name}</div>
              </div>
            </div>
          )}

          {/* Tips Section */}
          <div className="sidebar-section">
            <h3 className="sidebar-title">💡 Tips for Better Results</h3>
            <div className="tips-list">
              {tips.map((tip, index) => (
                <div key={index} className="tip-item">
                  <span className="tip-icon">{tip.icon}</span>
                  <div className="tip-content">
                    <div className="tip-title">{tip.title}</div>
                    <div className="tip-description">{tip.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Questions */}
          <div className="sidebar-section">
            <h3 className="sidebar-title">⚡ Quick Questions</h3>
            <div className="quick-questions">
              {quickQuestions.map((question, index) => (
                <div key={index} className="quick-question-item">
                  <span className="quick-question-icon">❓</span>
                  <span className="quick-question-text">{question}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Department Info */}
          <div className="sidebar-section">
            <h3 className="sidebar-title">🔒 Your Access</h3>
            <div className="access-info">
              <p className="access-text">
                You can only access documents from your <strong>{user?.department.name}</strong> department.
              </p>
              <p className="access-note">
                All answers are based on authorized content with source verification.
              </p>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
