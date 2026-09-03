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

          {/* Stats Section */}
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-number">🔒</div>
              <div className="stat-label">Department-Level Security</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">⚡</div>
              <div className="stat-label">Real-time Responses</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">📊</div>
              <div className="stat-label">Source Attribution</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">🤖</div>
              <div className="stat-label">AI-Powered Search</div>
            </div>
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

        {/* How It Works Section */}
        <section className="how-it-works-section">
          <h2 className="section-title">How It Works</h2>
          
          <div className="steps-container">
            <div className="step-item">
              <div className="step-number">1</div>
              <div className="step-content">
                <h3>Login Securely</h3>
                <p>Authenticate with your credentials and get assigned to your department.</p>
              </div>
            </div>

            <div className="step-connector">→</div>

            <div className="step-item">
              <div className="step-number">2</div>
              <div className="step-content">
                <h3>Ask Questions</h3>
                <p>Type your question in natural language about company policies and procedures.</p>
              </div>
            </div>

            <div className="step-connector">→</div>

            <div className="step-item">
              <div className="step-number">3</div>
              <div className="step-content">
                <h3>Get Answers</h3>
                <p>Receive AI-powered answers based only on documents you're authorized to access.</p>
              </div>
            </div>

            <div className="step-connector">→</div>

            <div className="step-item">
              <div className="step-number">4</div>
              <div className="step-content">
                <h3>Verify Sources</h3>
                <p>Review source documents and relevance scores for full transparency.</p>
              </div>
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

        {/* MCP Server Integration Section */}
        <section className="mcp-section">
          <div className="mcp-badge">
            <span className="mcp-label">NEW</span>
          </div>
          <h2 className="section-title">MCP Server Integration</h2>
          <p className="section-subtitle">
            Advanced Model Context Protocol (MCP) support for external AI integrations and automation
          </p>
          
          <div className="mcp-grid">
            <div className="mcp-card">
              <div className="mcp-icon">🔌</div>
              <h3>Seamless Integration</h3>
              <p>Connect external AI models and tools through our standardized MCP server interface.</p>
              <div className="mcp-feature">✓ JSON-RPC Communication</div>
              <div className="mcp-feature">✓ Protocol Buffers Support</div>
            </div>

            <div className="mcp-card">
              <div className="mcp-icon">🔑</div>
              <h3>Secure Token Management</h3>
              <p>Generate and manage API tokens for external integrations with full audit trails.</p>
              <div className="mcp-feature">✓ Rate Limiting</div>
              <div className="mcp-feature">✓ Token Revocation</div>
            </div>

            <div className="mcp-card">
              <div className="mcp-icon">🚀</div>
              <h3>Enterprise Automation</h3>
              <p>Automate knowledge management workflows with external applications and services.</p>
              <div className="mcp-feature">✓ Webhook Support</div>
              <div className="mcp-feature">✓ Async Processing</div>
            </div>

            <div className="mcp-card">
              <div className="mcp-icon">📊</div>
              <h3>Advanced Analytics</h3>
              <p>Monitor integration usage and performance metrics through comprehensive dashboards.</p>
              <div className="mcp-feature">✓ Usage Tracking</div>
              <div className="mcp-feature">✓ Performance Metrics</div>
            </div>
          </div>

          <div className="mcp-benefits">
            <h3>Benefits of MCP Server Integration</h3>
            <div className="benefits-list">
              <div className="benefit-box">
                <span className="benefit-number">01</span>
                <div className="benefit-content">
                  <h4>Extended Capabilities</h4>
                  <p>Integrate with third-party AI models and tools without modifying core infrastructure</p>
                </div>
              </div>

              <div className="benefit-box">
                <span className="benefit-number">02</span>
                <div className="benefit-content">
                  <h4>Custom Workflows</h4>
                  <p>Build automated workflows that connect Secure RAG with your existing tools</p>
                </div>
              </div>

              <div className="benefit-box">
                <span className="benefit-number">03</span>
                <div className="benefit-content">
                  <h4>Scalable Solutions</h4>
                  <p>Scale your knowledge management across departments and external systems</p>
                </div>
              </div>

              <div className="benefit-box">
                <span className="benefit-number">04</span>
                <div className="benefit-content">
                  <h4>Security First</h4>
                  <p>Enterprise-grade security with department-level access control throughout</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Benefits Section */}
        <section className="benefits-section">
          <h2 className="section-title">Why Choose Secure RAG?</h2>
          
          <div className="benefits-grid">
            <div className="benefit-item">
              <div className="benefit-icon">💡</div>
              <h3>Instant Knowledge Access</h3>
              <p>Find answers to company policies instantly without searching through multiple documents.</p>
            </div>

            <div className="benefit-item">
              <div className="benefit-icon">🛡️</div>
              <h3>Privacy Protected</h3>
              <p>Department-level isolation ensures you only see information you're authorized to access.</p>
            </div>

            <div className="benefit-item">
              <div className="benefit-icon">✅</div>
              <h3>Verified Accuracy</h3>
              <p>Every answer includes source attribution with relevance scores for verification.</p>
            </div>

            <div className="benefit-item">
              <div className="benefit-icon">⏱️</div>
              <h3>Save Time</h3>
              <p>Get answers in seconds instead of spending hours searching through documents.</p>
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
