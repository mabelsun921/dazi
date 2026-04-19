const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5005';

export const API = {
  base: API_BASE_URL,
  
  auth: {
    login: `${API_BASE_URL}/api/auth/login`,
    register: `${API_BASE_URL}/api/auth/register`,
  },
  
  profile: {
    get: (userId) => `${API_BASE_URL}/api/profile/${userId}`,
    update: (userId) => `${API_BASE_URL}/api/profile/${userId}`,
    getAll: `${API_BASE_URL}/api/profile/all`,
  },
  
  activities: {
    list: `${API_BASE_URL}/api/activities`,
    create: `${API_BASE_URL}/api/activities`,
    get: (id) => `${API_BASE_URL}/api/activities/${id}`,
    update: (id) => `${API_BASE_URL}/api/activities/${id}`,
    delete: (id, userId) => `${API_BASE_URL}/api/activities/${id}?user_id=${userId}`,
    search: `${API_BASE_URL}/api/activities/search`,
    apply: (id) => `${API_BASE_URL}/api/activities/${id}/apply`,
    score: `${API_BASE_URL}/api/activity/score`,
    aiHint: `${API_BASE_URL}/api/activity/ai_hint`,
  },
  
  users: {
    get: (userId) => `${API_BASE_URL}/api/users/${userId}`,
  },
  
  applications: {
    update: (id) => `${API_BASE_URL}/api/applications/${id}`,
    list: `${API_BASE_URL}/api/applications`,
  },
  
  user: {
    details: (userId) => `${API_BASE_URL}/api/user/${userId}/details`,
    appliedActivities: (userId) => `${API_BASE_URL}/api/user/${userId}/applied-activities`,
    hostApplications: (userId) => `${API_BASE_URL}/api/user/${userId}/host-applications`,
    reviewsGiven: (userId) => `${API_BASE_URL}/api/user/${userId}/reviews-given`,
    stats: (userId) => `${API_BASE_URL}/api/user/${userId}/stats`,
  },
  
  match: {
    score: `${API_BASE_URL}/api/match/score`,
  },
  
  actions: {
    create: `${API_BASE_URL}/api/actions`,
  },
  
  conversations: {
    list: (userId) => `${API_BASE_URL}/api/conversations/${userId}`,
    create: `${API_BASE_URL}/api/conversations`,
    messages: (conversationId) => `${API_BASE_URL}/api/conversations/${conversationId}/messages`,
  },
  
  messages: {
    create: `${API_BASE_URL}/api/messages`,
  },
  
  agent: {
    chat: `${API_BASE_URL}/api/agent/chat`,
  },
};

export default API;
