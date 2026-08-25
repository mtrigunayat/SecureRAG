/**
 * Source List Component
 * 
 * Displays document sources for assistant responses.
 * Sources are backend-controlled (not LLM-generated).
 */

import type { ChatSource } from '../../types/chat';
import './SourceList.css';

interface SourceListProps {
  sources: ChatSource[];
}

export function SourceList({ sources }: SourceListProps) {
  if (sources.length === 0) {
    return null;
  }

  return (
    <div className="source-list">
      <div className="source-header">Sources</div>
      <div className="sources">
        {sources.map((source, index) => (
          <div key={source.document_id} className="source-item">
            <div className="source-title">
              <span className="source-number">[{index + 1}]</span>
              <span className="source-name">{source.document_name}</span>
            </div>
            <div className="source-meta">
              <span>Pages {source.page_start}–{source.page_end}</span>
              <span className="source-separator">•</span>
              <span className="source-department">{source.department_name}</span>
              <span className="source-separator">•</span>
              <span className="source-relevance">
                {(source.score * 100).toFixed(0)}% relevant
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
