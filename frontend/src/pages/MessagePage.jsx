import React, { useState, useEffect, useRef } from 'react'
import API from '../utils/api'

const MessagePage = ({ currentUser, currentPage, initialUserId }) => {
  const [conversations, setConversations] = useState([])
  const [selectedConversation, setSelectedConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showUserDetails, setShowUserDetails] = useState(false)
  const [userDetails, setUserDetails] = useState(null)
  const hasTriedCreateConv = useRef(false)

  // Get current user ID from props
  const currentUserId = currentUser?.user_id || currentUser?._id

  const fetchConversations = async () => {
    try {
      const response = await fetch(API.conversations.list(currentUserId))
      if (response.ok) {
        const data = await response.json()
        setConversations(data)
      } else {
        console.error('Failed to fetch conversations')
      }
    } catch (error) {
      console.error('Error fetching conversations:', error)
    }
  }

  const createConversation = async (otherUserId) => {
    try {
      const response = await fetch(API.conversations.create, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          participant1: currentUserId,
          participant2: otherUserId
        })
      })
      if (response.ok) {
        fetchConversations()
      }
    } catch (error) {
      console.error('Error creating conversation:', error)
    }
  }

  // Fetch conversations on component mount
  useEffect(() => {
    if (currentUserId) {
      fetchConversations()
    }
  }, [currentUser, currentPage])

  // Auto-select or create conversation when initialUserId is provided
  useEffect(() => {
    if (initialUserId && currentUserId && !hasTriedCreateConv.current) {
      const targetConv = conversations.find(c => 
        c.participants.includes(initialUserId)
      )
      if (targetConv) {
        setSelectedConversation(targetConv)
      } else if (conversations.length >= 0) {
        hasTriedCreateConv.current = true
        createConversation(initialUserId)
      }
    }
  }, [initialUserId, currentUserId])

  // Fetch messages when conversation changes
  useEffect(() => {
    if (selectedConversation) {
      fetchMessages(selectedConversation.conversation_id)
    }
  }, [selectedConversation])

  const fetchMessages = async (conversationId) => {
    try {
      const response = await fetch(API.conversations.messages(conversationId))
      if (response.ok) {
        const data = await response.json()
        setMessages(data)
      } else {
        console.error('Failed to fetch messages')
      }
    } catch (error) {
      console.error('Error fetching messages:', error)
    }
  }

  const fetchUserDetails = async (userId) => {
    setIsLoading(true)
    try {
      const response = await fetch(API.user.details(userId))
      if (response.ok) {
        const data = await response.json()
        setUserDetails(data)
        setShowUserDetails(true)
      } else {
        console.error('Failed to fetch user details')
      }
    } catch (error) {
      console.error('Error fetching user details:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation || !currentUserId) return

    try {
      const response = await fetch(API.messages.create, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sender_id: currentUserId,
          conversation_id: selectedConversation.conversation_id,
          content: newMessage
        })
      })

      if (response.ok) {
        // Clear input and fetch updated messages
        setNewMessage('')
        fetchMessages(selectedConversation.conversation_id)
      } else {
        console.error('Failed to send message')
      }
    } catch (error) {
      console.error('Error sending message:', error)
    }
  }

  const handleConversationSelect = (conversation) => {
    setSelectedConversation(conversation)
  }

  const handleUserAvatarClick = (userId) => {
    fetchUserDetails(userId)
  }

  return (
    <div className="message-page">
      <h2 className="section-title">消息列表</h2>
      <p className="section-subtitle">与搭子的聊天记录</p>

      <div style={{ display: 'flex', height: '70vh', gap: '20px' }}>
        {/* Conversation List */}
        <div style={{ flex: 1, border: '1px solid #333', borderRadius: '8px', overflow: 'hidden' }}>
          <div style={{ padding: '15px', borderBottom: '1px solid #333', fontWeight: 'bold' }}>
            对话列表
          </div>
          <div style={{ height: 'calc(100% - 50px)', overflowY: 'auto' }}>
            {conversations.map(conversation => (
              <div
                key={conversation.conversation_id}
                style={{
                  padding: '15px',
                  borderBottom: '1px solid #333',
                  cursor: 'pointer',
                  backgroundColor: selectedConversation?.conversation_id === conversation.conversation_id ? '#333' : 'transparent'
                }}
                onClick={() => handleConversationSelect(conversation)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div 
                      style={{
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        backgroundColor: '#4CAF50',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'white',
                        fontWeight: 'bold',
                        cursor: 'pointer'
                      }}
                      onClick={(e) => {
                        e.stopPropagation()
                        handleUserAvatarClick(conversation.other_user_id)
                      }}
                    >
                      {conversation.other_user_name.charAt(0)}
                    </div>
                    <span style={{ fontWeight: 'bold' }}>{conversation.other_user_name}</span>
                  </div>
                  <span style={{ fontSize: '0.8rem', color: '#aaa' }}>
                    {conversation.last_message ? new Date(conversation.last_message.created_at).toLocaleTimeString() : ''}
                  </span>
                </div>
                <div style={{ fontSize: '0.9rem', color: '#aaa', marginLeft: '50px' }}>
                  {conversation.last_message ? conversation.last_message.content : '暂无消息'}
                </div>
              </div>
            ))}
            {conversations.length === 0 && (
              <div style={{ padding: '20px', textAlign: 'center', color: '#aaa' }}>
                暂无对话记录
              </div>
            )}
          </div>
        </div>

        {/* Chat Interface */}
        {selectedConversation ? (
          <div style={{ flex: 2, border: '1px solid #333', borderRadius: '8px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '15px', borderBottom: '1px solid #333', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div 
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    backgroundColor: '#4CAF50',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontWeight: 'bold',
                    cursor: 'pointer'
                  }}
                  onClick={() => handleUserAvatarClick(selectedConversation.other_user_id)}
                >
                  {selectedConversation.other_user_name.charAt(0)}
                </div>
                <span style={{ fontWeight: 'bold' }}>{selectedConversation.other_user_name}</span>
              </div>
            </div>

            <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
              {messages.map(message => (
                <div
                  key={message._id}
                  style={{
                    marginBottom: '15px',
                    display: 'flex',
                    justifyContent: message.sender_id === currentUserId ? 'flex-end' : 'flex-start'
                  }}
                >
                  <div
                    style={{
                      maxWidth: '70%',
                      padding: '10px 15px',
                      borderRadius: '18px',
                      backgroundColor: message.sender_id === currentUserId ? '#4CAF50' : '#333'
                    }}
                  >
                    <p style={{ margin: 0 }}>{message.content}</p>
                    <div style={{ fontSize: '0.7rem', color: '#aaa', textAlign: 'right', marginTop: '5px' }}>
                      {new Date(message.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div style={{ padding: '15px', borderTop: '1px solid #333', display: 'flex', gap: '10px' }}>
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="输入消息..."
                style={{ flex: 1, padding: '10px', borderRadius: '20px', border: '1px solid #333', backgroundColor: '#111' }}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              />
              <button
                style={{
                  padding: '10px 20px',
                  borderRadius: '20px',
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  cursor: 'pointer'
                }}
                onClick={sendMessage}
              >
                发送
              </button>
            </div>
          </div>
        ) : (
          <div style={{ flex: 2, border: '1px solid #333', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa' }}>
            选择一个对话开始聊天
          </div>
        )}
      </div>

      {/* User Details Modal */}
      {showUserDetails && userDetails && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: '#111',
            border: '1px solid #333',
            borderRadius: '8px',
            padding: '20px',
            width: '500px',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3>用户详情</h3>
              <button
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#aaa',
                  fontSize: '1.5rem',
                  cursor: 'pointer'
                }}
                onClick={() => setShowUserDetails(false)}
              >
                ×
              </button>
            </div>

            <div style={{ textAlign: 'center', marginBottom: '20px' }}>
              <div style={{
                width: '100px',
                height: '100px',
                borderRadius: '50%',
                backgroundColor: '#4CAF50',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 'bold',
                fontSize: '2rem',
                margin: '0 auto 10px'
              }}>
                {userDetails.profile.name ? userDetails.profile.name.charAt(0) : 'U'}
              </div>
              <h4>{userDetails.profile.name || '未知用户'}</h4>
              <p>{userDetails.profile.mbti || 'MBTI未知'} · {userDetails.profile.occupation || '职业未知'}</p>
              <div style={{ marginTop: '10px' }}>
                {'★'.repeat(Math.floor(userDetails.profile.reputation || 0))}
                {'☆'.repeat(5 - Math.floor(userDetails.profile.reputation || 0))}
                <span style={{ marginLeft: '5px' }}>{userDetails.profile.reputation || 0}</span>
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <h5>个人简介</h5>
              <p>{userDetails.profile.personality || '暂无简介'}</p>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <h5>正在发起的活动</h5>
              {userDetails.ongoing_activities.length > 0 ? (
                <ul style={{ listStyle: 'none', padding: 0 }}>
                  {userDetails.ongoing_activities.map(activity => (
                    <li key={activity._id} style={{ padding: '10px', borderBottom: '1px solid #333' }}>
                      <strong>{activity.title}</strong>
                      <p style={{ margin: '5px 0', fontSize: '0.9rem', color: '#aaa' }}>{activity.content}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>暂无正在发起的活动</p>
              )}
            </div>

            <div style={{ marginBottom: '20px' }}>
              <h5>历史活动</h5>
              {userDetails.past_activities.length > 0 ? (
                <ul style={{ listStyle: 'none', padding: 0 }}>
                  {userDetails.past_activities.map(activity => (
                    <li key={activity._id} style={{ padding: '10px', borderBottom: '1px solid #333' }}>
                      <strong>{activity.title}</strong>
                      <p style={{ margin: '5px 0', fontSize: '0.9rem', color: '#aaa' }}>{activity.content}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>暂无历史活动</p>
              )}
            </div>

            <div>
              <h5>评价</h5>
              {userDetails.reviews.length > 0 ? (
                <ul style={{ listStyle: 'none', padding: 0 }}>
                  {userDetails.reviews.map(review => (
                    <li key={review._id} style={{ padding: '10px', borderBottom: '1px solid #333' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                        <span>用户{review.from_uid.slice(-4)}</span>
                        <span>{'★'.repeat(review.rating)}</span>
                      </div>
                      <p style={{ margin: 0, fontSize: '0.9rem' }}>{review.comment || '无评价内容'}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>暂无评价</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MessagePage