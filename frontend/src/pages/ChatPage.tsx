/**
 * Chat Page
 */

import { Header } from '../components/layout/Header';
import { ChatWindow } from '../components/chat/ChatWindow';
import { ChatSidebar } from '../components/chat/ChatSidebar';
import './ChatPage.css';

export function ChatPage() {
  return (
    <div className="chat-page">
      <Header />
      <div className="chat-layout">
        <ChatSidebar />
        <ChatWindow />
      </div>
    </div>
  );
}
