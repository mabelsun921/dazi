import React, { useState, useEffect } from 'react'
import ActivityAgent from '../components/ActivityAgent'
import API from '../utils/api'
import './SquarePage.css'

const SquarePage = ({ isLoggedIn, currentUser, onViewUserProfile, onViewActivity, currentPage }) => {
  const [activities, setActivities] = useState([])
  const [originalActivities, setOriginalActivities] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [showAgent, setShowAgent] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const [selectedActivity, setSelectedActivity] = useState(null)
  const [expandedActivityId, setExpandedActivityId] = useState(null)
  const [newActivity, setNewActivity] = useState({
    title: '',
    content: '',
    category: '',
    time: '',
    location: { city: '', district: '' },
    budget: 0,
    people_range: { min: 1, max: 10 },
    requirements: '',
    need_confirmation: false,
    deposit: 0,
    tags: ''
  })
  const [activityDescription, setActivityDescription] = useState('')
  const [showAiHint, setShowAiHint] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)
  const [searchHistory, setSearchHistory] = useState(() => {
    // 从localStorage加载搜索历史
    const savedHistory = localStorage.getItem('searchHistory')
    return savedHistory ? JSON.parse(savedHistory) : []
  })
  const [showSearchResults, setShowSearchResults] = useState(false) // 控制是否显示搜索结果页

  // Fetch activities from backend API
  // 页面显示时获取活动
  useEffect(() => {
    fetchActivities()
  }, [currentPage])

  // 监听页面显示（从其他页面切回时刷新）
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        fetchActivities()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [])

  const fetchActivities = async () => {
    try {
      const response = await fetch(API.activities.list)
      if (response.ok) {
        const data = await response.json()
        
        // 获取当前用户的完整资料（用于评分API）
        let currentUserProfile = null;
        if (isLoggedIn && currentUser) {
          try {
            const profileResponse = await fetch(API.profile.get(currentUser.user_id || currentUser._id));
            if (profileResponse.ok) {
              currentUserProfile = await profileResponse.json();
            }
          } catch (error) {
            console.error('Error fetching current user profile:', error);
          }
        }
        
        // 为每个活动获取真实的用户信息和匹配度
        const activitiesWithUserInfo = await Promise.all(data.map(async (activity) => {
          let user_name = '未知用户';
          let user_rating = 0;
          let match_score = 0;
          let match_reason = '';
          
          // 尝试获取用户资料
          try {
            const userResponse = await fetch(API.profile.get(activity.user_id));
            if (userResponse.ok) {
              const userData = await userResponse.json();
              user_name = userData.name || userData.user_name || '未知用户';
              user_rating = userData.reputation || 0;
            }
          } catch (error) {
            console.error(`Error fetching user ${activity.user_id}:`, error);
          }
          
          // 为当前用户显示"我"
          if (activity.user_id === (currentUser?.user_id || currentUser?._id)) {
            user_name = currentUser?.name || '我';
          }
          
          // 如果有当前用户资料，获取真实的匹配度评分
          if (currentUserProfile) {
            try {
              const scoreResponse = await fetch(API.activities.score, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  profile: currentUserProfile,
                  activity: activity
                })
              });
              if (scoreResponse.ok) {
                const scoreData = await scoreResponse.json();
                match_score = scoreData.score || 0;
                match_reason = scoreData.reason || '';
              }
            } catch (error) {
              console.error(`Error fetching match score for activity ${activity._id}:`, error);
            }
          }
          
          return {
            ...activity,
            user_name,
            user_rating,
            match_score,
            match_reason
          };
        }));
        
        setActivities(activitiesWithUserInfo)
        setOriginalActivities(activitiesWithUserInfo) // 保存原始活动列表
      } else {
        console.error('Failed to fetch activities')
      }
    } catch (error) {
      console.error('Error fetching activities:', error)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setNewActivity(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleNumberChange = (name, value) => {
    setNewActivity(prev => ({
      ...prev,
      [name]: Number(value)
    }))
  }

  const handlePeopleRangeChange = (field, value) => {
    setNewActivity(prev => ({
      ...prev,
      people_range: {
        ...prev.people_range,
        [field]: Number(value)
      }
    }))
  }

  const handleLocationChange = (field, value) => {
    setNewActivity(prev => ({
      ...prev,
      location: {
        ...prev.location,
        [field]: value
      }
    }))
  }

  const handleCheckboxChange = (name, checked) => {
    setNewActivity(prev => ({
      ...prev,
      [name]: checked
    }))
  }

  const handleAiHint = async () => {
    if (!activityDescription.trim()) {
      alert('请输入活动描述');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(API.activities.aiHint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ activity_description: activityDescription })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Try to extract budget and people_range from description
        let budget = 0;
        let peopleMin = 1;
        let peopleMax = 10;
        let locationCity = '';
        let locationDistrict = '';
        
        // Extract budget from description
        const budgetMatch = activityDescription.match(/(\d+)\s*[元块]/);
        if (budgetMatch) {
          budget = parseInt(budgetMatch[1]);
        }
        
        // Extract people count
        const peopleMatch = activityDescription.match(/(\d+)\s*人/);
        if (peopleMatch) {
          const count = parseInt(peopleMatch[1]);
          peopleMin = count;
          peopleMax = count + 2;
        }
        
        // Extract location
        const cities = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '南京', '重庆'];
        for (const city of cities) {
          if (activityDescription.includes(city)) {
            locationCity = city;
            break;
          }
        }
        
        setNewActivity(prev => ({
          ...prev,
          title: data.title || '',
          content: data.description || '',
          category: data.category || '',
          tags: Array.isArray(data.tags) ? data.tags.join(', ') : (data.tags || ''),
          requirements: data.requirements || '',
          budget: budget || prev.budget,
          people_range: { min: peopleMin, max: peopleMax },
          location: { 
            city: locationCity || prev.location.city, 
            district: locationDistrict || prev.location.district 
          }
        }));
        setShowAiHint(false);
      } else {
        alert('AI提示生成失败，请重试');
      }
    } catch (error) {
      console.error('Error fetching AI hint:', error);
      alert('网络错误，请检查后端服务是否运行');
    } finally {
      setIsLoading(false);
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    try {
      // 转换tags为数组
      const tagsArray = newActivity.tags.split(',').map(tag => tag.trim()).filter(tag => tag);
      
      const activityData = {
        ...newActivity,
        tags: tagsArray,
        user_id: currentUser?.user_id || currentUser?._id || '661d3f2b9e9b4c001f8b4567'
      };
      
      // 调用后端API
      const response = await fetch(API.activities.create, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(activityData)
      });
      
      if (response.ok) {
        const data = await response.json();
        // 添加新活动到列表
        const newActivityWithInfo = {
          ...activityData,
          _id: data.activity_id,
          user_name: '我',
          user_rating: 4.6,
          status: 'ongoing',
          participants: ['661d3f2b9e9b4c001f8b4567'],
          created_at: new Date().toISOString()
        };
        setActivities(prev => [newActivityWithInfo, ...prev]);
        // 重置表单
        setNewActivity({
          title: '',
          content: '',
          category: '',
          time: '',
          location: { city: '', district: '' },
          budget: 0,
          people_range: { min: 1, max: 10 },
          requirements: '',
          need_confirmation: false,
          deposit: 0,
          tags: ''
        });
        setActivityDescription('');
        setShowForm(false);
      } else {
        alert('活动发布失败，请重试');
      }
    } catch (error) {
      console.error('Error submitting activity:', error);
      alert('活动发布失败，请重试');
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      alert('请输入搜索关键词');
      return;
    }

    try {
      // 保存搜索历史
      const newHistory = [searchQuery, ...searchHistory.filter(item => item !== searchQuery)].slice(0, 10); // 只保存最近10条
      setSearchHistory(newHistory);
      localStorage.setItem('searchHistory', JSON.stringify(newHistory));

      const response = await fetch(API.activities.search, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: searchQuery })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // 获取当前用户的完整资料（用于评分API）
        let currentUserProfile = null;
        if (isLoggedIn && currentUser) {
          try {
            const profileResponse = await fetch(API.profile.get(currentUser.user_id || currentUser._id));
            if (profileResponse.ok) {
              currentUserProfile = await profileResponse.json();
            }
          } catch (error) {
            console.error('Error fetching current user profile:', error);
          }
        }
        
        // Add user info to search results
        const searchResultsWithUserInfo = await Promise.all(data.map(async (activity) => {
          let user_name = '未知用户';
          let user_rating = 0;
          let match_score = 0;
          
          // 尝试获取用户资料
          try {
            const userResponse = await fetch(API.profile.get(activity.user_id));
            if (userResponse.ok) {
              const userData = await userResponse.json();
              user_name = userData.name || userData.user_name || '未知用户';
              user_rating = userData.reputation || 0;
            }
          } catch (error) {
            console.error(`Error fetching user ${activity.user_id}:`, error);
          }
          
          // 为当前用户显示"我"
          if (activity.user_id === (currentUser?.user_id || currentUser?._id)) {
            user_name = currentUser?.name || '我';
          }
          
          // 如果有当前用户资料，获取真实的匹配度评分
          if (currentUserProfile) {
            try {
              const scoreResponse = await fetch(API.activities.score, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  profile: currentUserProfile,
                  activity: activity
                })
              });
              if (scoreResponse.ok) {
                const scoreData = await scoreResponse.json();
                match_score = scoreData.score || 0;
              }
            } catch (error) {
              console.error(`Error fetching match score:`, error);
            }
          }
          
          return {
            ...activity,
            user_name,
            user_rating,
            match_score
          };
        }));
        setActivities(searchResultsWithUserInfo);
        setShowSearchResults(true); // 显示搜索结果页
        setShowSearch(false); // 隐藏搜索栏，直接显示结果
      } else {
        alert('搜索失败，请重试');
      }
    } catch (error) {
      console.error('Error searching activities:', error);
      alert('网络错误，请检查后端服务是否运行');
    }
  }

  // 从搜索历史中选择
  const handleSelectHistory = (query) => {
    if (!query || !query.trim()) {
      return;
    }
    setSearchQuery(query)
  }

  // 清空搜索历史
  const clearSearchHistory = () => {
    setSearchHistory([]);
    localStorage.removeItem('searchHistory');
  }

  // 返回活动主页
  const handleBackToHome = () => {
    setActivities(originalActivities);
    setShowSearchResults(false);
    setShowSearch(false);
    setSearchQuery('');
  }

  const handleApplyActivity = async (activityId) => {
    if (!isLoggedIn || !currentUser) {
      alert('请先登录后再申请参加活动');
      return;
    }
    
    try {
      const userId = currentUser.user_id || currentUser._id;
      console.log('Applying with user_id:', userId);
      
      const response = await fetch(API.activities.apply(activityId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ user_id: userId })
      });
      
      const data = await response.json();
      console.log('Apply response:', data);
      
      if (response.ok) {
        alert('申请已提交，等待发起者确认');
      } else {
        alert(data.error || '申请失败，请重试');
      }
    } catch (error) {
      console.error('Error applying for activity:', error);
      alert('网络错误，请检查后端服务是否运行');
    }
  }

  return (
    <div className="square-page">
      <h2 className="section-title">活动广场</h2>
      <p className="section-subtitle">AI 实时评估契合度 · 右侧环形图为你的匹配分</p>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={() => setShowSearch(!showSearch)}>
            {showSearch ? '取消搜索' : '搜索活动'}
          </button>
          <button 
            className="btn" 
            style={{ 
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white'
            }}
            onClick={() => setShowAgent(true)}
          >
            🤖 活动助手
          </button>
        </div>
        <button 
          className="btn btn-primary" 
          onClick={() => {
            if (!isLoggedIn) {
              alert('请先登录后再发布活动');
            } else {
              setShowForm(!showForm);
            }
          }}
        >
          {showForm ? '取消' : '发布活动'}
        </button>
      </div>

      {showSearch && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'white', zIndex: 1000, padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
            <button 
              style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', marginRight: '10px' }}
              onClick={() => setShowSearch(false)}
            >
              ×
            </button>
            <div style={{ flex: 1, display: 'flex', gap: '10px' }}>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索活动"
                style={{ flex: 1, padding: '10px', fontSize: '16px', border: '1px solid #ddd', borderRadius: '20px' }}
                autoFocus
              />
              <button className="btn btn-primary" onClick={handleSearch}>
                搜索
              </button>
            </div>
          </div>
          
          {searchHistory.length > 0 && (
            <div style={{ marginTop: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h4>搜索历史</h4>
                <button 
                  style={{ background: 'none', border: 'none', color: '#999', cursor: 'pointer' }}
                  onClick={clearSearchHistory}
                >
                  清空
                </button>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {searchHistory.map((item, index) => (
                  <div
                    key={index}
                    style={{
                      padding: '8px 12px',
                      backgroundColor: '#f5f5f5',
                      borderRadius: '16px',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                    onClick={() => handleSelectHistory(item)}
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {showSearchResults && (
        <div style={{ marginBottom: '1rem' }}>
          <button className="btn btn-secondary" onClick={handleBackToHome}>
            ← 返回活动主页
          </button>
          <h3 style={{ marginTop: '1rem' }}>搜索结果: {searchQuery}</h3>
        </div>
      )}

      {showForm && (
        <div className="card">
          <h3>发布新活动</h3>
          
          {!showAiHint ? (
            <div style={{ marginBottom: '1rem' }}>
              <button 
                className="btn btn-secondary" 
                onClick={() => setShowAiHint(true)}
                style={{ marginBottom: '1rem' }}
              >
                使用AI提示
              </button>
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label htmlFor="title">标题</label>
                  <input
                    type="text"
                    id="title"
                    name="title"
                    value={newActivity.title}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="content">内容</label>
                  <textarea
                    id="content"
                    name="content"
                    value={newActivity.content}
                    onChange={handleInputChange}
                    required
                  ></textarea>
                </div>
                <div className="form-group">
                  <label htmlFor="requirements">希望对方能：</label>
                  <input
                    type="text"
                    id="requirements"
                    name="requirements"
                    value={newActivity.requirements}
                    onChange={handleInputChange}
                    placeholder="例如：有经验、带相机、会开车等"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="tags">活动标签</label>
                  <input
                    type="text"
                    id="tags"
                    name="tags"
                    value={newActivity.tags}
                    onChange={handleInputChange}
                    placeholder="请用逗号分隔，例如：爬山,户外,摄影"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="category">分类</label>
                  <select
                    id="category"
                    name="category"
                    value={newActivity.category}
                    onChange={handleInputChange}
                    required
                  >
                    <option value="">请选择</option>
                    <option value="音乐演出">音乐演出</option>
                    <option value="户外运动">户外运动</option>
                    <option value="娱乐">娱乐</option>
                    <option value="学习">学习</option>
                    <option value="美食">美食</option>
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="time">时间</label>
                  <input
                    type="datetime-local"
                    id="time"
                    name="time"
                    value={newActivity.time}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="form-group">
                  <label>地点</label>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <input
                      type="text"
                      placeholder="城市"
                      value={newActivity.location.city}
                      onChange={(e) => handleLocationChange('city', e.target.value)}
                      required
                      style={{ flex: 1 }}
                    />
                    <input
                      type="text"
                      placeholder="区"
                      value={newActivity.location.district}
                      onChange={(e) => handleLocationChange('district', e.target.value)}
                      style={{ flex: 1 }}
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label htmlFor="budget">预算</label>
                  <input
                    type="number"
                    id="budget"
                    name="budget"
                    value={newActivity.budget}
                    onChange={(e) => handleNumberChange('budget', e.target.value)}
                    min="0"
                  />
                </div>
                <div className="form-group">
                  <label>人数范围</label>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <input
                      type="number"
                      placeholder="最少"
                      value={newActivity.people_range.min}
                      onChange={(e) => handlePeopleRangeChange('min', e.target.value)}
                      min="1"
                      style={{ flex: 1 }}
                    />
                    <input
                      type="number"
                      placeholder="最多"
                      value={newActivity.people_range.max}
                      onChange={(e) => handlePeopleRangeChange('max', e.target.value)}
                      min="1"
                      style={{ flex: 1 }}
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label htmlFor="deposit">活动押金（虚拟币）</label>
                  <input
                    type="number"
                    id="deposit"
                    name="deposit"
                    value={newActivity.deposit}
                    onChange={(e) => handleNumberChange('deposit', e.target.value)}
                    min="0"
                  />
                </div>
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={newActivity.need_confirmation}
                      onChange={(e) => handleCheckboxChange('need_confirmation', e.target.checked)}
                    />
                    需要发起者确认才能参与
                  </label>
                </div>
                <button type="submit" className="btn btn-primary">发布</button>
              </form>
            </div>
          ) : (
            <div>
              <h4>AI提示</h4>
              <p>请描述你想要组织的活动，AI将为你生成相关信息</p>
              <div className="form-group">
                <textarea
                  value={activityDescription}
                  onChange={(e) => setActivityDescription(e.target.value)}
                  placeholder="例如：周末想组织一次爬山活动，希望找有经验的伙伴一起"
                  style={{ width: '100%', height: '100px', marginBottom: '1rem' }}
                ></textarea>
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button 
                  className="btn btn-secondary" 
                  onClick={() => setShowAiHint(false)}
                >
                  取消
                </button>
                <button 
                  className="btn btn-primary" 
                  onClick={handleAiHint}
                  disabled={isLoading}
                >
                  {isLoading ? '生成中...' : '生成提示'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}



      <div className="activities-list">
        {(showForm ? [] : activities).map(activity => {
          // 使用后端返回的真实匹配度，如果没有则显示为0
          const matchScore = (activity.match_score || 0) / 100;
          const matchClass = matchScore > 0.8 ? 'very-high' : matchScore > 0.6 ? 'high' : matchScore > 0.4 ? 'medium' : 'low';
          
          const isExpanded = expandedActivityId === activity._id;
           
           return (
             <div 
               key={activity._id} 
               className="card activity-card"
               onClick={() => {
                 if (onViewActivity) {
                   onViewActivity(activity);
                 } else if (!isExpanded) {
                   setExpandedActivityId(activity._id);
                   setSelectedActivity(activity);
                 }
               }}
             >
               <div className="activity-header">
                <div className="user-info">
                  <div 
                    className="user-avatar" 
                    onClick={(e) => {
                      e.stopPropagation();
                      // 跳转到用户主页
                      if (onViewUserProfile && activity.user_id) {
                        onViewUserProfile(activity.user_id);
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    {activity.user_name.charAt(0)}
                  </div>
                  <div className="user-details">
                    <h4>{activity.user_name}</h4>
                    <div className="user-rating">
                      {activity.user_rating > 0 ? (
                        <>
                          <span className="rating-stars">{'★'.repeat(Math.floor(activity.user_rating))}</span>
                          <span>{activity.user_rating.toFixed(1)}</span>
                        </>
                      ) : (
                        <span>暂无评分</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className={`ai-match ${matchClass}`}>
                  {Math.floor(matchScore * 100)}%
                </div>
              </div>
              
              <div className="activity-category">{activity.category}</div>
              <div className="activity-content-wrapper">
                <h3 className="activity-title">{activity.title}</h3>
                <p className="activity-content">{activity.content}</p>
                
                {activity.tags && activity.tags.length > 0 && (
                  <div className="activity-tags">
                    {activity.tags.slice(0, 3).map((tag, index) => (
                      <span key={index} className="activity-tag">{tag}</span>
                    ))}
                    {activity.tags.length > 3 && <span className="activity-tag">+{activity.tags.length - 3}</span>}
                  </div>
                )}
              </div>
              
              <div className="activity-footer">
                <div className="activity-meta">
                  <div className="activity-time">
                    {new Date(activity.time).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </div>
                  <div className="activity-location">
                    {activity.location.district}
                  </div>
                </div>
              </div>
              
              {isExpanded && (
                <div className="activity-expanded" onClick={(e) => e.stopPropagation()}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3>活动详情</h3>
                    <button className="btn btn-secondary" onClick={() => setExpandedActivityId(null)}>
                      关闭
                    </button>
                  </div>
                  {activity.requirements && (
                    <div className="activity-requirements">
                      <strong>希望对方能：</strong> {activity.requirements}
                    </div>
                  )}
                  {activity.tags && activity.tags.length > 0 && (
                    <div className="activity-tags">
                      {activity.tags.map((tag, index) => (
                        <span key={index} className="tag">{tag}</span>
                      ))}
                    </div>
                  )}
                  <div className="activity-details">
                    <div><strong>时间：</strong>{new Date(activity.time).toLocaleString('zh-CN')}</div>
                    <div><strong>地点：</strong>{activity.location.city} {activity.location.district}</div>
                    <div><strong>预算：</strong>{activity.budget} 元</div>
                    <div><strong>人数范围：</strong>{activity.people_range.min} - {activity.people_range.max} 人</div>
                    <div><strong>活动押金：</strong>{activity.deposit} 虚拟币</div>
                    <div><strong>需要确认：</strong>{activity.need_confirmation ? '是' : '否'}</div>
                    <div><strong>当前参与人数：</strong>{activity.participants?.length || 0} 人</div>
                  </div>
                  <button 
                    className="btn btn-primary" 
                    style={{ marginTop: '1rem', width: '100%' }}
                    onClick={() => handleApplyActivity(activity._id)}
                  >
                    申请参加
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {showAgent && (
        <ActivityAgent 
          isLoggedIn={isLoggedIn}
          currentUser={currentUser}
          onClose={() => setShowAgent(false)}
          onViewActivity={(activity) => {
            setShowAgent(false)
            if (onViewActivity) {
              onViewActivity(activity)
            } else {
              setExpandedActivityId(activity._id)
              setSelectedActivity(activity)
            }
          }}
        />
      )}
    </div>
  )
}

export default SquarePage
