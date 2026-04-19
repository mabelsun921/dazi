import React, { useState, useEffect } from 'react'
import API from '../utils/api'
import './ActivityDetailPage.css'

const ActivityDetailPage = ({ activity, currentUser, isLoggedIn, onBack, onViewUserProfile, onNavigateToMessage }) => {
  const [isJoining, setIsJoining] = useState(false)
  const [joinMessage, setJoinMessage] = useState('')
  const [hostProfile, setHostProfile] = useState(null)
  const [participants, setParticipants] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (activity) {
      fetchHostProfile()
      fetchParticipants()
    }
  }, [activity])

  const fetchHostProfile = async () => {
    try {
      const response = await fetch(API.users.get(activity.user_id))
      if (response.ok) {
        const data = await response.json()
        setHostProfile(data)
      }
    } catch (error) {
      console.error('Error fetching host profile:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchParticipants = async () => {
    if (!activity.participants || activity.participants.length === 0) {
      setParticipants([])
      return
    }

    try {
      const participantPromises = activity.participants.map(async (userId) => {
        const response = await fetch(API.users.get(userId))
        if (response.ok) {
          return await response.json()
        }
        return null
      })

      const results = await Promise.all(participantPromises)
      setParticipants(results.filter(p => p !== null))
    } catch (error) {
      console.error('Error fetching participants:', error)
    }
  }

  const handleJoin = async () => {
    if (!isLoggedIn) {
      alert('请先登录')
      return
    }

    setIsJoining(true)
    try {
      const response = await fetch(API.applications.list, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          activity_id: activity._id,
          user_id: currentUser.user_id || currentUser._id,
          message: joinMessage
        })
      })

      if (response.ok) {
        alert('申请已提交，等待发起者确认')
        setJoinMessage('')
      } else {
        alert('申请失败，请稍后重试')
      }
    } catch (error) {
      console.error('Error joining activity:', error)
      alert('申请失败，请稍后重试')
    } finally {
      setIsJoining(false)
    }
  }

  const handleContactHost = () => {
    if (!isLoggedIn) {
      alert('请先登录')
      return
    }
    if (onNavigateToMessage) {
      onNavigateToMessage(activity.user_id)
    }
  }

  if (!activity) {
    return (
      <div className="activity-detail-page">
        <div className="detail-header">
          <button className="back-btn" onClick={onBack}>← 返回</button>
        </div>
        <div className="detail-empty">
          <p>活动不存在</p>
        </div>
      </div>
    )
  }

  const isHost = currentUser && (currentUser.user_id === activity.user_id || currentUser._id === activity.user_id)
  const isParticipant = currentUser && activity.participants && 
    activity.participants.includes(currentUser.user_id || currentUser._id)

  return (
    <div className="activity-detail-page">
      <div className="detail-header">
        <button className="back-btn" onClick={onBack}>← 返回</button>
      </div>

      <div className="detail-content">
        <div className="detail-category-tag">{activity.category}</div>
        
        <h1 className="detail-title">{activity.title}</h1>

        <div className="detail-meta">
          <div className="detail-meta-item">
            <span className="meta-icon">📅</span>
            <span>{new Date(activity.time).toLocaleString('zh-CN')}</span>
          </div>
          <div className="detail-meta-item">
            <span className="meta-icon">📍</span>
            <span>{activity.location.city} {activity.location.district}</span>
          </div>
          <div className="detail-meta-item">
            <span className="meta-icon">💰</span>
            <span>{activity.budget > 0 ? `¥${activity.budget}` : '免费'}</span>
          </div>
          <div className="detail-meta-item">
            <span className="meta-icon">👥</span>
            <span>{activity.participants?.length || 1} / {activity.max_participants || '不限'}</span>
          </div>
        </div>

        <div className="detail-section">
          <h3>活动详情</h3>
          <p className="detail-description">{activity.content}</p>
        </div>

        {activity.tags && activity.tags.length > 0 && (
          <div className="detail-section">
            <h3>标签</h3>
            <div className="detail-tags">
              {activity.tags.map((tag, index) => (
                <span key={index} className="detail-tag">{tag}</span>
              ))}
            </div>
          </div>
        )}

        {activity.requirements && (
          <div className="detail-section">
            <h3>活动要求</h3>
            <p className="detail-requirements">{activity.requirements}</p>
          </div>
        )}

        <div className="detail-section">
          <h3>发起人</h3>
          <div 
            className="detail-host"
            onClick={() => onViewUserProfile && onViewUserProfile(activity.user_id)}
          >
            <div className="host-avatar">
              {hostProfile?.name?.charAt(0) || '?'}
            </div>
            <div className="host-info">
              <div className="host-name">{hostProfile?.name || '加载中...'}</div>
              <div className="host-rating">
                {'★'.repeat(Math.floor(hostProfile?.reputation || 0))}
                {'☆'.repeat(5 - Math.floor(hostProfile?.reputation || 0))}
                <span>{(hostProfile?.reputation || 0).toFixed(1)}</span>
              </div>
            </div>
            <span className="host-arrow">›</span>
          </div>
        </div>

        {participants.length > 0 && (
          <div className="detail-section">
            <h3>参与者 ({participants.length})</h3>
            <div className="detail-participants">
              {participants.slice(0, 5).map((participant, index) => (
                <div 
                  key={index}
                  className="participant-item"
                  onClick={() => onViewUserProfile && onViewUserProfile(participant._id)}
                >
                  <div className="participant-avatar">
                    {participant.name?.charAt(0) || '?'}
                  </div>
                  <span className="participant-name">{participant.name}</span>
                </div>
              ))}
              {participants.length > 5 && (
                <div className="participant-more">+{participants.length - 5}人</div>
              )}
            </div>
          </div>
        )}

        {!isHost && !isParticipant && (
          <div className="detail-actions">
            <div className="join-form">
              <textarea
                placeholder="向发起者说些什么..."
                value={joinMessage}
                onChange={(e) => setJoinMessage(e.target.value)}
                className="join-message-input"
              />
              <button 
                className="join-btn"
                onClick={handleJoin}
                disabled={isJoining}
              >
                {isJoining ? '申请中...' : '申请参加'}
              </button>
            </div>
            <button className="contact-btn" onClick={handleContactHost}>
              💬 联系发起人
            </button>
          </div>
        )}

        {isParticipant && !isHost && (
          <div className="detail-actions">
            <div className="joined-notice">✓ 您已报名此活动</div>
            <button className="contact-btn" onClick={handleContactHost}>
              💬 联系发起人
            </button>
          </div>
        )}

        {isHost && (
          <div className="detail-actions">
            <div className="host-notice">✓ 您是此活动的发起人</div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ActivityDetailPage
