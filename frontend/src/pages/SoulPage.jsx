import React, { useState, useEffect, useCallback } from 'react'
import API from '../utils/api'
import './SoulPage.css'

const SoulPage = ({ isLoggedIn, currentUser, currentPage, onNavigateToMessage }) => {
  const [profiles, setProfiles] = useState([])
  const [currentProfile, setCurrentProfile] = useState(null)
  const [matchReport, setMatchReport] = useState('')
  const [matchScore, setMatchScore] = useState(0)
  const [showFullReport, setShowFullReport] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)
  const dailyLimit = 3
  const [remainingMatches, setRemainingMatches] = useState(3)
  const [currentUserProfile, setCurrentUserProfile] = useState(null)
  const [viewedProfiles, setViewedProfiles] = useState([])

  // 获取当前用户资料
  const fetchCurrentUserProfile = async () => {
    if (!currentUser) return null
    try {
      const userId = currentUser.user_id || currentUser._id
      const response = await fetch(API.profile.get(userId))
      if (response.ok) {
        const data = await response.json()
        return data
      }
    } catch (error) {
      console.error('Error fetching current user profile:', error)
    }
    return null
  }

  // Fetch profiles from backend API
  useEffect(() => {
    if (!isLoggedIn || !currentUser) {
      setProfiles([])
      setCurrentProfile(null)
      setMatchScore(0)
      setMatchReport('')
      return
    }
    
    const loadData = async () => {
      const profile = await fetchCurrentUserProfile()
      if (profile) {
        setCurrentUserProfile(profile)
        fetchProfiles(profile)
      }
    }
    loadData()
  }, [isLoggedIn, currentUser])

  // Also refresh when currentPage changes to 'soul'
  useEffect(() => {
    if (currentPage === 'soul' && isLoggedIn && currentUser) {
      const loadData = async () => {
        const profile = await fetchCurrentUserProfile()
        if (profile) {
          setCurrentUserProfile(profile)
          fetchProfiles(profile)
        }
      }
      loadData()
    }
  }, [currentPage, isLoggedIn, currentUser])

  // Refresh when page becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        const loadData = async () => {
          const profile = await fetchCurrentUserProfile()
          if (profile) {
            setCurrentUserProfile(profile)
            fetchProfiles(profile)
          }
        }
        loadData()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [])

  const fetchProfiles = async (userProfile) => {
    if (!userProfile) return
    
    const today = new Date().toDateString()
    const storedDate = localStorage.getItem('soulMatchDate')
    const storedViewed = JSON.parse(localStorage.getItem('viewedProfiles') || '[]')
    
    if (storedDate !== today) {
      localStorage.setItem('soulMatchDate', today)
      localStorage.setItem('viewedProfiles', '[]')
      setViewedProfiles([])
    } else {
      setViewedProfiles(storedViewed)
    }
    
    try {
      const response = await fetch(API.profile.getAll)
      if (response.ok) {
        const data = await response.json()
        const otherProfiles = data.filter(p => p.user_id !== userProfile.user_id)
        
        const viewed = JSON.parse(localStorage.getItem('viewedProfiles') || '[]')
        const unviewedProfiles = otherProfiles.filter(p => !viewed.includes(p.user_id))
        
        const profilesToShow = unviewedProfiles.slice(0, dailyLimit)
        setProfiles(profilesToShow)
        
        if (profilesToShow.length > 0) {
          setCurrentProfile(profilesToShow[0])
          setCurrentIndex(0)
          setRemainingMatches(dailyLimit)
          calculateMatchScore(userProfile, profilesToShow[0])
        } else {
          setCurrentProfile(null)
          setRemainingMatches(0)
        }
      } else {
        console.error('Failed to fetch profiles')
      }
    } catch (error) {
      console.error('Error fetching profiles:', error)
    }
  }

  // 提取profile中需要评分的字段
  const sanitizeProfile = (profile) => {
    if (!profile) return null
    return {
      user_id: profile.user_id,
      name: profile.name,
      gender: profile.gender,
      age: profile.age,
      mbti: profile.mbti,
      occupation: profile.occupation,
      personality: profile.personality,
      hobbies: profile.hobbies || [],
      location: profile.location,
      ai_tags: profile.ai_tags || []
    }
  }

  const calculateMatchScore = async (profileA, profileB) => {
    setIsLoading(true)
    try {
      // 清理profile数据，移除所有非序列化属性
      const cleanProfileA = sanitizeProfile(profileA)
      const cleanProfileB = sanitizeProfile(profileB)
      
      const response = await fetch(API.match.score, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          profile_a: cleanProfileA,
          profile_b: cleanProfileB,
          match_mode: 'similarity'
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setMatchScore(data.matchScore)
        // Generate match report from the detailed rationale
        const rationale = data.detailedRationale
        let report = ''
        if (rationale.overlapPoints && rationale.overlapPoints.length > 0) {
          report += `**契合点：** ${rationale.overlapPoints.join('、')}\n`
        }
        if (rationale.complementaryPoints && rationale.complementaryPoints.length > 0) {
          report += `**互补点：** ${rationale.complementaryPoints.join('、')}\n`
        }
        if (rationale.summary) {
          report += `**总结：** ${rationale.summary}`
        }
        setMatchReport(report)
      } else {
        console.error('Failed to calculate match score')
        setMatchScore(70) // Default score
        setMatchReport('匹配度分析中...')
      }
    } catch (error) {
      console.error('Error calculating match score:', error)
      setMatchScore(70) // Default score
      setMatchReport('匹配度分析中...')
    } finally {
      setIsLoading(false)
    }
  }

  const handleLike = async () => {
    if (!isLoggedIn || !currentUser) {
      alert('请先登录后再进行匹配操作');
      return;
    }
    
    if (!currentProfile) return
    
    const viewed = JSON.parse(localStorage.getItem('viewedProfiles') || '[]')
    if (!viewed.includes(currentProfile.user_id)) {
      viewed.push(currentProfile.user_id)
      localStorage.setItem('viewedProfiles', JSON.stringify(viewed))
      setViewedProfiles(viewed)
    }

    try {
      const response = await fetch(API.actions.create, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          from_uid: currentUser.user_id || currentUser._id,
          to_uid: currentProfile.user_id,
          action: 'like'
        })
      })
      
      if (response.ok) {
        if (onNavigateToMessage) {
          onNavigateToMessage(currentProfile.user_id)
        }
      }
    } catch (error) {
      console.error('Error sending like action:', error)
    }

    moveToNextProfile()
  }

  const handlePass = async () => {
    if (!isLoggedIn || !currentUser) {
      alert('请先登录后再进行匹配操作');
      return;
    }
    
    if (!currentProfile) return
    
    const viewed = JSON.parse(localStorage.getItem('viewedProfiles') || '[]')
    if (!viewed.includes(currentProfile.user_id)) {
      viewed.push(currentProfile.user_id)
      localStorage.setItem('viewedProfiles', JSON.stringify(viewed))
      setViewedProfiles(viewed)
    }

    try {
      await fetch(API.actions.create, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          from_uid: currentUser.user_id || currentUser._id, // 使用真实的用户ID
          to_uid: currentProfile.user_id,
          action: 'pass'
        })
      })
    } catch (error) {
      console.error('Error sending pass action:', error)
    }

    // Move to next profile
    moveToNextProfile()
  }

  const moveToNextProfile = () => {
    const nextIndex = currentIndex + 1
    if (nextIndex < profiles.length && nextIndex < dailyLimit) {
      const nextProfile = profiles[nextIndex]
      setCurrentProfile(nextProfile)
      setCurrentIndex(nextIndex)
      setRemainingMatches(dailyLimit - nextIndex - 1)
      
      // Get current user profile (mock data)
      const currentUserProfile = {
        user_id: '661d3f2b9e9b4c001f8b4567',
        name: '我',
        gender: '男',
        mbti: 'INTP',
        occupation: '软件工程师',
        personality: '喜欢技术和创新，寻找志同道合的伙伴',
        location: { city: '北京', district: '海淀' },
        ai_tags: ['技术', '创新', '运动']
      }
      
      calculateMatchScore(currentUserProfile, nextProfile)
    } else {
      setCurrentProfile(null)
      setMatchReport('')
      setMatchScore(0)
      setRemainingMatches(0)
    }
  }

  return (
    <div className="soul-page">
      <h2 className="section-title">灵魂匹配</h2>
      <p className="section-subtitle">左滑 Pass · 右滑 Like · AI报告实时生成</p>
      
      {currentProfile ? (
        <div className="soul-profile-card">
          <div className="soul-avatar">
            {currentProfile.name.charAt(0)}
          </div>
          
          <div className="soul-name">{currentProfile.name}</div>
          <div className="soul-mbti-badge">{currentProfile.mbti}</div>
          
          <div className="soul-rating">
            {'★'.repeat(Math.floor(currentProfile.reputation))}
            {'☆'.repeat(5 - Math.floor(currentProfile.reputation))}
            <span style={{ marginLeft: '5px' }}>{currentProfile.reputation.toFixed(1)}</span>
          </div>
          
          <div className="soul-location-info">
            {currentProfile.location.city} · {currentProfile.location.district}
          </div>
          
          <div className="soul-tags-container">
            {currentProfile.ai_tags.map((tag, index) => (
              <span key={index} className="soul-tag">
                {tag}
              </span>
            ))}
          </div>
          
          <div className="soul-description">
            "{currentProfile.personality}"
          </div>
          
          <div className="soul-ai-report" onClick={() => setShowFullReport(!showFullReport)}>
            <div className="soul-ai-report-title">
              AI 匹配报告 {!showFullReport ? '▼ 点击展开' : '▲ 点击收起'}
            </div>
            {showFullReport && (
              <div className="soul-ai-report-content">
                {isLoading ? '正在分析画像契合度...' : matchReport || '暂无匹配报告'}
              </div>
            )}
            <div className="soul-match-score">
              <div className="soul-match-percentage">{matchScore}%</div>
              <div className="soul-match-label">灵魂契合度</div>
            </div>
          </div>
          
          <div className="soul-actions">
            <button 
              className="soul-action-btn soul-pass-btn"
              onClick={handlePass}
              disabled={isLoading}
            >
              ×
            </button>
            <button 
              className="soul-action-btn soul-like-btn"
              onClick={handleLike}
              disabled={isLoading}
            >
              ♥
            </button>
          </div>
          
          <div className="soul-limit-hint">
            {currentIndex + 1}/{dailyLimit} 位推荐
          </div>
        </div>
      ) : (
        <div className="soul-empty-card">
          <div className="soul-empty-icon">💔</div>
          <div className="soul-empty-text">暂无更多推荐</div>
          <p style={{ color: '#aaa', marginTop: '1rem' }}>每天可匹配 {dailyLimit} 位用户，明天再来看看吧</p>
          <button 
            className="btn btn-primary" 
            style={{ marginTop: '2rem' }}
            onClick={fetchProfiles}
          >
            刷新推荐
          </button>
        </div>
      )}
    </div>
  )
}

export default SoulPage
