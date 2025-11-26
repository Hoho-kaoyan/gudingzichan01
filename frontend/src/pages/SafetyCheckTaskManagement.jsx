import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, DatePicker, message, Popconfirm, Space, Steps, Card, Tag, Checkbox } from 'antd'
import { PlusOutlined, EyeOutlined, CloseOutlined } from '@ant-design/icons'
import api from '../utils/api'
import { useAuth } from '../contexts/AuthContext'
import dayjs from 'dayjs'

const { TextArea } = Input
const { RangePicker } = DatePicker

const SafetyCheckTaskManagement = () => {
  const { isAdmin } = useAuth()
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [createStep, setCreateStep] = useState(0)
  const [checkTypes, setCheckTypes] = useState([])
  const [categories, setCategories] = useState([])
  const [assets, setAssets] = useState([])
  const [selectedAssets, setSelectedAssets] = useState([])
  const [assetFilters, setAssetFilters] = useState({})
  const [form] = Form.useForm()
  const [filterForm] = Form.useForm()

  useEffect(() => {
    if (isAdmin) {
      fetchTasks()
      fetchCheckTypes()
      fetchCategories()
    }
  }, [isAdmin])

  const fetchTasks = async (filters = {}) => {
    setLoading(true)
    try {
      const params = { ...filters, page: 1, limit: 100 }
      const response = await api.get('/safety-check-tasks/', { params })
      setTasks(response.data.items || [])
    } catch (error) {
      message.error('获取任务列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchCheckTypes = async () => {
    try {
      const response = await api.get('/safety-check-types/')
      const activeTypes = response.data.filter(type => type.is_active)
      setCheckTypes(activeTypes)
    } catch (error) {
      message.error('获取检查类型失败')
    }
  }

  const fetchCategories = async () => {
    try {
      const response = await api.get('/categories/')
      setCategories(response.data)
    } catch (error) {
      console.error('获取资产大类失败:', error)
    }
  }

  const fetchAssets = async (filters = {}) => {
    try {
      const params = { ...filters, limit: 1000 }
      const response = await api.get('/assets/', { params })
      // 只显示有使用人的资产
      const assetsWithUsers = response.data.filter(asset => asset.user_id)
      setAssets(assetsWithUsers)
    } catch (error) {
      message.error('获取资产列表失败')
    }
  }

  const handleCreate = () => {
    setCreateStep(0)
    setSelectedAssets([])
    form.resetFields()
    filterForm.resetFields()
    setAssetFilters({})
    setModalVisible(true)
    fetchAssets()
  }

  const handleNext = async () => {
    if (createStep === 0) {
      // 验证检查类型和资产选择
      const values = form.getFieldsValue()
      if (!values.check_type_id) {
        message.error('请选择检查类型')
        return
      }
      if (selectedAssets.length === 0) {
        message.error('请至少选择一个资产')
        return
      }
      setCreateStep(1)
    } else if (createStep === 1) {
      // 验证任务信息
      try {
        await form.validateFields(['title'])
        setCreateStep(2)
      } catch (error) {
        message.error('请填写任务标题')
      }
    }
  }

  const handlePrev = () => {
    setCreateStep(createStep - 1)
  }

  const handleSubmit = async () => {
    try {
      const values = form.getFieldsValue()
      const payload = {
        check_type_id: values.check_type_id,
        title: values.title,
        description: values.description,
        asset_ids: selectedAssets.map(a => a.id),
        deadline: values.deadline ? values.deadline.toISOString() : null
      }
      await api.post('/safety-check-tasks/', payload)
      message.success('任务创建成功')
      setModalVisible(false)
      fetchTasks()
    } catch (error) {
      message.error(error.response?.data?.detail || '创建任务失败')
    }
  }

  const handleCancel = async (taskId) => {
    try {
      await api.delete(`/safety-check-tasks/${taskId}`)
      message.success('任务已取消')
      fetchTasks()
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const handleViewDetail = async (taskId) => {
    // 可以打开详情弹窗或跳转到详情页
    message.info('查看任务详情功能待实现')
  }

  const handleAssetSearch = () => {
    const values = filterForm.getFieldsValue()
    const filters = {
      category_id: values.category_id,
      status: values.status,
      search: values.search
    }
    setAssetFilters(filters)
    fetchAssets(filters)
  }

  const handleAssetSelect = (asset, checked) => {
    if (checked) {
      setSelectedAssets([...selectedAssets, asset])
    } else {
      setSelectedAssets(selectedAssets.filter(a => a.id !== asset.id))
    }
  }

  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedAssets([...assets])
    } else {
      setSelectedAssets([])
    }
  }

  const columns = [
    {
      title: '任务编号',
      dataIndex: 'task_number',
      key: 'task_number',
      width: 150
    },
    {
      title: '任务标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true
    },
    {
      title: '检查类型',
      key: 'check_type',
      width: 150,
      render: (_, record) => record.check_type?.name || '-'
    },
    {
      title: '进度',
      key: 'progress',
      width: 150,
      render: (_, record) => {
        const total = record.total_assets || 0
        const completed = record.completed_assets || 0
        const percent = total > 0 ? Math.round((completed / total) * 100) : 0
        return `${completed}/${total} (${percent}%)`
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const statusMap = {
          pending: { text: '进行中', color: 'processing' },
          completed: { text: '已完成', color: 'success' },
          overdue: { text: '已逾期', color: 'error' },
          cancelled: { text: '已取消', color: 'default' }
        }
        const config = statusMap[status] || { text: status, color: 'default' }
        return <Tag color={config.color}>{config.text}</Tag>
      }
    },
    {
      title: '截止时间',
      dataIndex: 'deadline',
      key: 'deadline',
      width: 180,
      render: (deadline) => deadline ? dayjs(deadline).format('YYYY-MM-DD HH:mm') : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EyeOutlined />} onClick={() => handleViewDetail(record.id)}>
            查看
          </Button>
          {record.status === 'pending' && (
            <Popconfirm
              title="确定要取消此任务吗？"
              onConfirm={() => handleCancel(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" danger icon={<CloseOutlined />}>
                取消
              </Button>
            </Popconfirm>
          )}
        </Space>
      )
    }
  ]

  // 计算资产分配统计
  const getAssetDistribution = () => {
    const distribution = {}
    selectedAssets.forEach(asset => {
      const userId = asset.user_id
      const userName = asset.user?.real_name || '未知'
      if (!distribution[userId]) {
        distribution[userId] = { name: userName, count: 0 }
      }
      distribution[userId].count++
    })
    return Object.values(distribution)
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>安全检查任务管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          发布新任务
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1200 }}
      />

      <Modal
        title="发布安全检查任务"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        width={1000}
        footer={null}
        destroyOnClose
      >
        <Steps current={createStep} style={{ marginBottom: 24 }}>
          <Steps.Step title="选择检查类型和资产" />
          <Steps.Step title="设置任务信息" />
          <Steps.Step title="确认发布" />
        </Steps>

        <Form form={form} layout="vertical">
          {createStep === 0 && (
            <div>
              <Form.Item
                name="check_type_id"
                label="检查类型"
                rules={[{ required: true, message: '请选择检查类型' }]}
              >
                <Select placeholder="请选择检查类型">
                  {checkTypes.map(type => (
                    <Select.Option key={type.id} value={type.id}>
                      {type.name}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>

              <div style={{ marginTop: 24 }}>
                <h4>资产筛选</h4>
                <Form form={filterForm} layout="inline" style={{ marginBottom: 16 }}>
                  <Form.Item name="category_id" label="资产大类">
                    <Select placeholder="全部" style={{ width: 150 }} allowClear>
                      {categories.map(cat => (
                        <Select.Option key={cat.id} value={cat.id}>
                          {cat.name}
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>
                  <Form.Item name="status" label="状态">
                    <Select placeholder="全部" style={{ width: 120 }} allowClear>
                      <Select.Option value="在用">在用</Select.Option>
                      <Select.Option value="库存备用">库存备用</Select.Option>
                    </Select>
                  </Form.Item>
                  <Form.Item name="search" label="搜索">
                    <Input placeholder="资产编号/名称" style={{ width: 200 }} />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" onClick={handleAssetSearch}>搜索</Button>
                  </Form.Item>
                </Form>

                <div style={{ marginBottom: 16 }}>
                  <Checkbox
                    checked={selectedAssets.length === assets.length && assets.length > 0}
                    indeterminate={selectedAssets.length > 0 && selectedAssets.length < assets.length}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                  >
                    全选 ({selectedAssets.length}/{assets.length})
                  </Checkbox>
                </div>

                <div style={{ maxHeight: 400, overflow: 'auto', border: '1px solid #d9d9d9', padding: 8, borderRadius: 4 }}>
                  {assets.map(asset => (
                    <div key={asset.id} style={{ marginBottom: 8 }}>
                      <Checkbox
                        checked={selectedAssets.some(a => a.id === asset.id)}
                        onChange={(e) => handleAssetSelect(asset, e.target.checked)}
                      >
                        {asset.asset_number} - {asset.name} ({asset.user?.real_name || '无使用人'})
                      </Checkbox>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {createStep === 1 && (
            <div>
              <Form.Item
                name="title"
                label="任务标题"
                rules={[{ required: true, message: '请输入任务标题' }]}
              >
                <Input placeholder="例如：2025年第一季度消防安全检查" />
              </Form.Item>

              <Form.Item
                name="description"
                label="任务描述"
              >
                <TextArea rows={4} placeholder="任务描述（可选）" />
              </Form.Item>

              <Form.Item
                name="deadline"
                label="截止时间"
              >
                <DatePicker
                  showTime
                  format="YYYY-MM-DD HH:mm"
                  style={{ width: '100%' }}
                  placeholder="选择截止时间（可选）"
                />
              </Form.Item>

              <Card size="small" style={{ marginTop: 16 }}>
                <h4>任务预览</h4>
                <p>检查类型: {checkTypes.find(t => t.id === form.getFieldValue('check_type_id'))?.name || '-'}</p>
                <p>资产数量: {selectedAssets.length}</p>
                <p>分配用户: {getAssetDistribution().length}人</p>
              </Card>
            </div>
          )}

          {createStep === 2 && (
            <div>
              <Card>
                <h4>请确认任务信息</h4>
                <p><strong>任务标题:</strong> {form.getFieldValue('title')}</p>
                <p><strong>检查类型:</strong> {checkTypes.find(t => t.id === form.getFieldValue('check_type_id'))?.name || '-'}</p>
                <p><strong>资产数量:</strong> {selectedAssets.length}</p>
                <p><strong>分配用户:</strong></p>
                <ul>
                  {getAssetDistribution().map((dist, index) => (
                    <li key={index}>{dist.name} ({dist.count}项)</li>
                  ))}
                </ul>
                <p><strong>截止时间:</strong> {form.getFieldValue('deadline') ? form.getFieldValue('deadline').format('YYYY-MM-DD HH:mm') : '无'}</p>
              </Card>
            </div>
          )}

          <div style={{ marginTop: 24, textAlign: 'right' }}>
            {createStep > 0 && (
              <Button style={{ marginRight: 8 }} onClick={handlePrev}>
                上一步
              </Button>
            )}
            {createStep < 2 ? (
              <Button type="primary" onClick={handleNext}>
                下一步
              </Button>
            ) : (
              <Button type="primary" onClick={handleSubmit}>
                确认发布
              </Button>
            )}
          </div>
        </Form>
      </Modal>
    </div>
  )
}

export default SafetyCheckTaskManagement

