/**
 * Home/Landing Page
 * 
 * Project information and entry point for users.
 */

import { Link } from 'react-router-dom';
import './HomePage.css';

export function HomePage() {
  return (
    <div className="home-page">
      <div className="home-container">
        {/* Hero Section */}
        <section className="hero-section">
          <div className="logo-badge">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <rect width="48" height="48" rx="12" fill="url(#gradient)" />
              <path d="M24 14L32 20V28L24 34L16 28V20L24 14Z" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="24" cy="24" r="3" fill="white" />
              <defs>
                <linearGradient id="gradient" x1="0" y1="0" x2="48" y2="48">
                  <stop offset="0%" stopColor="#667eea" />
                  <stop offset="100%" stopColor="#764ba2" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          
          <h1 className="hero-title">Secure RAG Assistant</h1>
          
          <p className="hero-subtitle">
            Enterprise-grade Retrieval Augmented Generation with department-level access control
          </p>

          <div className="cta-buttons">
            <Link to="/login" className="btn btn-primary">
              Get Started
            </Link>
            <a href="#features" className="btn btn-secondary">
              Learn More
            </a>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="features-section">
          <h2 className="section-title">Key Features</h2>
          
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">🔒</div>
              <h3>Department-Level Security</h3>
              <p>
                Role-based access control ensures users only access documents relevant to their department (Engineering, HR, Sales).
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">🤖</div>
              <h3>Intelligent RAG System</h3>
              <p>
                Advanced retrieval-augmented generation powered by vector embeddings and semantic search for accurate answers.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">📄</div>
              <h3>PDF Document Processing</h3>
              <p>
                Automatic extraction, chunking, and indexing of PDF documents with metadata preservation.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">⚡</div>
              <h3>Real-time Responses</h3>
              <p>
                Fast query processing with context-aware answers and source attribution for transparency.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">🔐</div>
              <h3>JWT Authentication</h3>
              <p>
                Secure token-based authentication with encrypted password storage using bcrypt.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">📊</div>
              <h3>Source Attribution</h3>
              <p>
                Every answer includes source documents with similarity scores for full traceability.
              </p>
            </div>
          </div>
        </section>

        {/* Tech Stack Section */}
        <section className="tech-section">
          <h2 className="section-title">Technology Stack</h2>
          
          <div className="tech-grid">
            <div className="tech-group">
              <h3>Backend</h3>
              <ul>
                <li>FastAPI (Python)</li>
                <li>PostgreSQL</li>
                <li>Qdrant Vector DB</li>
                <li>SQLAlchemy ORM</li>
              </ul>
            </div>

            <div className="tech-group">
              <h3>Frontend</h3>
              <ul>
                <li>React + TypeScript</li>
                <li>React Router</li>
                <li>Vite</li>
                <li>Modern CSS</li>
              </ul>
            </div>

            <div className="tech-group">
              <h3>AI & ML</h3>
              <ul>
                <li>OpenAI GPT-4</li>
                <li>Sentence Transformers</li>
                <li>Vector Embeddings</li>
                <li>Semantic Search</li>
              </ul>
            </div>

            <div className="tech-group">
              <h3>Security</h3>
              <ul>
                <li>JWT Tokens</li>
                <li>bcrypt Hashing</li>
                <li>CORS Protection</li>
                <li>RBAC Authorization</li>
              </ul>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="cta-section">
          <h2>Ready to get started?</h2>
          <p>Log in to access your department's knowledge base and start asking questions.</p>
          <Link to="/login" className="btn btn-primary btn-large">
            Login Now
          </Link>
        </section>

        {/* Footer */}
        <footer className="home-footer">
          <p>&copy; 2026 Secure RAG Assistant. Enterprise Knowledge Management System.</p>
        </footer>
      </div>
    </div>
  );
}
