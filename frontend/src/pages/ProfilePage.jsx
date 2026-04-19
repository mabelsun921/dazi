import React, { useState, useEffect } from 'react'
import API from '../utils/api'
import './ProfilePage.css'

const ProfilePage = ({ isLoggedIn, currentUser, onProfileComplete }) => {
  const [profile, setProfile] = useState({
    name: '',
    gender: '',
    age: 0,
    mbti: '',
    occupation: '',
    hobbies: [],
    location: { city: '', district: '' },
    personality: '',
    privacy_settings: { age_visible: true, occupation_visible: true },
    reputation: 5.0,
    ai_tags: []
  })
  const [ongoingActivities, setOngoingActivities] = useState([])
  const [appliedActivities, setAppliedActivities] = useState([])
  const [pastActivities, setPastActivities] = useState([])
  const [hostApplications, setHostApplications] = useState([])
  const [reviews, setReviews] = useState([])
  const [reviewsGiven, setReviewsGiven] = useState([])
  const [stats, setStats] = useState({})
  const [showEditForm, setShowEditForm] = useState(false)
  const [activeTab, setActiveTab] = useState('activities')
  const [activeActivityTab, setActiveActivityTab] = useState('hosting')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedActivity, setSelectedActivity] = useState(null)
  const [editingActivity, setEditingActivity] = useState(null)
  const [showActivityDetail, setShowActivityDetail] = useState(false)

  useEffect(() => {
    fetchUserData()
  }, [isLoggedIn, currentUser])

  const fetchUserData = async () => {
    if (!isLoggedIn || !currentUser) return
    
    setIsLoading(true)
    try {
      const userId = currentUser.user_id || currentUser._id
      
      const detailsResponse = await fetch(API.user.details(userId))
      if (detailsResponse.ok) {
        const detailsData = await detailsResponse.json()
        const profileData = {
          ...detailsData.profile,
          hobbies: detailsData.profile.hobbies || [],
          ai_tags: detailsData.profile.ai_tags || []
        }
        setProfile(profileData)
        setOngoingActivities(detailsData.ongoing_activities || [])
        setPastActivities(detailsData.past_activities || [])
        setReviews(detailsData.reviews || [])
      }

      const appliedResponse = await fetch(API.user.appliedActivities(userId))
      if (appliedResponse.ok) {
        const appliedData = await appliedResponse.json()
        setAppliedActivities(appliedData || [])
      }

      const hostAppsResponse = await fetch(API.user.hostApplications(userId))
      if (hostAppsResponse.ok) {
        const hostAppsData = await hostAppsResponse.json()
        setHostApplications(hostAppsData || [])
      }

      const reviewsGivenResponse = await fetch(API.user.reviewsGiven(userId))
      if (reviewsGivenResponse.ok) {
        const reviewsGivenData = await reviewsGivenResponse.json()
        setReviewsGiven(reviewsGivenData || [])
      }

      const statsResponse = await fetch(API.user.stats(userId))
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        setStats(statsData || {})
      }
    } catch (error) {
      console.error('Error fetching user data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setProfile(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleLocationChange = (field, value) => {
    setProfile(prev => ({
      ...prev,
      location: {
        ...prev.location,
        [field]: value
      }
    }))
  }

  const handlePrivacyChange = (field, checked) => {
    setProfile(prev => ({
      ...prev,
      privacy_settings: {
        ...prev.privacy_settings,
        [field]: checked
      }
    }))
  }

  const handleProfileSubmit = async (e) => {
    e.preventDefault()
    try {
      const userId = currentUser.user_id || currentUser._id
      const response = await fetch(API.profile.update(userId), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(profile)
      })
      
      if (response.ok) {
        alert('资料更新成功！')
        fetchUserData()
        if (onProfileComplete) {
          onProfileComplete()
        }
      } else {
        const error = await response.json()
        alert(error.error || '资料更新失败')
      }
    } catch (error) {
      console.error('Error updating profile:', error)
      alert('资料更新失败，请稍后重试')
    }
    setShowEditForm(false)
  }

  const handleActivityClick = (activity) => {
    setSelectedActivity(activity)
    setShowActivityDetail(true)
  }

  const handleEditActivity = (activity) => {
    setEditingActivity({...activity})
  }

  const handleUpdateActivity = async () => {
    if (!editingActivity) return
    
    try {
      const userId = currentUser.user_id || currentUser._id
      const response = await fetch(API.activities.update(editingActivity._id), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...editingActivity,
          user_id: userId
        })
      })
      
      if (response.ok) {
        alert('活动更新成功！')
        setEditingActivity(null)
        fetchUserData()
      } else {
        const error = await response.json()
        alert(error.error || '更新失败')
      }
    } catch (error) {
      console.error('Error updating activity:', error)
      alert('更新失败，请稍后重试')
    }
  }

  const handleDeleteActivity = async (activityId) => {
    if (!confirm('确定要撤销/删除这个活动吗？')) return
    
    try {
      const userId = currentUser.user_id || currentUser._id
      const response = await fetch(API.activities.delete(activityId, userId), {
        method: 'DELETE'
      })
      
      if (response.ok) {
        alert('活动已撤销！')
        fetchUserData()
      } else {
        const error = await response.json()
        alert(error.error || '撤销失败')
      }
    } catch (error) {
      console.error('Error deleting activity:', error)
      alert('撤销失败，请稍后重试')
    }
  }

  const handleApproveApplication = async (applicationId, approved) => {
    try {
      const response = await fetch(API.applications.update(applicationId), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          status: approved ? 'approved' : 'rejected'
        })
      })
      
      if (response.ok) {
        alert(approved ? '已批准申请！' : '已拒绝申请！')
        fetchUserData()
      } else {
        const error = await response.json()
        alert(error.error || '操作失败')
      }
    } catch (error) {
      console.error('Error updating application:', error)
      alert('操作失败，请稍后重试')
    }
  }

  const getActivityApplications = (activityId) => {
    return hostApplications.filter(app => app.activity_id === activityId)
  }

  const pendingApplicationsCount = hostApplications.filter(app => app.status === 'pending').length

  const renderActivityList = () => {
    let activities = []
    switch (activeActivityTab) {
      case 'hosting':
        activities = ongoingActivities
        break
      case 'applied':
        activities = appliedActivities
        break
      case 'past':
        activities = pastActivities
        break
      default:
        activities = ongoingActivities
    }

    if (activities.length === 0) {
      return (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#999' }}>
          暂无活动
        </div>
      )
    }

    return (
      <div className="activity-list">
        {activities.map(activity => {
          const apps = getActivityApplications(activity._id)
          const pendingCount = apps.filter(a => a.status === 'pending').length
          
          return (
            <div 
              key={activity._id} 
              className="activity-item"
              onClick={() => handleActivityClick(activity)}
            >
              <div className="activity-item-header">
                <div className="activity-item-category">{activity.category}</div>
                {pendingCount > 0 && (
                  <div className="activity-item-badge">{pendingCount}个待审核</div>
                )}
              </div>
              <h4 className="activity-item-title">{activity.title}</h4>
              <div className="activity-item-info">
                <span>📍 {activity.location?.city || '未设置'}</span>
                <span>👥 {activity.participants?.length || 0}人参与</span>
                <span>💰 {activity.budget || 0}元</span>
              </div>
              {activity.time && (
                <div className="activity-item-time">
                  🕐 {new Date(activity.time).toLocaleString('zh-CN', { 
                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    )
  }

  const renderActivityDetail = () => {
    if (!selectedActivity) return null
    
    const apps = getActivityApplications(selectedActivity._id)
    
    return (
      <div className="activity-detail-modal">
        <div className="activity-detail-content">
          <div className="activity-detail-header">
            <h3>活动管理</h3>
            <button className="close-btn" onClick={() => setShowActivityDetail(false)}>✕</button>
          </div>
          
          <div className="activity-detail-body">
            <div className="activity-info-section">
              <h4>基本信息</h4>
              <div className="info-grid">
                <div className="info-item">
                  <label>标题</label>
                  <p>{selectedActivity.title}</p>
                </div>
                <div className="info-item">
                  <label>分类</label>
                  <p>{selectedActivity.category}</p>
                </div>
                <div className="info-item">
                  <label>地点</label>
                  <p>{selectedActivity.location?.city} {selectedActivity.location?.district}</p>
                </div>
                <div className="info-item">
                  <label>预算</label>
                  <p>{selectedActivity.budget}元</p>
                </div>
                <div className="info-item">
                  <label>时间</label>
                  <p>{selectedActivity.time ? new Date(selectedActivity.time).toLocaleString('zh-CN') : '未设置'}</p>
                </div>
                <div className="info-item">
                  <label>参与人数</label>
                  <p>{selectedActivity.participants?.length || 0}人</p>
                </div>
              </div>
              <div className="info-item">
                <label>内容</label>
                <p>{selectedActivity.content}</p>
              </div>
              <div className="info-item">
                <label>要求</label>
                <p>{selectedActivity.requirements || '无'}</p>
              </div>
            </div>

            <div className="activity-actions-section">
              <h4>管理操作</h4>
              <div className="action-buttons">
                <button 
                  className="btn-edit"
                  onClick={() => handleEditActivity(selectedActivity)}
                >
                  ✏️ 编辑活动
                </button>
                <button 
                  className="btn-delete"
                  onClick={() => handleDeleteActivity(selectedActivity._id)}
                >
                  🗑️ 撤销活动
                </button>
              </div>
            </div>

            <div className="activity-applications-section">
              <h4>报名申请 ({apps.length})</h4>
              {apps.length === 0 ? (
                <p style={{ color: '#999' }}>暂无申请</p>
              ) : (
                <div className="application-list">
                  {apps.map(app => (
                    <div key={app._id} className="application-item">
                      <div className="applicant-info">
                        <span className="applicant-name">{app.applicant_name}</span>
                        <span className={`application-status status-${app.status}`}>
                          {app.status === 'pending' ? '待审核' : 
                           app.status === 'approved' ? '已通过' : '已拒绝'}
                        </span>
                      </div>
                      {app.status === 'pending' && (
                        <div className="application-actions">
                          <button 
                            className="btn-approve"
                            onClick={() => handleApproveApplication(app._id, true)}
                          >
                            ✅ 通过
                          </button>
                          <button 
                            className="btn-reject"
                            onClick={() => handleApproveApplication(app._id, false)}
                          >
                            ❌ 拒绝
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  const renderEditActivityForm = () => {
    if (!editingActivity) return null
    
    const handleChange = (field, value) => {
      setEditingActivity(prev => ({
        ...prev,
        [field]: value
      }))
    }
    
    const handleLocationChange = (field, value) => {
      setEditingActivity(prev => ({
        ...prev,
        location: {
          ...prev.location,
          [field]: value
        }
      }))
    }
    
    return (
      <div className="edit-activity-modal">
        <div className="edit-activity-content">
          <div className="edit-activity-header">
            <h3>编辑活动</h3>
            <button className="close-btn" onClick={() => setEditingActivity(null)}>✕</button>
          </div>
          
          <div className="edit-activity-body">
            <div className="form-group">
              <label>标题</label>
              <input 
                type="text" 
                value={editingActivity.title || ''}
                onChange={(e) => handleChange('title', e.target.value)}
              />
            </div>
            
            <div className="form-group">
              <label>内容</label>
              <textarea 
                value={editingActivity.content || ''}
                onChange={(e) => handleChange('content', e.target.value)}
              />
            </div>
            
            <div className="form-group">
              <label>分类</label>
              <select 
                value={editingActivity.category || ''}
                onChange={(e) => handleChange('category', e.target.value)}
              >
                <option value="">选择分类</option>
                <option value="运动">运动</option>
                <option value="学习">学习</option>
                <option value="娱乐">娱乐</option>
                <option value="社交">社交</option>
                <option value="美食">美食</option>
                <option value="旅行">旅行</option>
                <option value="艺术">艺术</option>
              </select>
            </div>
            
            <div className="form-row">
              <div className="form-group">
                <label>城市</label>
                <input 
                  type="text" 
                  value={editingActivity.location?.city || ''}
                  onChange={(e) => handleLocationChange('city', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>区</label>
                <input 
                  type="text" 
                  value={editingActivity.location?.district || ''}
                  onChange={(e) => handleLocationChange('district', e.target.value)}
                />
              </div>
            </div>
            
            <div className="form-group">
              <label>预算</label>
              <input 
                type="number" 
                value={editingActivity.budget || 0}
                onChange={(e) => handleChange('budget', parseInt(e.target.value))}
              />
            </div>
            
            <div className="form-group">
              <label>时间</label>
              <input 
                type="datetime-local" 
                value={editingActivity.time ? editingActivity.time.slice(0, 16) : ''}
                onChange={(e) => handleChange('time', e.target.value)}
              />
            </div>
            
            <div className="form-group">
              <label>要求</label>
              <textarea 
                value={editingActivity.requirements || ''}
                onChange={(e) => handleChange('requirements', e.target.value)}
              />
            </div>
            
            <div className="form-actions">
              <button className="btn-cancel" onClick={() => setEditingActivity(null)}>取消</button>
              <button className="btn-save" onClick={handleUpdateActivity}>保存</button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="profile-page">
      {!isLoggedIn ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <h2>请先登录以查看个人信息</h2>
        </div>
      ) : isLoading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <p>加载中...</p>
        </div>
      ) : (
        <>
          <div className="profile-header-section">
            <div className="profile-avatar-section">
              <div className="profile-avatar">
                {profile.name ? profile.name[0].toUpperCase() : '?'}
              </div>
              <button 
                className="edit-profile-btn"
                onClick={() => setShowEditForm(true)}
              >
                编辑资料
              </button>
            </div>
            
            <div className="profile-basic-info">
              <h2 className="profile-name">{profile.name}</h2>
              <div className="profile-tags">
                {profile.ai_tags?.map((tag, idx) => (
                  <span key={idx} className="tag">{tag}</span>
                ))}
              </div>
              <div className="profile-meta">
                <span>📍 {profile.location?.city || '未设置'}</span>
                <span>⭐ {profile.reputation?.toFixed(1) || '5.0'}</span>
              </div>
            </div>
          </div>

          <div className="profile-stats-bar">
            <div className="stat-item">
              <span className="stat-value">{stats.activities_created || 0}</span>
              <span className="stat-label">发起</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{stats.activities_joined || 0}</span>
              <span className="stat-label">参加</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{stats.average_rating?.toFixed(1) || '0.0'}</span>
              <span className="stat-label">评分</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{pendingApplicationsCount}</span>
              <span className="stat-label">待审核</span>
            </div>
          </div>

          <div className="profile-tabs">
            <div 
              className={`tab ${activeTab === 'activities' ? 'active' : ''}`}
              onClick={() => setActiveTab('activities')}
            >
              我的活动
            </div>
            <div 
              className={`tab ${activeTab === 'reviews' ? 'active' : ''}`}
              onClick={() => setActiveTab('reviews')}
            >
              评价
            </div>
          </div>

          {activeTab === 'activities' && (
            <div className="activity-tab-section">
              <div className="activity-sub-tabs">
                <div 
                  className={`sub-tab ${activeActivityTab === 'hosting' ? 'active' : ''}`}
                  onClick={() => setActiveActivityTab('hosting')}
                >
                  我发起的 ({ongoingActivities.length})
                </div>
                <div 
                  className={`sub-tab ${activeActivityTab === 'applied' ? 'active' : ''}`}
                  onClick={() => setActiveActivityTab('applied')}
                >
                  我参与的 ({appliedActivities.length})
                </div>
                <div 
                  className={`sub-tab ${activeActivityTab === 'past' ? 'active' : ''}`}
                  onClick={() => setActiveActivityTab('past')}
                >
                  已结束 ({pastActivities.length})
                </div>
              </div>
              
              {renderActivityList()}
            </div>
          )}

          {activeTab === 'reviews' && (
            <div className="reviews-section">
              <h3>收到的评价</h3>
              {reviews.length === 0 ? (
                <p style={{ color: '#999', textAlign: 'center', padding: '2rem' }}>暂无评价</p>
              ) : (
                <div className="review-list">
                  {reviews.map(review => (
                    <div key={review._id} className="review-item">
                      <div className="review-rating">
                        {'⭐'.repeat(review.rating)}
                      </div>
                      <div className="review-comment">{review.comment}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {showActivityDetail && renderActivityDetail()}
          {editingActivity && renderEditActivityForm()}

          {showEditForm && (
            <div className="edit-modal">
              <div className="edit-modal-content">
                <div className="edit-modal-header">
                  <h3>编辑资料</h3>
                  <button onClick={() => setShowEditForm(false)}>✕</button>
                </div>
                <form onSubmit={handleProfileSubmit}>
                  <div className="form-group">
                    <label>昵称</label>
                    <input type="text" name="name" value={profile.name || ''} onChange={handleInputChange} />
                  </div>
                  <div className="form-group">
                    <label>性别</label>
                    <select name="gender" value={profile.gender || ''} onChange={handleInputChange}>
                      <option value="">选择性别</option>
                      <option value="男">男</option>
                      <option value="女">女</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>年龄</label>
                    <input type="number" name="age" value={profile.age || 0} onChange={handleInputChange} />
                  </div>
                  <div className="form-group">
                    <label>职业</label>
                    <input type="text" name="occupation" value={profile.occupation || ''} onChange={handleInputChange} />
                  </div>
                  <div className="form-group">
                    <label>MBTI</label>
                    <input type="text" name="mbti" value={profile.mbti || ''} onChange={handleInputChange} />
                  </div>
                  <div className="form-group">
                    <label>城市</label>
                    <input type="text" value={profile.location?.city || ''} onChange={(e) => handleLocationChange('city', e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label>个人描述</label>
                    <textarea name="personality" value={profile.personality || ''} onChange={handleInputChange} />
                  </div>
                  <div className="form-actions">
                    <button type="button" onClick={() => setShowEditForm(false)}>取消</button>
                    <button type="submit">保存</button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default ProfilePage
