import React, { createContext, useState, useContext, useEffect } from 'react'
import { message } from 'antd'
import api from '../utils/api'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(localStorage.getItem('token'))

  useEffect(() => {
    if (token) {
      // 验证token并获取用户信息
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      fetchUserInfo()
    } else {
      setLoading(false)
    }
  }, [token])

  const fetchUserInfo = async () => {
    try {
      const response = await api.get('/users/me')
      setUser(response.data)
      setLoading(false)
    } catch (error) {
      console.error('获取用户信息失败:', error)
      localStorage.removeItem('token')
      setToken(null)
      setUser(null)
      setLoading(false)
    }
  }

  const login = async (ehrNumber, password) => {
    try {
      const response = await api.post('/auth/login', {
        ehr_number: ehrNumber,
        password: password
      })
      const { access_token, user: userData } = response.data
      localStorage.setItem('token', access_token)
      setToken(access_token)
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      setUser(userData)
      message.success('登录成功')
      return true
    } catch (error) {
      message.error(error.response?.data?.detail || '登录失败')
      return false
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    delete api.defaults.headers.common['Authorization']
    message.success('已退出登录')
  }

  const checkEHR = async (ehrNumber) => {
    try {
      const response = await api.post('/auth/check-ehr', {
        ehr_number: ehrNumber
      })
      return response.data
    } catch (error) {
      return { exists: false, real_name: null }
    }
  }

  const value = {
    user,
    loading,
    login,
    logout,
    checkEHR,
    isAdmin: user?.role === 'admin'
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}


import { message } from 'antd'
import api from '../utils/api'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(localStorage.getItem('token'))

  useEffect(() => {
    if (token) {
      // 验证token并获取用户信息
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      fetchUserInfo()
    } else {
      setLoading(false)
    }
  }, [token])

  const fetchUserInfo = async () => {
    try {
      const response = await api.get('/users/me')
      setUser(response.data)
      setLoading(false)
    } catch (error) {
      console.error('获取用户信息失败:', error)
      localStorage.removeItem('token')
      setToken(null)
      setUser(null)
      setLoading(false)
    }
  }

  const login = async (ehrNumber, password) => {
    try {
      const response = await api.post('/auth/login', {
        ehr_number: ehrNumber,
        password: password
      })
      const { access_token, user: userData } = response.data
      localStorage.setItem('token', access_token)
      setToken(access_token)
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      setUser(userData)
      message.success('登录成功')
      return true
    } catch (error) {
      message.error(error.response?.data?.detail || '登录失败')
      return false
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    delete api.defaults.headers.common['Authorization']
    message.success('已退出登录')
  }

  const checkEHR = async (ehrNumber) => {
    try {
      const response = await api.post('/auth/check-ehr', {
        ehr_number: ehrNumber
      })
      return response.data
    } catch (error) {
      return { exists: false, real_name: null }
    }
  }

  const value = {
    user,
    loading,
    login,
    logout,
    checkEHR,
    isAdmin: user?.role === 'admin'
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}




