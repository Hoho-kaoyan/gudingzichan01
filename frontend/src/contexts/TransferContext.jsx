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

  const LOG = '[侧栏-待检查]'
  // 与「我的检查任务」列表页同源：拉取 my-tasks 全量后按 pending_count 求和，用于侧栏小橙点
  const fetchPendingSafetyChecks = async () => {
    if (!user) {
      console.warn(LOG, 'fetchPendingSafetyChecks 未登录跳过', { user })
      setPendingSafetyCheckCount(0)
      return
    }
    console.log(LOG, 'fetchPendingSafetyChecks 开始', { userId: user.id, role: user.role })
    try {
      const response = await api.get('/safety-check-results/my-tasks')
      const raw = response?.data
      const items = Array.isArray(raw?.items) ? raw.items : Array.isArray(raw) ? raw : []
      const count = items.reduce((sum, task) => {
        const n = Number(task?.pending_count ?? task?.pendingCount ?? 0) || 0
        return sum + n
      }, 0)
      console.log(LOG, 'fetchPendingSafetyChecks 成功', { rawKeys: raw ? Object.keys(raw) : [], itemsLength: items.length, pendingCounts: items.map(t => t?.pending_count ?? t?.pendingCount), count })
      setPendingSafetyCheckCount(count)
    } catch (error) {
      console.error(LOG, 'fetchPendingSafetyChecks 失败', { message: error?.message, status: error?.response?.status, detail: error?.response?.data })
      setPendingSafetyCheckCount(0)
    }
  }

  useEffect(() => {
    console.log(LOG, 'useEffect 执行', { hasUser: !!user, userId: user?.id, role: user?.role })
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

  // 列表页拉取到 my-tasks 后可直接用同一份数据同步侧栏数量，避免二次请求或解析不一致
  const syncPendingSafetyCheckCountFromTasks = (tasks) => {
    if (!Array.isArray(tasks)) {
      console.warn(LOG, 'syncPendingSafetyCheckCountFromTasks 非数组', { type: typeof tasks })
      return
    }
    const count = tasks.reduce((sum, t) => sum + (Number(t?.pending_count ?? t?.pendingCount) || 0), 0)
    console.log(LOG, 'syncPendingSafetyCheckCountFromTasks 调用', { tasksLength: tasks.length, pendingCounts: tasks.map(t => t?.pending_count ?? t?.pendingCount), count })
    setPendingSafetyCheckCount(count)
  }

  const value = {
    pendingTransferConfirmCount,
    refreshPendingConfirmations: fetchPendingConfirmations,
    pendingApprovalCount,
    refreshPendingApprovals: fetchPendingApprovals,
    pendingSafetyCheckCount,
    refreshPendingSafetyChecks: fetchPendingSafetyChecks,
    syncPendingSafetyCheckCountFromTasks
  }

  return <TransferContext.Provider value={value}>{children}</TransferContext.Provider>
}

