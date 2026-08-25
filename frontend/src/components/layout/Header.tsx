/**
 * Header Component
 */

import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { ConfirmModal } from '../common/ConfirmModal';
import './Header.css';

export function Header() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  const handleLogoutClick = () => {
    setShowLogoutModal(true);
  };

  const handleConfirmLogout = () => {
    setShowLogoutModal(false);
    logout();
    navigate('/login', { replace: true });
  };

  const handleCancelLogout = () => {
    setShowLogoutModal(false);
  };

  return (
    <>
      <header className="app-header">
        <div className="header-content">
          <h1 className="header-title">Secure RAG Assistant</h1>
          <button onClick={handleLogoutClick} className="logout-button">
            Logout
          </button>
        </div>
      </header>

      <ConfirmModal
        isOpen={showLogoutModal}
        title="Confirm Logout"
        message="Are you sure you want to log out? You will need to sign in again to access the chat."
        confirmText="Logout"
        cancelText="Cancel"
        variant="warning"
        onConfirm={handleConfirmLogout}
        onCancel={handleCancelLogout}
      />
    </>
  );
}
