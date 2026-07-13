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
  const [requirePasswordChange, setRequirePasswordChange] = useState(false)

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
      const { access_token, user: userData, require_password_change } = response.data
      localStorage.setItem('token', access_token)
      setToken(access_token)
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      setUser(userData)
      setRequirePasswordChange(require_password_change)
      message.success('登录成功')
      return true
    } catch (error) {
      // 不再在此处直接弹窗，交由调用者处理更复杂的 UI 逻辑
      throw error
    }
  }


  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    setRequirePasswordChange(false)
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
    requirePasswordChange,
    setRequirePasswordChange,
    isAdmin: user?.role === 'admin',
    isLeader: user?.role === 'leader',
    isAdminOrLeader: user?.role === 'admin' || user?.role === 'leader'
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
