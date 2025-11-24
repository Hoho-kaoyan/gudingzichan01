import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic } from 'antd'
import { DatabaseOutlined, UserOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'
import api from '../utils/api'

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalAssets: 0,
    totalUsers: 0,
    pendingApprovals: 0,
    inUseAssets: 0
  })

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await api.get('/stats/')
      setStats({
        totalAssets: response.data.total_assets,
        totalUsers: response.data.total_users,
        pendingApprovals: response.data.pending_approvals,
        inUseAssets: response.data.in_use_assets
      })
    } catch (error) {
      console.error('获取统计数据失败:', error)
    }
  }

  return (
    <div>
      <h1>首页</h1>
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="资产总数"
              value={stats.totalAssets}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="在用资产"
              value={stats.inUseAssets}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="用户总数"
              value={stats.totalUsers}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="待审批"
              value={stats.pendingApprovals}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard

