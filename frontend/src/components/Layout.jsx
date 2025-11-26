import React, { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, Avatar, Dropdown, Space, Badge } from 'antd'
import {
  DashboardOutlined,
  UserOutlined,
  DatabaseOutlined,
  SwapOutlined,
  RollbackOutlined,
  CheckCircleOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SafetyOutlined,
  FileTextOutlined
} from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'
import { useTransfer } from '../contexts/TransferContext'

const { Header, Sider, Content } = AntLayout

const Layout = () => {
  const [collapsed, setCollapsed] = useState(false)
  
  const setCollapse = (value) => {
    setCollapsed(value)
  }
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, isAdmin } = useAuth()
  const { pendingTransferConfirmCount, pendingApprovalCount } = useTransfer()

  const renderTransferLabel = () => {
    if (pendingTransferConfirmCount > 0) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          资产交接
          <Badge
            count={pendingTransferConfirmCount}
            size="small"
            color="#fa8c16"
            style={{
              backgroundColor: '#fa8c16',
              boxShadow: '0 0 0 1px #fff'
            }}
          />
        </span>
      )
    }
    return '资产交接'
  }

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '首页'
    },
    {
      key: '/assets',
      icon: <DatabaseOutlined />,
      label: '资产管理'
    },
    {
      key: '/transfers',
      icon: <SwapOutlined />,
      label: renderTransferLabel()
    },
    {
      key: '/returns',
      icon: <RollbackOutlined />,
      label: '资产退回'
    }
  ]

  const renderApprovalLabel = () => {
    if (pendingApprovalCount > 0) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          审批管理
          <Badge
            count={pendingApprovalCount}
            size="small"
            color="#fa8c16"
            style={{
              backgroundColor: '#fa8c16',
              boxShadow: '0 0 0 1px #fff'
            }}
          />
        </span>
      )
    }
    return '审批管理'
  }

  if (isAdmin) {
    menuItems.push(
      {
        key: '/users',
        icon: <UserOutlined />,
        label: '用户管理'
      },
      {
        key: '/approvals',
        icon: <CheckCircleOutlined />,
        label: renderApprovalLabel()
      },
      {
        key: '/safety-check-types',
        icon: <SafetyOutlined />,
        label: '检查类型管理'
      },
      {
        key: '/safety-check-tasks',
        icon: <FileTextOutlined />,
        label: '安全检查任务'
      }
    )
  } else {
    menuItems.push(
      {
        key: '/my-safety-check-tasks',
        icon: <CheckCircleOutlined />,
        label: '我的检查任务'
      }
    )
  }

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => {
        logout()
        navigate('/login')
      }
    }
  ]

  return (
    <AntLayout style={{ height: '100vh', overflow: 'hidden' }}>
      <Sider 
        collapsible 
        collapsed={collapsed} 
        onCollapse={setCollapse} 
        style={{ background: '#c41d3f', position: 'relative', height: '100vh', overflow: 'hidden' }}
        trigger={null}
        width={200}
      >
        <div style={{ height: 32, margin: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold' }}>
          {collapsed ? '资产' : '固定资产管理'}
        </div>
        <div style={{ flex: 1, overflow: 'auto', paddingBottom: 48, height: 'calc(100vh - 96px)' }}>
          <Menu
            theme="dark"
            selectedKeys={[location.pathname]}
            mode="inline"
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ background: '#c41d3f', borderRight: 'none' }}
          />
        </div>
        <div 
          className="custom-sider-trigger"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </div>
      </Sider>
      <AntLayout style={{ height: '100vh', overflow: 'hidden' }}>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', flexShrink: 0 }}>
          <Space>
            <span>欢迎，{user?.real_name}</span>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Avatar style={{ cursor: 'pointer' }} icon={<UserOutlined />} />
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ margin: '24px 16px', padding: 24, background: '#fff', overflow: 'auto', height: 'calc(100vh - 64px)' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}

export default Layout
