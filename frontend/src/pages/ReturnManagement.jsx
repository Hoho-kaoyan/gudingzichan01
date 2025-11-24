import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Space, Divider } from 'antd'
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import api from '../utils/api'
import { useAuth } from '../contexts/AuthContext'

const { Option } = Select
const { TextArea } = Input

const ReturnManagement = () => {
  const { user: currentUser } = useAuth()
  const [returns, setReturns] = useState([])
  const [assets, setAssets] = useState([])
  const [users, setUsers] = useState([])
  const [selectedAsset, setSelectedAsset] = useState(null)
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()
  const [filtersForm] = Form.useForm()
  const [filters, setFilters] = useState({})

  useEffect(() => {
    fetchReturns()
    fetchAssets()
    fetchUsers()
  }, [])

  const fetchReturns = async (extraFilters) => {
    setLoading(true)
    try {
      const params = { ...filters, ...(extraFilters || {}) }
      const response = await api.get('/returns/', { params })
      setReturns(response.data)
    } catch (error) {
      message.error('获取退回申请列表失败')
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
    fetchReturns(payload)
  }

  const handleResetFilters = () => {
    filtersForm.resetFields()
    setFilters({})
    fetchReturns({})
  }

  const fetchAssets = async () => {
    try {
      const response = await api.get('/assets/', { params: { status: '在用' } })
      setAssets(response.data)
    } catch (error) {
      console.error('获取资产列表失败:', error)
      message.error('获取资产列表失败')
    }
  }

  const fetchUsers = async () => {
    try {
      const response = await api.get('/users/')
      setUsers(response.data || [])
    } catch (error) {
      console.error('获取用户列表失败:', error)
      message.error('获取用户列表失败')
    }
  }

  const handleAdd = () => {
    form.resetFields()
    setSelectedAsset(null)
    setModalVisible(true)
  }

  const handleAssetChange = (assetId) => {
    const asset = assets.find(a => a.id === assetId)
    setSelectedAsset(asset)
    if (asset) {
      // 预填充当前资产的值
      form.setFieldsValue({
        mac_address: asset.mac_address || '',
        ip_address: asset.ip_address || '',
        office_location: asset.office_location || '',
        floor: asset.floor || '',
        seat_number: asset.seat_number || '',
        new_user_id: undefined,
        remark: asset.remark || ''
      })
    }
  }

  const handleSubmit = async (values) => {
    try {
      const payload = {
        asset_id: values.asset_id,
        reason: values.reason || undefined
      }
      
      if (selectedAsset) {
        // 只提交与当前值不同的字段，空字符串转为null
        const normalizeValue = (val) => (val === '' || val === undefined) ? null : val
        
        if (normalizeValue(values.mac_address) !== (selectedAsset.mac_address || null)) {
          payload.mac_address = normalizeValue(values.mac_address)
        }
        if (normalizeValue(values.ip_address) !== (selectedAsset.ip_address || null)) {
          payload.ip_address = normalizeValue(values.ip_address)
        }
        if (normalizeValue(values.office_location) !== (selectedAsset.office_location || null)) {
          payload.office_location = normalizeValue(values.office_location)
        }
        if (normalizeValue(values.floor) !== (selectedAsset.floor || null)) {
          payload.floor = normalizeValue(values.floor)
        }
        if (normalizeValue(values.seat_number) !== (selectedAsset.seat_number || null)) {
          payload.seat_number = normalizeValue(values.seat_number)
        }
        if (values.new_user_id !== undefined && values.new_user_id !== selectedAsset.user_id) {
          payload.new_user_id = values.new_user_id || null
        }
        if (normalizeValue(values.remark) !== (selectedAsset.remark || null)) {
          payload.remark = normalizeValue(values.remark)
        }
      }
      
      await api.post('/returns/', payload)
      message.success('退回申请已提交')
      setModalVisible(false)
      setSelectedAsset(null)
      fetchReturns(filters)
    } catch (error) {
      message.error(error.response?.data?.detail || '提交失败')
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
      title: '退回人',
      dataIndex: ['user', 'real_name'],
      key: 'user'
    },
    {
      title: '退回原因',
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
    }
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h1>资产退回</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          申请退回
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
            placeholder="搜索资产编号、名称、退回人、退回原因等"
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
        dataSource={returns}
        loading={loading}
        rowKey="id"
      />

      <Modal
        title="申请资产退回仓库"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false)
          setSelectedAsset(null)
        }}
        onOk={() => form.submit()}
        width={700}
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
            <Select 
              placeholder="请选择要退回的资产"
              onChange={handleAssetChange}
            >
              {assets.map(asset => (
                <Option key={asset.id} value={asset.id}>
                  {asset.asset_number} - {asset.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            label="退回原因"
            name="reason"
          >
            <TextArea rows={3} placeholder="请输入退回原因（可选）" />
          </Form.Item>

          <Divider orientation="left" style={{ margin: '16px 0' }}>
            <span style={{ fontSize: '14px', color: '#666' }}>可修改资产信息（可选）</span>
          </Divider>
          <div style={{ marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 4, fontSize: '13px', color: '#666' }}>
            提示：您可以在退回时修改以下资产信息。如不修改，审批通过后资产将退回仓库。
          </div>

          <Form.Item
            label="MAC地址"
            name="mac_address"
          >
            <Input placeholder="如不修改请留空" />
          </Form.Item>

          <Form.Item
            label="IP地址"
            name="ip_address"
          >
            <Input placeholder="如不修改请留空" />
          </Form.Item>

          <Form.Item
            label="存放地点"
            name="office_location"
          >
            <Input placeholder="如不修改请留空" />
          </Form.Item>

          <Form.Item
            label="存放楼层"
            name="floor"
          >
            <Input placeholder="如不修改请留空" />
          </Form.Item>

          <Form.Item
            label="座位号"
            name="seat_number"
          >
            <Input placeholder="如不修改请留空" />
          </Form.Item>

          <Form.Item
            label="保管人"
            name="new_user_id"
            tooltip="如指定新的保管人，审批通过后资产将转给该保管人；如不指定，资产将退回仓库"
          >
            <Select 
              placeholder="选择新的保管人（可选，不选则退回仓库）"
              allowClear
              showSearch
              filterOption={(input, option) =>
                (option?.children ?? '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {users
                .filter(user => user.ehr_number !== '1000000') // 过滤掉仓库用户
                .map(user => (
                  <Option key={user.id} value={user.id}>
                    {user.real_name} ({user.ehr_number}) - {user.group}
                  </Option>
                ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="备注说明"
            name="remark"
          >
            <TextArea rows={3} placeholder="如不修改请留空" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ReturnManagement

