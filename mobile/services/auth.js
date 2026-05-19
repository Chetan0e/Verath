import React, { useState, createContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { TOKEN_KEY, REFRESH_KEY, USERNAME_KEY } from './authKeys';
import axios from 'axios';
import { API_BASE_URL } from "../config";

export const AuthContext = createContext({});

const API_BASE = API_BASE_URL;

export const AuthProvider = ({ children }) => {
  const [userToken, setUserToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const login = async (username, password) => {
    try {
      const response = await axios.post(`${API_BASE}/auth/login`, { username, password });
      const token = response.data.access_token;
      await AsyncStorage.setItem(TOKEN_KEY, token);
      if (response.data.refresh_token) await AsyncStorage.setItem(REFRESH_KEY, response.data.refresh_token);
      if (response.data.username) await AsyncStorage.setItem(USERNAME_KEY, response.data.username);
      setUserToken(token);
    } catch (e) {
      console.error("Login failed", e);
      throw e;
    }
  };

  const logout = async () => {
    await AsyncStorage.removeItem(TOKEN_KEY);
    await AsyncStorage.removeItem(REFRESH_KEY);
    await AsyncStorage.removeItem(USERNAME_KEY);
    setUserToken(null);
  };

  const isLoggedIn = async () => {
    try {
      setIsLoading(true);
      let token = await AsyncStorage.getItem(TOKEN_KEY);
      setUserToken(token);
      setIsLoading(false);
    } catch (e) {
      console.log("isLogged in error", e);
    }
  };

  useEffect(() => {
    isLoggedIn();
  }, []);

  return (
    <AuthContext.Provider value={{ login, logout, userToken, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};
