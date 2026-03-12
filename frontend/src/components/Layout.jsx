import React, { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, Avatar, Dropdown, Space, Badge, Modal, Form, Input, message } from 'antd'
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
  FileTextOutlined,
  LockOutlined
} from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'
import { useTransfer } from '../contexts/TransferContext'
import api from '../utils/api'

const { Header, Sider, Content } = AntLayout

const ORANGE_BADGE_STYLE = { backgroundColor: '#fa8c16', boxShadow: '0 0 0 1px #fff' }

function SidebarSafetyCheckLabel() {
  const { pendingSafetyCheckCount } = useTransfer()
  if (pendingSafetyCheckCount > 0) {
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        我的检查任务
        <Badge
          count={pendingSafetyCheckCount}
          size="small"
          color="#fa8c16"
          style={ORANGE_BADGE_STYLE}
        />
      </span>
    )
  }
  return '我的检查任务'
}

const Layout = () => {
  const [collapsed, setCollapsed] = useState(false)
  const [passwordModalVisible, setPasswordModalVisible] = useState(false)
  const [passwordForm] = Form.useForm()
  const [passwordSubmitting, setPasswordSubmitting] = useState(false)

  const setCollapse = (value) => {
    setCollapsed(value)
  }
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, isAdmin, isLeader } = useAuth()

  const handlePasswordSubmit = async () => {
    try {
      const values = await passwordForm.validateFields()
      if (values.new_password !== values.confirm_password) {
        message.error('两次输入的新密码不一致')
        return
      }
      setPasswordSubmitting(true)
      await api.put('/users/me/password', {
        old_password: values.old_password,
        new_password: values.new_password
      })
      message.success('密码修改成功')
      setPasswordModalVisible(false)
      passwordForm.resetFields()
    } catch (error) {
      if (error.response?.status === 400 && error.response?.data?.detail === '原密码错误') {
        message.error('原密码错误')
      } else {
        message.error(error.response?.data?.detail || '修改失败')
      }
    } finally {
      setPasswordSubmitting(false)
    }
  }
  const { pendingTransferConfirmCount, pendingApprovalCount, pendingSafetyCheckCount } = useTransfer()

  // 与资产交接同一套：有数量时显示小橙点 Badge（#fa8c16）
  const renderLabelWithOrangeBadge = (label, count) => {
    if (count > 0) {
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          {label}
          <Badge
            count={count}
            size="small"
            color="#fa8c16"
            style={{ backgroundColor: '#fa8c16', boxShadow: '0 0 0 1px #fff' }}
          />
        </span>
      )
    }
    return label
  }

  const renderTransferLabel = () => renderLabelWithOrangeBadge('资产交接', pendingTransferConfirmCount)

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

  const renderApprovalLabel = () => renderLabelWithOrangeBadge('审批管理', pendingApprovalCount)

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
        key: '/my-safety-check-tasks',
        icon: <CheckCircleOutlined />,
        label: <SidebarSafetyCheckLabel />
      },
      {
        key: '/safety-check-tasks',
        icon: <FileTextOutlined />,
        label: '检查任务管理'
      }
    )
  } else {
    menuItems.push({
      key: '/my-safety-check-tasks',
      icon: <CheckCircleOutlined />,
      label: <SidebarSafetyCheckLabel />
    })
    if (isLeader) {
      menuItems.push({
        key: '/safety-check-tasks',
        icon: <FileTextOutlined />,
        label: '安全检查任务'
      })
    }
  }

  const userMenuItems = [
    {
      key: 'password',
      icon: <LockOutlined />,
      label: '修改密码',
      onClick: () => {
        passwordForm.resetFields()
        setPasswordModalVisible(true)
      }
    },
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
        <div style={{ flex: 1, overflow: 'auto', paddingBottom: 48, height: 'calc(100vh - 96px)' }} className="sider-menu-wrap">
          <Menu
            key={`badge-${pendingTransferConfirmCount}-${pendingApprovalCount}-${pendingSafetyCheckCount}`}
            theme="dark"
            selectedKeys={[location.pathname]}
            mode="inline"
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ background: '#c41d3f', borderRight: 'none', overflow: 'visible' }}
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

      <Modal
        title="修改密码"
        open={passwordModalVisible}
        onCancel={() => { setPasswordModalVisible(false); passwordForm.resetFields() }}
        onOk={handlePasswordSubmit}
        confirmLoading={passwordSubmitting}
        destroyOnClose
      >
        <Form form={passwordForm} layout="vertical">
          <Form.Item name="old_password" label="原密码" rules={[{ required: true, message: '请输入原密码' }]}>
            <Input.Password placeholder="请输入原密码" />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, message: '请输入新密码' }, { min: 6, message: '至少6位' }]}>
            <Input.Password placeholder="请输入新密码（至少6位）" />
          </Form.Item>
          <Form.Item name="confirm_password" label="确认新密码" rules={[{ required: true, message: '请再次输入新密码' }]}>
            <Input.Password placeholder="请再次输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </AntLayout>
  )
}

export default Layout
