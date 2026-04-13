import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_BASE_URL } from "../config";
import axios from "axios";

const BASE_URL = API_BASE_URL;

// ── Token refresh lock to prevent race conditions ───────────────────────────────
let isRefreshing = false;
let refreshSubscribers = [];

/**
 * Add a callback to be executed when token refresh completes
 */
function subscribeTokenRefresh(callback) {
  refreshSubscribers.push(callback);
}

/**
 * Execute all pending callbacks with new token
 */
function onRefreshed(token) {
  refreshSubscribers.forEach(callback => callback(token));
  refreshSubscribers = [];
}

// Create axios instance
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

// Request interceptor - inject Bearer token
api.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem("sb_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle 401 and auto-refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // If already refreshing, wait for the refresh to complete
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          });
        }).catch((err) => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Attempt to refresh token
        const refreshToken = await AsyncStorage.getItem("sb_refresh_token");
        if (!refreshToken) {
          throw new Error("No refresh token available");
        }

        const response = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: new_refresh_token } = response.data;

        // Store new tokens
        await AsyncStorage.setItem("sb_token", access_token);
        await AsyncStorage.setItem("sb_refresh_token", new_refresh_token);

        // Notify all waiting requests
        onRefreshed(access_token);

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed - clear tokens and redirect to login
        await AsyncStorage.removeItem("sb_token");
        await AsyncStorage.removeItem("sb_refresh_token");
        await AsyncStorage.removeItem("sb_username");
        
        // Note: Navigation would need to be handled by the React Native navigation system
        // This is a placeholder - actual implementation would use navigation.navigate('Login')
        console.error("Token refresh failed, user must log in again");
        
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

const getAuthHeader = async () => {
  const token = await AsyncStorage.getItem("sb_token");
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const askQuestion = async (q, options = {}) => {
  try {
    const authHeader = await getAuthHeader();
    const { limit = 5, intent_filter, speaker_filter } = options;
    
    let url = `${BASE_URL}/query?q=${encodeURIComponent(q)}&limit=${limit}`;
    if (intent_filter) url += `&intent_filter=${intent_filter}`;
    if (speaker_filter) url += `&speaker_filter=${speaker_filter}`;
    
    const response = await fetch(url, {
      headers: { ...authHeader }
    });
    
    if (!response.ok) {
      console.warn(`Query failed: ${response.status}`);
      return { answer: 'Neural core responded with error.', context: [], sources: [] };
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error asking question:', error);
    return { answer: 'Sorry, I could not connect to your SecondBrain.', context: [], sources: [] };
  }
};

export const getTimeline = async () => {
  try {
    const authHeader = await getAuthHeader();
    const response = await fetch(`${BASE_URL}/timeline`, {
      headers: { ...authHeader }
    });
    
    if (!response.ok) return { timeline: [] };
    return await response.json();
  } catch (error) {
    console.warn('Timeline fetch failed:', error.message);
    return { timeline: [] };
  }
};

export const getSummary = async () => {
  try {
    const authHeader = await getAuthHeader();
    const response = await fetch(`${BASE_URL}/summary`, {
      headers: { ...authHeader }
    });
    
    if (!response.ok) return { summary: 'Summary unavailable.' };
    return await response.json();
  } catch (error) {
    return { summary: 'No summary available (Connection error).' };
  }
};

export const startRecording = async (duration = 10) => {
  try {
    const authHeader = await getAuthHeader();
    const response = await fetch(`${BASE_URL}/record`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader
      },
      body: JSON.stringify({ 
        duration,
        filename: `recording_${Date.now()}.wav`
      }),
    });
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        return { success: false, error: errorData.detail };
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error recording:', error);
    return { success: false, error: 'Failed to record audio' };
  }
};

export const getInsights = async () => {
  try {
    const authHeader = await getAuthHeader();
    const response = await fetch(`${BASE_URL}/insights`, {
      headers: { ...authHeader }
    });
    
    if (!response.ok) return { insights: [] };
    return await response.json();
  } catch (error) {
    console.warn('Insights fetch failed:', error.message);
    return { insights: [] };
  }
};

export const getStatistics = async () => {
  try {
    const authHeader = await getAuthHeader();
    const response = await fetch(`${BASE_URL}/statistics`, {
      headers: { ...authHeader }
    });
    
    if (!response.ok) return { total: 0, by_intent: {}, by_speaker: {}, avg_importance: 0.0, recent_count: 0 };
    return await response.json();
  } catch (error) {
    return { total: 0, by_intent: {refresh_token', data.refresh_token);
    await AsyncStorage.setItem('sb_}, by_speak}, avg_importance: 0.0, recent_count: 0 };
  }
};

export const trainSpeaker = async (name, text) => {
  try {
    const authHeader = await getAuthHeader();
    const response = await fetch(`${BASE_URL}/speaker/train`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader
      },
      body: JSON.stringify({ name, text }),
    });
    
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Error training speaker:', error);
    return { error: 'Failed to train speaker' };
  }
};

export const getVoiceProfiles = async () => {
  try {
    const authHeader = await getAuthHeader();
    const response = await fetch(`${BASE_URL}/speaker/profiles`, {
      headers: { ...authHeader }
    });
    refresh_token');
    await AsyncStorage.removeItem('sb_
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Error getting voice profiles:', error);
    return { profiles: [] };
  }
};

export const getStatus = async () => {
  try {
    const authHeader = await getAuthHeader();
    const response = await fetch(`${BASE_URL}/status`, {
      headers: { ...authHeader }
    });
    
    if (!response.ok) return { nodes: 0, status: 'error' };
    return await response.json();
  } catch (error) {
    console.warn('Status fetch failed:', error.message);
    return { nodes: 0, status: 'offline' };
  }
};

export const login = async (username, password) => {
  try {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }
    
    const data = await response.json();
    await AsyncStorage.setItem('sb_token', data.access_token);
    await AsyncStorage.setItem('sb_username', data.username);
    return data;
  } catch (error) {
    console.error('Error logging in:', error);
    throw error;
  }
};

export const signup = async (username, password) => {
  try {
    const response = await fetch(`${BASE_URL}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Signup failed');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error signing up:', error);
    throw error;
  }
};

export const logout = async () => {
  try {
    await AsyncStorage.removeItem('sb_token');
    await AsyncStorage.removeItem('sb_username');
    return true;
  } catch (error) {
    console.error('Error logging out:', error);
    return false;
  }
};
