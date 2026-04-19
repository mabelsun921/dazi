import React, { useState, useEffect } from 'react'
import './App.css'
import API from './utils/api'
import SquarePage from './pages/SquarePage'
import SoulPage from './pages/SoulPage'
import MessagePage from './pages/MessagePage'
import ProfilePage from './pages/ProfilePage'
import UserProfilePage from './pages/UserProfilePage'
import ActivityDetailPage from './pages/ActivityDetailPage'

function App() {
  const [currentPage, setCurrentPage] = useState('square')
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [currentUser, setCurrentUser] = useState(null)
  const [messageToUserId, setMessageToUserId] = useState(null)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authMode, setAuthMode] = useState('login') // 'login' or 'register'
  const [authForm, setAuthForm] = useState({
    email: '',
    password: '',
    name: ''
  })
  const [viewedUserId, setViewedUserId] = useState(null) // 查看其他用户主页
  const [viewedActivity, setViewedActivity] = useState(null) // 查看活动详情
  const [showProfileModal, setShowProfileModal] = useState(false) // 强制填写资料弹窗

  // Check if user is already logged in
  useEffect(() => {
    const checkLoginStatus = () => {
      const userData = localStorage.getItem('currentUser')
      if (userData) {
        setCurrentUser(JSON.parse(userData))
        setIsLoggedIn(true)
      }
    }
    checkLoginStatus()
  }, [])

  const handleAuthSubmit = async (e) => {
    e.preventDefault()
    try {
      const url = authMode === 'login' 
        ? API.auth.login
        : API.auth.register
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(authForm)
      })
      
      if (response.ok) {
        const data = await response.json()
        setCurrentUser(data)
        setIsLoggedIn(true)
        localStorage.setItem('currentUser', JSON.stringify(data))
        setShowAuthModal(false)
        
        if (authMode === 'register') {
          setShowProfileModal(true)
        } else {
          const profileResponse = await fetch(API.profile.get(data.user_id))
          if (profileResponse.ok) {
            const profileData = await profileResponse.json()
            const hasProfile = profileData.name && profileData.name.trim() !== ''
            if (!hasProfile) {
              setShowProfileModal(true)
            }
          }
        }
      } else {
        const error = await response.json()
        alert(error.error || '认证失败')
      }
    } catch (error) {
      console.error('认证错误:', error)
      alert('网络错误，请稍后重试')
    }
  }

  const handleLogout = () => {
    setIsLoggedIn(false)
    setCurrentUser(null)
    localStorage.removeItem('currentUser')
  }

  return (
    <div className="App">
      <header className="header">
        <h1>搭子</h1>
        <div className="header-actions">
          {!isLoggedIn ? (
            <button className="login-button" onClick={() => setShowAuthModal(true)}>
              登录/注册
            </button>
          ) : (
            <button className="logout-button" onClick={handleLogout}>
              退出
            </button>
          )}
        </div>
      </header>
      
      <main>
        {currentPage === 'square' && (
          <SquarePage 
            isLoggedIn={isLoggedIn} 
            currentUser={currentUser}
            currentPage={currentPage}
            onViewUserProfile={(userId) => {
              setViewedUserId(userId)
              setCurrentPage('userprofile')
            }}
            onViewActivity={(activity) => {
              setViewedActivity(activity)
              setCurrentPage('activitydetail')
            }}
          />
        )}
        {currentPage === 'soul' && <SoulPage isLoggedIn={isLoggedIn} currentUser={currentUser} currentPage={currentPage} onNavigateToMessage={(userId) => { setMessageToUserId(userId); setCurrentPage('message'); }} />}
        {currentPage === 'message' && <MessagePage isLoggedIn={isLoggedIn} currentUser={currentUser} currentPage={currentPage} initialUserId={messageToUserId} />}
        {currentPage === 'profile' && <ProfilePage isLoggedIn={isLoggedIn} currentUser={currentUser} onProfileComplete={() => setShowProfileModal(false)} />}
        {currentPage === 'userprofile' && (
          <UserProfilePage 
            userId={viewedUserId} 
            currentUser={currentUser} 
            isLoggedIn={isLoggedIn}
            onBack={() => setCurrentPage('square')}
            onNavigateToMessage={() => setCurrentPage('message')}
          />
        )}
        {currentPage === 'activitydetail' && (
          <ActivityDetailPage 
            activity={viewedActivity}
            currentUser={currentUser}
            isLoggedIn={isLoggedIn}
            onBack={() => setCurrentPage('square')}
            onViewUserProfile={(userId) => {
              setViewedUserId(userId)
              setCurrentPage('userprofile')
            }}
            onNavigateToMessage={(userId) => {
              setMessageToUserId(userId)
              setCurrentPage('message')
            }}
          />
        )}
      </main>
      
      <nav className="bottom-nav">
        <div 
          className={`bottom-nav-item ${currentPage === 'square' ? 'active' : ''}`}
          onClick={() => setCurrentPage('square')}
        >
          <i>🏠</i>
          <span>广场</span>
        </div>
        <div 
          className={`bottom-nav-item ${currentPage === 'soul' ? 'active' : ''}`}
          onClick={() => setCurrentPage('soul')}
        >
          <i>💖</i>
          <span>灵魂</span>
        </div>
        <div 
          className={`bottom-nav-item ${currentPage === 'message' ? 'active' : ''}`}
          onClick={() => setCurrentPage('message')}
        >
          <i>💬</i>
          <span>消息</span>
        </div>
        <div 
          className={`bottom-nav-item ${currentPage === 'profile' ? 'active' : ''}`}
          onClick={() => setCurrentPage('profile')}
        >
          <i>👤</i>
          <span>我</span>
        </div>
      </nav>

      {/* 登录/注册弹窗 */}
      {showAuthModal && (
        <div className="modal-overlay">
          <div className="auth-modal">
            <div className="modal-header">
              <h2>{authMode === 'login' ? '登录' : '注册'}</h2>
              <button className="close-button" onClick={() => setShowAuthModal(false)}>×</button>
            </div>
            <form onSubmit={handleAuthSubmit}>
              {authMode === 'register' && (
                <div className="form-group">
                  <label>用户名</label>
                  <input
                    type="text"
                    name="name"
                    value={authForm.name}
                    onChange={(e) => setAuthForm({...authForm, name: e.target.value})}
                    required
                  />
                </div>
              )}
              <div className="form-group">
                <label>邮箱</label>
                <input
                  type="email"
                  name="email"
                  value={authForm.email}
                  onChange={(e) => setAuthForm({...authForm, email: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>密码</label>
                <input
                  type="password"
                  name="password"
                  value={authForm.password}
                  onChange={(e) => setAuthForm({...authForm, password: e.target.value})}
                  required
                />
              </div>
              <button type="submit" className="auth-button">
                {authMode === 'login' ? '登录' : '注册'}
              </button>
              <div className="auth-switch">
                {authMode === 'login' ? (
                  <p>还没有账号？ <span onClick={() => setAuthMode('register')}>立即注册</span></p>
                ) : (
                  <p>已有账号？ <span onClick={() => setAuthMode('login')}>立即登录</span></p>
                )}
              </div>
            </form>
          </div>
        </div>
      )}

      {showProfileModal && (
        <div className="modal-overlay" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="profile-modal" style={{ maxHeight: '90vh', overflow: 'auto' }}>
            <div className="modal-header">
              <h2>完善个人资料</h2>
            </div>
            <div style={{ padding: '20px', textAlign: 'center' }}>
              <p style={{ marginBottom: '20px', color: '#666' }}>
                请先完善个人资料，以便更好地使用平台功能
              </p>
              <button 
                className="btn btn-primary"
                onClick={() => {
                  setShowProfileModal(false)
                  setCurrentPage('profile')
                }}
              >
                去完善资料
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
