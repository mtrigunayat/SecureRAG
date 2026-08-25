/**
 * Chat Page
 */

import { Header } from '../components/layout/Header';
import { ChatWindow } from '../components/chat/ChatWindow';

export function ChatPage() {
  return (
    <div className="chat-page">
      <Header />
      <ChatWindow />
    </div>
  );
}
