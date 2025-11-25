import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Space, Popconfirm, Row, Col } from 'antd'
import { PlusOutlined, CloseCircleOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import api from '../utils/api'
import { useAuth } from '../contexts/AuthContext'

const { Option } = Select

const TransferManagement = () => {
  const { user: currentUser } = useAuth()
  const [transfers, setTransfers] = useState([])
  const [assets, setAssets] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()
  const [filtersForm] = Form.useForm()
  const [filters, setFilters] = useState({})

  useEffect(() => {
    fetchTransfers()
    fetchUsers()
  }, [])

  useEffect(() => {
    // 等待当前用户信息加载完成后再获取资产
    if (currentUser) {
      fetchAssets()
    }
  }, [currentUser])

  const fetchTransfers = async (extraFilters) => {
    setLoading(true)
    try {
      const params = { ...filters, ...(extraFilters || {}) }
      const response = await api.get('/transfers/', { params })
      setTransfers(response.data)
    } catch (error) {
      message.error('获取交接申请列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    const values = filtersForm.getFieldsValue()
    const payload = {
      search: values.keyword || undefined,
      status: values.status || undefined
    }
    setFilters(payload)
    fetchTransfers(payload)
  }

  const handleResetFilters = () => {
    filtersForm.resetFields()
    setFilters({})
    fetchTransfers({})
  }

  const fetchAssets = async () => {
    if (!currentUser) return
    try {
      const params = { status: '在用' }
      // 不再传递user_id参数，因为后端已经允许所有用户查看全部资产
      // 普通用户只能交接自己名下的资产，这个限制在提交时由后端检查
      const response = await api.get('/assets/', { params })
      setAssets(response.data)
    } catch (error) {
      console.error('获取资产列表失败:', error)
      message.error('获取资产列表失败，请刷新页面重试')
    }
  }

  const fetchUsers = async () => {
    try {
      const response = await api.get('/users/')
      setUsers(response.data)
    } catch (error) {
      console.error('获取用户列表失败:', error)
      message.error('获取用户列表失败，请刷新页面重试')
    }
  }

  const handleAdd = () => {
    form.resetFields()
    setModalVisible(true)
  }

  const handleSubmit = async (values) => {
    try {
      await api.post('/transfers/', values)
      message.success('交接申请已提交')
      setModalVisible(false)
      fetchTransfers()
    } catch (error) {
      message.error(error.response?.data?.detail || '提交失败')
    }
  }

  const handleCancel = async (requestId) => {
    try {
      await api.delete(`/transfers/${requestId}`)
      message.success('申请已撤回')
      fetchTransfers()
    } catch (error) {
      message.error(error.response?.data?.detail || '撤回失败')
    }
  }

  const getStatusTag = (status) => {
    const statusMap = {
      pending: { color: 'orange', text: '待审批' },
      approved: { color: 'green', text: '已批准' },
      rejected: { color: 'red', text: '已拒绝' }
    }
    const statusInfo = statusMap[status] || { color: 'default', text: status }
    return <span style={{ color: statusInfo.color }}>{statusInfo.text}</span>
  }

  const columns = [
    {
      title: '资产编号',
      dataIndex: ['asset', 'asset_number'],
      key: 'asset_number'
    },
    {
      title: '资产名称',
      dataIndex: ['asset', 'name'],
      key: 'asset_name'
    },
    {
      title: '转出人',
      dataIndex: ['from_user', 'real_name'],
      key: 'from_user'
    },
    {
      title: '转入人',
      dataIndex: ['to_user', 'real_name'],
      key: 'to_user'
    },
    {
      title: '交接原因',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: getStatusTag
    },
    {
      title: '审批意见',
      dataIndex: 'approval_comment',
      key: 'approval_comment',
      ellipsis: true,
      render: (text) => text || '-'
    },
    {
      title: '申请时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) => text ? new Date(text).toLocaleString('zh-CN') : '-'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => {
        // 只有转出用户可以对pending状态的申请进行撤回
        const canCancel = record.status === 'pending' && 
                         (currentUser?.role === 'admin' || record.from_user_id === currentUser?.id)
        
        return (
          <Space>
            {canCancel && (
              <Popconfirm
                title="确定要撤回此申请吗？"
                onConfirm={() => handleCancel(record.id)}
                okText="确定"
                cancelText="取消"
              >
                <Button 
                  type="link" 
                  danger 
                  icon={<CloseCircleOutlined />}
                  size="small"
                >
                  撤回
                </Button>
              </Popconfirm>
            )}
          </Space>
        )
      }
    }
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h1>资产交接</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          申请交接
        </Button>
      </div>

      {/* 查询表单 */}
      <Form
        form={filtersForm}
        layout="inline"
        style={{ marginBottom: 16, padding: 16, background: '#fafafa', borderRadius: 4 }}
        onFinish={handleSearch}
      >
        <Form.Item label="关键字" name="keyword">
          <Input
            placeholder="搜索资产编号、名称、转出人、转入人、交接原因等"
            style={{ width: 300 }}
            allowClear
          />
        </Form.Item>
        <Form.Item label="状态" name="status">
          <Select placeholder="全部" style={{ width: 120 }} allowClear>
            <Option value="pending">待审批</Option>
            <Option value="approved">已批准</Option>
            <Option value="rejected">已拒绝</Option>
          </Select>
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" icon={<SearchOutlined />} htmlType="submit">
              查询
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleResetFilters}>
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>

      <Table
        columns={columns}
        dataSource={transfers}
        loading={loading}
        rowKey="id"
      />

      <Modal
        title="申请资产交接"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            label="资产"
            name="asset_id"
            rules={[{ required: true, message: '请选择资产' }]}
          >
            <Select>
              {assets.map(asset => (
                <Option key={asset.id} value={asset.id}>
                  {asset.asset_number} - {asset.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="转入用户"
            name="to_user_id"
            rules={[{ required: true, message: '请选择转入用户' }]}
          >
            <Select>
              {users
                .filter(user => user.id !== currentUser?.id && user.ehr_number !== '1000000') // 过滤掉当前用户和仓库用户
                .map(user => (
                  <Option key={user.id} value={user.id}>
                    {user.real_name} ({user.ehr_number})
                  </Option>
                ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="交接原因"
            name="reason"
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default TransferManagement

