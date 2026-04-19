import React, { useState, useEffect, useRef } from 'react'
import API from '../utils/api'
import './ActivityAgent.css'

const ActivityAgent = ({ isLoggedIn, currentUser, onClose, onViewActivity }) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'agent',
      content: '您好！我是活动助手 🤖\n\n我可以帮您：\n• 根据您的兴趣推荐活动\n• 帮您找到志同道合的伙伴\n• 如果没有合适的活动，可以帮您创建\n\n请告诉我您想参加什么类型的活动？',
      suggestions: [
        '推荐一些运动活动',
        '想找些娱乐活动',
        '帮我找个学习活动',
        '创建一个活动'
      ]
    }
  ])
  const [inputText, setInputText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [userRequirements, setUserRequirements] = useState({})
  const [showRecommendations, setShowRecommendations] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (text) => {
    if (!text.trim() || isLoading) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: text
    }
    setMessages(prev => [...prev, userMessage])
    setInputText('')
    setIsLoading(true)

    try {
      const response = await fetch(API.agent.chat, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          requirements: userRequirements,
          conversation_history: messages.slice(-6).map(m => ({
            role: m.type === 'user' ? 'user' : 'assistant',
            content: m.content
          })),
          user_id: currentUser?.user_id || currentUser?._id
        })
      })

      if (response.ok) {
        const data = await response.json()
        
        setUserRequirements(data.requirements || userRequirements)
        
        // Handle publish action
        if (data.mode === 'publish' || data.action === 'publish') {
          const agentMessage = {
            id: Date.now() + 1,
            type: 'agent',
            content: data.response,
            published: data.published
          }
          setMessages(prev => [...prev, agentMessage])
        } 
        // Handle trip plan confirmation
        else if (data.mode === 'confirm_publish' || data.trip_plan) {
          const agentMessage = {
            id: Date.now() + 1,
            type: 'agent',
            content: data.response,
            trip_plan: data.trip_plan,
            suggestions: data.suggestions || ['发布行程', '修改行程']
          }
          setMessages(prev => [...prev, agentMessage])
        }
        // Handle recommendations
        else if (data.recommendations && data.recommendations.length > 0) {
          const agentMessage = {
            id: Date.now() + 1,
            type: 'agent',
            content: data.response,
            recommendations: data.recommendations
          }
          setMessages(prev => [...prev, agentMessage])
          setShowRecommendations(true)
        } 
        // Handle regular response
        else {
          const agentMessage = {
            id: Date.now() + 1,
            type: 'agent',
            content: data.response,
            suggestions: data.suggestions || []
          }
          setMessages(prev => [...prev, agentMessage])
        }
      } else {
        const errorMsg = {
          id: Date.now() + 1,
          type: 'agent',
          content: '抱歉，我遇到了一些问题，请稍后重试。'
        }
        setMessages(prev => [...prev, errorMsg])
      }
    } catch (error) {
      console.error('Agent error:', error)
      const errorMsg = {
        id: Date.now() + 1,
        type: 'agent',
        content: '网络错误，请检查网络后重试。'
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSuggestionClick = (text) => {
    handleSend(text)
  }

  const handleQuickStart = (text) => {
    handleSend(text)
  }

  return (
    <div className="agent-overlay" onClick={onClose}>
      <div className="agent-container" onClick={e => e.stopPropagation()}>
        <div className="agent-header">
          <div className="agent-title">
            <span className="agent-avatar">🤖</span>
            <span>活动助手</span>
          </div>
          <button className="agent-close" onClick={onClose}>✕</button>
        </div>

        <div className="agent-messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`message message-${msg.type}`}>
              {msg.type === 'agent' && <span className="message-avatar">🤖</span>}
              <div className="message-content">
                {msg.content.split('\n').map((line, i) => (
                  <p key={i}>{line}</p>
                ))}
                
                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div className="message-suggestions">
                    {msg.suggestions.map((suggestion, i) => (
                      <button
                        key={i}
                        className="suggestion-btn"
                        onClick={() => handleSuggestionClick(suggestion)}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}

                {msg.recommendations && msg.recommendations.length > 0 && (
                  <div className="recommendations-list">
                    {msg.recommendations.map((activity, i) => (
                      <div 
                        key={i} 
                        className="recommendation-card"
                        onClick={() => onViewActivity && onViewActivity(activity)}
                      >
                        <div className="recommendation-header">
                          <span className="recommendation-category">{activity.category}</span>
                          <span className="recommendation-match">{activity.match_score}% 匹配</span>
                        </div>
                        <h4>{activity.title}</h4>
                        <p>{activity.content?.substring(0, 60)}...</p>
                        <div className="recommendation-footer">
                          <span>📍 {activity.location?.city} {activity.location?.district}</span>
                          <span>💰 {activity.budget}元</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="message message-agent">
              <span className="message-avatar">🤖</span>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <div className="agent-input-area">
          <input
            type="text"
            className="agent-input"
            placeholder="描述您的需求..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend(inputText)}
            disabled={isLoading}
          />
          <button 
            className="agent-send-btn"
            onClick={() => handleSend(inputText)}
            disabled={!inputText.trim() || isLoading}
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  )
}

export default ActivityAgent
