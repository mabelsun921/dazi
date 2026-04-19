import React, { useState, useEffect } from 'react'
import API from '../utils/api'

const UserProfilePage = ({ userId, currentUser, isLoggedIn, onBack, onNavigateToMessage }) => {
  const [userProfile, setUserProfile] = useState(null)
  const [userActivities, setUserActivities] = useState([])
  const [userReviews, setUserReviews] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('activities')

  useEffect(() => {
    if (userId) {
      fetchUserData()
    }
  }, [userId])

  const fetchUserData = async () => {
    setIsLoading(true)
    try {
      const profileResponse = await fetch(API.profile.get(userId))
      if (profileResponse.ok) {
        const profileData = await profileResponse.json()
        setUserProfile(profileData)
      }

      const detailsResponse = await fetch(API.user.details(userId))
      if (detailsResponse.ok) {
        const detailsData = await detailsResponse.json()
        setUserActivities(detailsData.ongoing_activities || [])
        setUserReviews(detailsData.reviews || [])
      }
    } catch (error) {
      console.error('Error fetching user data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSendMessage = async () => {
    if (!isLoggedIn) {
      alert('请先登录')
      return
    }

    try {
      const currentUserId = currentUser.user_id || currentUser._id
      const response = await fetch(API.conversations.create, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user1_id: currentUserId,
          user2_id: userId
        })
      })

      if (response.ok) {
        const data = await response.json()
        if (onNavigateToMessage) {
          onNavigateToMessage()
        }
      } else {
        alert('发起对话失败')
      }
    } catch (error) {
      console.error('Error creating conversation:', error)
      alert('网络错误')
    }
  }

  if (isLoading) {
    return (
      <div className="page profile-page">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>加载中...</p>
        </div>
      </div>
    )
  }

  if (!userProfile) {
    return (
      <div className="page profile-page">
        <div className="header">
          <button className="back-btn" onClick={onBack}>← 返回</button>
        </div>
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <p>用户不存在</p>
        </div>
      </div>
    )
  }

  const isOwnProfile = currentUser && (currentUser.user_id === userId || currentUser._id === userId)

  return (
    <div className="page profile-page">
      <div className="header">
        <button className="back-btn" onClick={onBack}>← 返回</button>
      </div>

      <div className="card profile-card">
        <div className="profile-avatar" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
          {userProfile.name?.charAt(0) || '?'}
        </div>
        
        <div className="profile-name">{userProfile.name || '匿名用户'}</div>
        
        <div className="profile-rating">
          {'★'.repeat(Math.floor(userProfile.reputation || 0))}
          {'☆'.repeat(5 - Math.floor(userProfile.reputation || 0))}
          <span style={{ marginLeft: '5px' }}>{(userProfile.reputation || 0).toFixed(1)}</span>
        </div>
        
        <div className="profile-info-grid">
          {userProfile.mbti && (
            <div className="profile-info-item">
              <div className="profile-info-label">MBTI</div>
              <div className="profile-info-value">{userProfile.mbti}</div>
            </div>
          )}
          {userProfile.occupation && (
            <div className="profile-info-item">
              <div className="profile-info-label">职业</div>
              <div className="profile-info-value">{userProfile.occupation}</div>
            </div>
          )}
          {userProfile.location?.city && (
            <div className="profile-info-item">
              <div className="profile-info-label">城市</div>
              <div className="profile-info-value">{userProfile.location.city}{userProfile.location.district || ''}</div>
            </div>
          )}
          {userProfile.gender && (
            <div className="profile-info-item">
              <div className="profile-info-label">性别</div>
              <div className="profile-info-value">{userProfile.gender}</div>
            </div>
          )}
          {userProfile.age > 0 && (
            <div className="profile-info-item">
              <div className="profile-info-label">年龄</div>
              <div className="profile-info-value">{userProfile.age}岁</div>
            </div>
          )}
          {userProfile.hobbies?.length > 0 && (
            <div className="profile-info-item">
              <div className="profile-info-label">爱好</div>
              <div className="profile-info-value">{userProfile.hobbies.join(', ')}</div>
            </div>
          )}
        </div>
        
        {userProfile.ai_tags?.length > 0 && (
          <div className="profile-tags">
            {userProfile.ai_tags.map((tag, index) => (
              <span key={index} className="profile-tag">
                {tag}
              </span>
            ))}
          </div>
        )}
        
        <div className="profile-description">
          "{userProfile.personality || '暂无个人简介'}"
        </div>

        {!isOwnProfile && isLoggedIn && (
          <div style={{ marginTop: '1.5rem' }}>
            <button className="btn btn-primary" onClick={handleSendMessage} style={{ width: '100%' }}>
              💬 发消息
            </button>
          </div>
        )}
      </div>

      <div className="tabs-container" style={{ marginTop: '1rem' }}>
        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'activities' ? 'active' : ''}`}
            onClick={() => setActiveTab('activities')}
          >
            活动 ({userActivities.length})
          </button>
          <button 
            className={`tab ${activeTab === 'reviews' ? 'active' : ''}`}
            onClick={() => setActiveTab('reviews')}
          >
            评价 ({userReviews.length})
          </button>
        </div>
      </div>

      <div className="tab-content" style={{ marginTop: '1rem' }}>
        {activeTab === 'activities' && (
          <div className="activities-section">
            {userActivities.length > 0 ? (
              userActivities.map(activity => (
                <div key={activity._id} className="card activity-item-card" style={{ marginBottom: '0.75rem' }}>
                  <div className="activity-item-header">
                    <span className="activity-item-category">{activity.category}</span>
                    <span className="activity-item-status">{activity.status === 'ongoing' ? '进行中' : '已结束'}</span>
                  </div>
                  <h4 className="activity-item-title">{activity.title}</h4>
                  <p className="activity-item-content">{activity.content}</p>
                  {activity.location?.city && (
                    <p className="activity-item-location">📍 {activity.location.city} {activity.location.district}</p>
                  )}
                </div>
              ))
            ) : (
              <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
                <p style={{ color: '#999' }}>暂无活动</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'reviews' && (
          <div className="reviews-section">
            {userReviews.length > 0 ? (
              userReviews.map(review => (
                <div key={review._id} className="card review-item-card" style={{ marginBottom: '0.75rem' }}>
                  <div className="review-item-header">
                    <span className="review-rating">
                      {'★'.repeat(review.rating)}
                      {'☆'.repeat(5 - review.rating)}
                    </span>
                    <span className="review-date">
                      {review.created_at ? new Date(review.created_at).toLocaleDateString() : ''}
                    </span>
                  </div>
                  {review.comment && <p className="review-comment">{review.comment}</p>}
                </div>
              ))
            ) : (
              <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
                <p style={{ color: '#999' }}>暂无评价</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default UserProfilePage
