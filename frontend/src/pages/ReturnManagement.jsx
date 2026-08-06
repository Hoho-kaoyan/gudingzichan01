import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Button, Modal, Form, Input, Select, message, Space, Divider } from 'antd'
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import api from '../utils/api'
import { formatEast8 } from '../utils/datetime'
import { useAuth } from '../contexts/AuthContext'
import { parseSafetyCheckError } from '../utils/safetyCheckError'

const { Option } = Select
const { TextArea } = Input

const MY_TASKS_PATH = '/my-safety-check-tasks'

const ReturnManagement = () => {
  const navigate = useNavigate()
  const { user: currentUser, isAdmin, isLeader, isAdminOrLeader } = useAuth()
  const [returns, setReturns] = useState([])
  const [assets, setAssets] = useState([])
  const [selectedAsset, setSelectedAsset] = useState(null)
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()
  const [filtersForm] = Form.useForm()
  const [filters, setFilters] = useState({})

  useEffect(() => {
    fetchReturns()
    fetchAssets()
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

  const handleAdd = () => {
    form.resetFields()
    setSelectedAsset(null)
    setModalVisible(true)
  }

  const handleAssetsChange = (assetIds) => {
    // v5.1 批量退回：多选资产时预填第一件的字段（如用户不修改则视为不修改）
    if (assetIds && assetIds.length > 0) {
      const firstAsset = assets.find(a => a.id === assetIds[0])
      setSelectedAsset(firstAsset || null)
      if (firstAsset) {
        form.setFieldsValue({
          mac_address: firstAsset.mac_address || '',
          ip_address: firstAsset.ip_address || '',
          office_location: firstAsset.office_location || '',
          floor: firstAsset.floor || '',
          seat_number: firstAsset.seat_number || '',
          remark: firstAsset.remark || ''
        })
      }
    } else {
      setSelectedAsset(null)
    }
  }

  const handleSubmit = async (values) => {
    try {
      // v5.1 批量退回：前端字段名从 asset_id 改成 asset_ids（数组）
      const payload = {
        asset_ids: values.asset_ids,
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
        if (normalizeValue(values.remark) !== (selectedAsset.remark || null)) {
          payload.remark = normalizeValue(values.remark)
        }
      }

      await api.post('/returns/', payload)
      // v5.1 批量退回：后端返回 List，根据数量提示
      const cnt = (values.asset_ids || []).length
      message.success(`已提交 ${cnt} 件资产的退回申请,待管理员审批`)
      setModalVisible(false)
      setSelectedAsset(null)
      fetchReturns(filters)
    } catch (error) {
      const { isSafetyCheck, message: msg } = parseSafetyCheckError(error)
      if (isSafetyCheck) {
        Modal.warning({
          title: '需要先完成数据安全检查',
          content: msg,
          okText: '前往我的检查任务',
          onOk: () => navigate(MY_TASKS_PATH)
        })
      } else {
        message.error(msg)
      }
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
      key: 'asset_number',
      width: 96
    },
    {
      title: '资产名称',
      dataIndex: ['asset', 'name'],
      key: 'asset_name',
      width: 100
    },
    {
      title: '退回人',
      dataIndex: ['user', 'real_name'],
      key: 'user',
      width: 88
    },
    {
      title: '退回原因',
      dataIndex: 'reason',
      key: 'reason',
      width: 100,
      ellipsis: true
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 88,
      render: getStatusTag
    },
    {
      title: '审批意见',
      dataIndex: 'approval_comment',
      key: 'approval_comment',
      width: 100,
      ellipsis: true,
      render: (text) => text || '-'
    },
    {
      title: '申请时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (text) => text ? formatEast8(text) : '-'
    }
  ]

  // 可选资产逻辑：
  // 1. 管理员：全量在用资产
  // 2. 组长：所属组的所有在用资产
  // 3. 普通用户：仅个人名下的在用资产
  const selectableAssets = isAdmin
    ? assets
    : isLeader
      ? assets.filter(asset => asset.user_group === currentUser?.group)
      : assets.filter(asset => asset.user?.id === currentUser?.id)

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
        scroll={{ x: 692 }}
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
            label="资产（可多选，v5.1 批量退回）"
            name="asset_ids"
            rules={[{ required: true, message: '请至少选择一件资产' }, {
              validator: (_, v) => (v && v.length >= 1) ? Promise.resolve() : Promise.reject(new Error('请至少选择一件资产'))
            }]}
          >
            <Select
              mode="multiple"
              placeholder={isAdmin ? '请选择要退回的资产（可多选）' : '请选择自己名下的资产（可多选）'}
              onChange={handleAssetsChange}
              maxTagCount="responsive"
            >
              {selectableAssets.map(asset => (
                <Option key={asset.id} value={asset.id}>
                  {asset.asset_number} - {asset.name}
                </Option>
              ))}
              {!isAdmin && selectableAssets.length === 0 && (
                <Option disabled value="">
                  暂无可退回资产
                </Option>
              )}
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
