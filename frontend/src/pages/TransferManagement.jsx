import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Space, Popconfirm, Row, Col, Tag, AutoComplete } from 'antd'
import { PlusOutlined, CloseCircleOutlined, SearchOutlined, ReloadOutlined, CheckCircleOutlined } from '@ant-design/icons'
import api from '../utils/api'
import { useAuth } from '../contexts/AuthContext'
import { useTransfer } from '../contexts/TransferContext'

const { Option } = Select

const TransferManagement = () => {
  const { user: currentUser, isAdmin } = useAuth()
  const { refreshPendingConfirmations, refreshPendingApprovals } = useTransfer()
  const [transfers, setTransfers] = useState([])
  const [assets, setAssets] = useState([])
  const [userOptions, setUserOptions] = useState([])
  const [toUserSearchValue, setToUserSearchValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [confirmModalVisible, setConfirmModalVisible] = useState(false)
  const [currentTransfer, setCurrentTransfer] = useState(null)
  const [form] = Form.useForm()
  const selectedToUserId = Form.useWatch('to_user_id', form)
  const [confirmForm] = Form.useForm()
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
      const options = (response.data || []).map(user => ({
        label: `${user.real_name} (${user.ehr_number}) - ${user.group || '未分组'}`,
        value: user.id,
        ehrNumber: user.ehr_number
      }))
      setUserOptions(options)
    } catch (error) {
      console.error('获取用户列表失败:', error)
      message.error('获取用户列表失败，请刷新页面重试')
    }
  }

  const handleAdd = () => {
    form.resetFields()
    setToUserSearchValue('')
    setModalVisible(true)
  }

  const handleSubmit = async (values) => {
    try {
      await api.post('/transfers/', values)
      message.success('交接申请已提交')
      setModalVisible(false)
      fetchTransfers()
      // 刷新侧边栏的待确认数量（如果当前用户是转入人）
      refreshPendingConfirmations()
    } catch (error) {
      message.error(error.response?.data?.detail || '提交失败')
    }
  }

  const handleCancel = async (requestId) => {
    try {
      await api.delete(`/transfers/${requestId}`)
      message.success('申请已撤回')
      fetchTransfers()
      // 刷新侧边栏的待确认数量
      refreshPendingConfirmations()
    } catch (error) {
      message.error(error.response?.data?.detail || '撤回失败')
    }
  }

  const handleConfirm = (record) => {
    setCurrentTransfer(record)
    confirmForm.resetFields()
    setConfirmModalVisible(true)
  }

  const handleConfirmSubmit = async (values) => {
    try {
      const confirmed = values.action === 'confirm'
      await api.post(`/transfers/${currentTransfer.id}/confirm`, {
        confirmed,
        comment: values.comment
      })
      message.success(confirmed ? '已确认交接申请' : '已拒绝交接申请')
      setConfirmModalVisible(false)
      setCurrentTransfer(null)
      fetchTransfers()
      // 刷新侧边栏的待确认数量
      refreshPendingConfirmations()
      // 如果确认了，也会影响待审批数量（转入人确认后进入待审批状态）
      if (confirmed) {
        refreshPendingApprovals()
      }
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const getStatusTag = (status) => {
    const statusMap = {
      waiting_confirmation: { color: '#1677ff', text: '待转入人确认', icon: '⏳' },
      pending: { color: '#faad14', text: '待审批', icon: '⏰' },
      approved: { color: '#52c41a', text: '已批准', icon: '✓' },
      rejected: { color: '#722ed1', text: '已拒绝', icon: '✗' },
      confirmation_rejected: { color: '#ff4d4f', text: '转入人已拒绝', icon: '✗' }
    }
    const statusInfo = statusMap[status] || { color: '#d9d9d9', text: status || '未知', icon: '' }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', maxWidth: 160 }}>
        <Tag
          color={statusInfo.color}
          style={{
            marginBottom: 4,
            whiteSpace: 'normal',
            wordBreak: 'break-word',
            padding: '2px 8px',
            lineHeight: 1.4
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            {statusInfo.icon && <span>{statusInfo.icon}</span>}
            <span>{statusInfo.text}</span>
          </span>
        </Tag>
      </div>
    )
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
      width: 180,
      render: getStatusTag
    },
    {
      title: '转入人意见',
      key: 'to_user_confirm',
      width: 200,
      render: (_, record) => {
        // 待确认
        if (record.to_user_confirmed === null || record.to_user_confirmed === undefined) {
          return <Tag color="default">待确认</Tag>
        }
        // 已确认
        if (record.to_user_confirmed === 1) {
          return (
            <div>
              <Tag color="success" style={{ marginBottom: 4 }}>✓ 已确认</Tag>
              {record.to_user_confirm_comment && (
                <div style={{ color: '#666', fontSize: '12px', marginTop: 4, wordBreak: 'break-word' }}>
                  {record.to_user_confirm_comment}
                </div>
              )}
              {record.to_user_confirmed_at && (
                <div style={{ color: '#999', fontSize: '11px', marginTop: 2 }}>
                  {new Date(record.to_user_confirmed_at).toLocaleString('zh-CN')}
                </div>
              )}
            </div>
          )
        }
        // 已拒绝
        if (record.to_user_confirmed === 0) {
          return (
            <div>
              <Tag color="error" style={{ marginBottom: 4 }}>✗ 已拒绝</Tag>
              {record.to_user_confirm_comment && (
                <div style={{ color: '#666', fontSize: '12px', marginTop: 4, wordBreak: 'break-word' }}>
                  {record.to_user_confirm_comment}
                </div>
              )}
              {record.to_user_confirmed_at && (
                <div style={{ color: '#999', fontSize: '11px', marginTop: 2 }}>
                  {new Date(record.to_user_confirmed_at).toLocaleString('zh-CN')}
                </div>
              )}
            </div>
          )
        }
        return '-'
      }
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
        const isToUser = record.to_user_id === currentUser?.id
        const isFromUser = record.from_user_id === currentUser?.id
        const isAdmin = currentUser?.role === 'admin'
        
        // 转入人可以确认或拒绝待确认的申请
        const canConfirm = isToUser && record.status === 'waiting_confirmation'
        
        // 转出用户或管理员可以撤回待确认或待审批的申请
        const canCancel = (isFromUser || isAdmin) && 
                         (record.status === 'waiting_confirmation' || record.status === 'pending')
        
        return (
          <Space>
            {canConfirm && (
              <Button 
                type="link" 
                icon={<CheckCircleOutlined />}
                size="small"
                onClick={() => handleConfirm(record)}
              >
                确认
              </Button>
            )}
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

  const selectableAssets = isAdmin ? assets : assets.filter((asset) => asset.user?.id === currentUser?.id)

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
          <Select placeholder="全部" style={{ width: 150 }} allowClear>
            <Option value="waiting_confirmation">待转入人确认</Option>
            <Option value="pending">待审批</Option>
            <Option value="approved">已批准</Option>
            <Option value="rejected">已拒绝</Option>
            <Option value="confirmation_rejected">转入人已拒绝</Option>
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
            <Select placeholder={isAdmin ? '请选择资产' : '请选择自己名下的资产'}>
              {selectableAssets.map((asset) => (
                <Option key={asset.id} value={asset.id}>
                  {asset.asset_number} - {asset.name}
                </Option>
              ))}
              {!isAdmin && selectableAssets.length === 0 && (
                <Option disabled value="">
                  暂无可交接资产
                </Option>
              )}
            </Select>
          </Form.Item>
          <Form.Item
            label="转入用户"
            required
          >
            <AutoComplete
              value={toUserSearchValue}
              options={userOptions
                .filter(option => option.value !== currentUser?.id && option.ehrNumber !== '1000000')
                .filter(option => option.label.toLowerCase().includes((toUserSearchValue || '').toLowerCase()))
                .slice(0, 5)
                .map(option => ({
                  value: option.label,
                  userId: option.value
                }))
              }
              placeholder="请输入转入人姓名或EHR号"
              onSearch={(value) => {
                setToUserSearchValue(value)
              }}
              onSelect={(value, option) => {
                const selectedOption = userOptions.find(item => item.label === value)
                if (selectedOption) {
                  setToUserSearchValue(value)
                  form.setFieldsValue({ to_user_id: selectedOption.value })
                }
              }}
              onChange={(value) => {
                setToUserSearchValue(value)
                form.setFieldsValue({ to_user_id: null })
              }}
              allowClear
              notFoundContent={toUserSearchValue ? '无匹配用户' : null}
            />
            <Form.Item
              name="to_user_id"
              rules={[{ required: true, message: '请选择转入用户' }]}
              style={{ display: 'none' }}
            >
              <Input />
            </Form.Item>
            {toUserSearchValue &&
              !selectedToUserId &&
              !userOptions.some(option => option.label === toUserSearchValue) && (
                <div style={{ color: '#ff4d4f', marginTop: 4, fontSize: 12 }}>
                  此用户不存在
                </div>
            )}
          </Form.Item>
          <Form.Item
            label="交接原因"
            name="reason"
          >
            <Input.TextArea rows={4} />
          </Form.Item>
          </Form>
        </Modal>

        {/* 转入人确认弹窗 */}
        <Modal
          title="确认资产交接"
          open={confirmModalVisible}
          onCancel={() => {
            setConfirmModalVisible(false)
            setCurrentTransfer(null)
          }}
          footer={null}
        >
          {currentTransfer && (
            <div style={{ marginBottom: 16 }}>
              <p><strong>资产编号：</strong>{currentTransfer.asset?.asset_number}</p>
              <p><strong>资产名称：</strong>{currentTransfer.asset?.name}</p>
              <p><strong>转出人：</strong>{currentTransfer.from_user?.real_name}</p>
              <p><strong>交接原因：</strong>{currentTransfer.reason || '无'}</p>
            </div>
          )}
          <Form
            form={confirmForm}
            layout="vertical"
            onFinish={handleConfirmSubmit}
          >
            <Form.Item
              label="操作"
              name="action"
              rules={[{ required: true, message: '请选择操作' }]}
            >
              <Select>
                <Option value="confirm">确认接收</Option>
                <Option value="reject">拒绝接收</Option>
              </Select>
            </Form.Item>
            <Form.Item
              label="备注"
              name="comment"
            >
              <Input.TextArea rows={4} placeholder="请输入确认备注（可选）" />
            </Form.Item>
            <Form.Item>
              <Space>
                <Button onClick={() => {
                  setConfirmModalVisible(false)
                  setCurrentTransfer(null)
                }}>
                  取消
                </Button>
                <Button type="primary" htmlType="submit">
                  提交
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>
      </div>
    )
  }
  
  export default TransferManagement

