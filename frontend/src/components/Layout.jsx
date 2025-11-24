import React, { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, Avatar, Dropdown, Space } from 'antd'
import {
  DashboardOutlined,
  UserOutlined,
  DatabaseOutlined,
  SwapOutlined,
  RollbackOutlined,
  CheckCircleOutlined,
  LogoutOutlined
} from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'

const { Header, Sider, Content } = AntLayout

const Layout = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, isAdmin } = useAuth()

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
      label: '资产交接'
    },
    {
      key: '/returns',
      icon: <RollbackOutlined />,
      label: '资产退回'
    }
  ]

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
        label: '审批管理'
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
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{ height: 32, margin: 16, background: 'rgba(255, 255, 255, 0.3)', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold' }}>
          {collapsed ? '资产' : '固定资产管理'}
        </div>
        <Menu
          theme="dark"
          selectedKeys={[location.pathname]}
          mode="inline"
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          <Space>
            <span>欢迎，{user?.real_name}</span>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Avatar style={{ cursor: 'pointer' }} icon={<UserOutlined />} />
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ margin: '24px 16px', padding: 24, background: '#fff', minHeight: 280 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}

export default Layout


import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, Avatar, Dropdown, Space } from 'antd'
import {
  DashboardOutlined,
  UserOutlined,
  DatabaseOutlined,
  SwapOutlined,
  RollbackOutlined,
  CheckCircleOutlined,
  LogoutOutlined
} from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'

const { Header, Sider, Content } = AntLayout

const Layout = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, isAdmin } = useAuth()

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
      label: '资产交接'
    },
    {
      key: '/returns',
      icon: <RollbackOutlined />,
      label: '资产退回'
    }
  ]

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
        label: '审批管理'
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
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{ height: 32, margin: 16, background: 'rgba(255, 255, 255, 0.3)', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold' }}>
          {collapsed ? '资产' : '固定资产管理'}
        </div>
        <Menu
          theme="dark"
          selectedKeys={[location.pathname]}
          mode="inline"
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          <Space>
            <span>欢迎，{user?.real_name}</span>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Avatar style={{ cursor: 'pointer' }} icon={<UserOutlined />} />
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ margin: '24px 16px', padding: 24, background: '#fff', minHeight: 280 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}

export default Layout




