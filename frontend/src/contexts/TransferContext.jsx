import React, { createContext, useState, useContext, useEffect } from 'react'
import api from '../utils/api'
import { useAuth } from './AuthContext'

const TransferContext = createContext()

export const useTransfer = () => {
  const context = useContext(TransferContext)
  if (!context) {
    throw new Error('useTransfer must be used within TransferProvider')
  }
  return context
}

export const TransferProvider = ({ children }) => {
  const { user } = useAuth()
  const [pendingTransferConfirmCount, setPendingTransferConfirmCount] = useState(0)
  const [pendingApprovalCount, setPendingApprovalCount] = useState(0)
  const [pendingSafetyCheckCount, setPendingSafetyCheckCount] = useState(0)

  const fetchPendingConfirmations = async () => {
    if (!user) {
      setPendingTransferConfirmCount(0)
      return
    }
    try {
      const response = await api.get('/transfers/', {
        params: { status: 'waiting_confirmation' }
      })
      const count = response.data.filter((item) => item.to_user_id === user.id).length
      setPendingTransferConfirmCount(count)
    } catch (error) {
      console.error('获取待确认交接失败:', error)
      setPendingTransferConfirmCount(0)
    }
  }

  const fetchPendingApprovals = async () => {
    if (!user || user.role !== 'admin') {
      setPendingApprovalCount(0)
      return
    }
    try {
      // 获取所有待审批的申请（交接、退回、编辑）
      const [transfersRes, returnsRes, editsRes] = await Promise.all([
        api.get('/transfers/', { params: { status: 'pending' } }),
        api.get('/returns/', { params: { status: 'pending' } }),
        api.get('/edit-requests/', { params: { status: 'pending' } })
      ])
      const totalCount = transfersRes.data.length + returnsRes.data.length + editsRes.data.length
      setPendingApprovalCount(totalCount)
    } catch (error) {
      console.error('获取待审批数量失败:', error)
      setPendingApprovalCount(0)
    }
  }

  const fetchPendingSafetyChecks = async () => {
    if (!user || user.role === 'admin') {
      setPendingSafetyCheckCount(0)
      return
    }
    try {
      // 获取待检查的安全检查任务
      const response = await api.get('/safety-check-results/my-tasks', {
        params: { status: 'pending' }
      })
      // 计算所有任务中待检查资产的总数
      const totalPendingCount = response.data.items?.reduce((sum, task) => {
        return sum + (task.pending_count || 0)
      }, 0) || 0
      setPendingSafetyCheckCount(totalPendingCount)
    } catch (error) {
      console.error('获取待检查任务数量失败:', error)
      setPendingSafetyCheckCount(0)
    }
  }

  useEffect(() => {
    fetchPendingConfirmations()
    fetchPendingApprovals()
    fetchPendingSafetyChecks()
    // 每30秒刷新一次，确保数据同步
    const interval = setInterval(() => {
      fetchPendingConfirmations()
      fetchPendingApprovals()
      fetchPendingSafetyChecks()
    }, 30000)
    return () => clearInterval(interval)
  }, [user])

  const value = {
    pendingTransferConfirmCount,
    refreshPendingConfirmations: fetchPendingConfirmations,
    pendingApprovalCount,
    refreshPendingApprovals: fetchPendingApprovals,
    pendingSafetyCheckCount,
    refreshPendingSafetyChecks: fetchPendingSafetyChecks
  }

  return <TransferContext.Provider value={value}>{children}</TransferContext.Provider>
}

