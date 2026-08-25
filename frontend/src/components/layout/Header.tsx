/**
 * Header Component
 */

import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { ConfirmModal } from '../common/ConfirmModal';
import './Header.css';

export function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  const handleLogoutClick = () => {
    setShowLogoutModal(true);
  };

  const handleConfirmLogout = () => {
    setShowLogoutModal(false);
    logout();
    navigate('/', { replace: true });
  };

  const handleCancelLogout = () => {
    setShowLogoutModal(false);
  };

  // Get department display info
  const getDepartmentInfo = () => {
    if (!user?.department) return { name: 'Unknown', color: '#6b7280' };
    
    const deptName = user.department.name.toLowerCase();
    const departmentColors: Record<string, { name: string; color: string }> = {
      'engineering': { name: 'Engineering', color: '#3b82f6' },
      'hr': { name: 'HR', color: '#10b981' },
      'sales': { name: 'Sales', color: '#f59e0b' },
    };
    
    return departmentColors[deptName] || { 
      name: user.department.name.charAt(0).toUpperCase() + user.department.name.slice(1), 
      color: '#6b7280' 
    };
  };

  const deptInfo = getDepartmentInfo();

  return (
    <>
      <header className="app-header">
        <div className="header-content">
          <h1 className="header-title">Secure RAG Assistant</h1>
          
          {user && (
            <div className="user-info">
              <div className="user-details">
                <div className="user-name">{user.full_name}</div>
                <div className="user-username">@{user.username}</div>
              </div>
              <div 
                className="department-badge" 
                style={{ backgroundColor: deptInfo.color }}
              >
                {deptInfo.name}
              </div>
              <button onClick={handleLogoutClick} className="logout-button">
                Logout
              </button>
            </div>
          )}
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
