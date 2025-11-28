import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, DatePicker, message, Popconfirm, Space, Steps, Card, Tag, Checkbox, Tooltip, Switch } from 'antd'
import { PlusOutlined, EyeOutlined, CloseOutlined, SettingOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
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
  const [formValues, setFormValues] = useState({})
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [detailTask, setDetailTask] = useState(null)
  const [detailAssets, setDetailAssets] = useState([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [typeManagementVisible, setTypeManagementVisible] = useState(false)
  const [typeManagementLoading, setTypeManagementLoading] = useState(false)
  const [editingType, setEditingType] = useState(null)
  const [typeFormModalVisible, setTypeFormModalVisible] = useState(false)
  const [typeForm] = Form.useForm()
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
      console.log(response.data)
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

  const fetchAllCheckTypes = async () => {
    setTypeManagementLoading(true)
    try {
      const response = await api.get('/safety-check-types/')
      setCheckTypes(response.data)
    } catch (error) {
      message.error('获取检查类型列表失败')
    } finally {
      setTypeManagementLoading(false)
    }
  }

  const handleOpenTypeManagement = () => {
    setTypeManagementVisible(true)
    fetchAllCheckTypes()
  }

  const handleTypeAdd = () => {
    setEditingType(null)
    typeForm.resetFields()
    typeForm.setFieldsValue({ is_active: true, check_items: [] })
    setTypeFormModalVisible(true)
  }

  const handleTypeEdit = (record) => {
    setEditingType(record)
    typeForm.setFieldsValue({
      name: record.name,
      description: record.description,
      is_active: record.is_active,
      check_items: record.check_items || []
    })
    setTypeFormModalVisible(true)
  }

  const handleTypeDelete = async (id) => {
    try {
      await api.delete(`/safety-check-types/${id}`)
      message.success('检查类型已停用')
      fetchAllCheckTypes()
      fetchCheckTypes() // 同时更新任务创建时使用的检查类型列表
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const handleTypeSubmit = async (values) => {
    try {
      const payload = {
        name: values.name,
        description: values.description,
        is_active: values.is_active,
        check_items: values.check_items || []
      }

      if (editingType) {
        await api.put(`/safety-check-types/${editingType.id}`, payload)
        message.success('更新成功')
      } else {
        await api.post('/safety-check-types/', payload)
        message.success('创建成功')
      }
      typeForm.resetFields()
      setEditingType(null)
      setTypeFormModalVisible(false)
      fetchAllCheckTypes()
      fetchCheckTypes() // 同时更新任务创建时使用的检查类型列表
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败')
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
    setFormValues({})
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
      const values = { ...formValues, ...form.getFieldsValue(true) }
      if (!values.check_type_id) {
        message.error('请选择检查类型')
        setCreateStep(0)
        return
      }
      if (!values.title) {
        message.error('请输入任务标题')
        setCreateStep(1)
        return
      }
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
    setDetailModalVisible(true)
    setDetailLoading(true)
    try {
      const [taskRes, assetsRes] = await Promise.all([
        api.get(`/safety-check-tasks/${taskId}`),
        api.get(`/safety-check-tasks/${taskId}/assets`)
      ])
      setDetailTask(taskRes.data)
      // assetsRes.data.assets 是 TaskAssetResponse 对象数组
      setDetailAssets(assetsRes.data.assets || [])
    } catch (error) {
      console.error('获取任务详情失败:', error)
      message.error(error.response?.data?.detail || '获取任务详情失败')
      setDetailModalVisible(false)
    } finally {
      setDetailLoading(false)
    }
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
      width: 200,
      ellipsis: {
        showTitle: false
      },
      render: (value) =>
        value ? (
          <Tooltip placement="topLeft" title={value}>
            {value}
          </Tooltip>
        ) : (
          '-'
        )
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
      width: 180,
      fixed: 'right',
      align: 'center',
      render: (_, record) => (
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12 }}>
          <Button type="link" icon={<EyeOutlined />} onClick={() => handleViewDetail(record.id)} style={{ padding: 0 }}>
            查看
          </Button>
          {record.status === 'pending' && (
            <Popconfirm
              title="确定要取消此任务吗？"
              onConfirm={() => handleCancel(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" danger icon={<CloseOutlined />} style={{ padding: 0 }}>
                取消
              </Button>
            </Popconfirm>
          )}
        </div>
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
        <Space>
          <Button icon={<SettingOutlined />} onClick={handleOpenTypeManagement}>
            检查类型管理
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            发布新任务
          </Button>
        </Space>
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

        <Form
          form={form}
          layout="vertical"
          onValuesChange={(_, allValues) => setFormValues(allValues)}
        >
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
                <p>检查类型: {checkTypes.find(t => t.id === formValues.check_type_id)?.name || '-'}</p>
                <p>资产数量: {selectedAssets.length}</p>
                <p>分配用户: {getAssetDistribution().length}人</p>
              </Card>
            </div>
          )}

          {createStep === 2 && (
            <div>
              <Card>
                <h4>请确认任务信息</h4>
                <p><strong>任务标题:</strong> {formValues.title || '-'}</p>
                <p><strong>检查类型:</strong> {checkTypes.find(t => t.id === formValues.check_type_id)?.name || '-'}</p>
                <p><strong>资产数量:</strong> {selectedAssets.length}</p>
                <p><strong>分配用户:</strong></p>
                <ul>
                  {getAssetDistribution().map((dist, index) => (
                    <li key={index}>{dist.name} ({dist.count}项)</li>
                  ))}
                </ul>
                <p><strong>截止时间:</strong> {formValues.deadline ? formValues.deadline.format('YYYY-MM-DD HH:mm') : '无'}</p>
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

      <Modal
        title="任务详情"
        open={detailModalVisible}
        onCancel={() => {
          setDetailModalVisible(false)
          setDetailTask(null)
          setDetailAssets([])
        }}
        width={900}
        footer={null}
        destroyOnClose
      >
        {detailLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : detailTask ? (
          <div>
            <Card size="small" style={{ marginBottom: 16 }}>
              <p><strong>任务编号：</strong>{detailTask.task_number}</p>
              <p><strong>任务标题：</strong>{detailTask.title}</p>
              <p><strong>检查类型：</strong>{detailTask.check_type?.name || '-'}</p>
              <p><strong>创建时间：</strong>{dayjs(detailTask.created_at).format('YYYY-MM-DD HH:mm')}</p>
              <p><strong>截止时间：</strong>{detailTask.deadline ? dayjs(detailTask.deadline).format('YYYY-MM-DD HH:mm') : '无'}</p>
              <p><strong>描述：</strong>{detailTask.description || '无'}</p>
            </Card>
            <Card size="small" title="完成情况" style={{ marginBottom: 16 }}>
              <Space size="large">
                <div>
                  <div style={{ fontSize: 18, fontWeight: 600 }}>{detailTask.total_assets ?? detailAssets.length}</div>
                  <div>任务总数</div>
                </div>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: '#52c41a' }}>{detailAssets.filter(a => a.status === 'checked').length}</div>
                  <div>已完成</div>
                </div>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: '#faad14' }}>{detailAssets.filter(a => a.status === 'pending').length}</div>
                  <div>待检查</div>
                </div>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: '#ff4d4f' }}>{detailAssets.filter(a => a.status === 'returned').length}</div>
                  <div>已退库</div>
                </div>
              </Space>
            </Card>
            <Card size="small" title="未完成名单" style={{ marginBottom: 16 }}>
              {detailAssets.filter(a => a.status !== 'checked').length === 0 ? (
                <div>全部完成</div>
              ) : (
                detailAssets
                  .filter(a => a.status !== 'checked')
                  .map(asset => (
                    <div key={asset.id} style={{ marginBottom: 8 }}>
                      <Tag color={asset.status === 'returned' ? 'red' : 'orange'}>
                        {asset.status === 'returned' ? '已退库' : '待检查'}
                      </Tag>
                      {asset.asset?.asset_number || '-'} - {asset.asset?.name || '-'}（{asset.assigned_user?.real_name || '未知使用人'}）
                    </div>
                  ))
              )}
            </Card>
            <Card size="small" title="全部资产进度">
              {detailAssets.length === 0 ? (
                <div>暂无数据</div>
              ) : (
                <div style={{ maxHeight: 300, overflow: 'auto' }}>
                  {detailAssets.map(asset => (
                    <div key={asset.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                      <div style={{ flex: 1 }}>
                        <div>{asset.asset?.asset_number || '-'} - {asset.asset?.name || '-'}</div>
                        <div style={{ color: '#888', fontSize: '12px' }}>使用人：{asset.assigned_user?.real_name || '未知'}</div>
                        {asset.status === 'checked' && asset.check_result && (
                          <div style={{ color: '#666', fontSize: '12px', marginTop: '4px' }}>
                            <div>
                              检查结果：<span style={{ color: asset.check_result === 'yes' ? '#52c41a' : '#ff4d4f', fontWeight: 500 }}>
                                {asset.check_result === 'yes' ? '通过' : '不通过'}
                              </span>
                              {asset.check_comment && (
                                <span style={{ marginLeft: '8px' }}>备注：{asset.check_comment}</span>
                              )}
                            </div>
                            {asset.check_items_result && Array.isArray(asset.check_items_result) && asset.check_items_result.length > 0 && (
                              <div style={{ marginTop: '4px', paddingLeft: '8px' }}>
                                {asset.check_items_result.map((item, index) => (
                                  <div key={index} style={{ marginTop: '2px', fontSize: '11px' }}>
                                    • {item.item}：
                                    <span style={{ 
                                      color: item.result === 'yes' ? '#52c41a' : '#ff4d4f', 
                                      fontWeight: 500,
                                      marginLeft: '4px'
                                    }}>
                                      {item.result === 'yes' ? '通过' : '不通过'}
                                    </span>
                                    {item.comment && (
                                      <span style={{ color: '#999', marginLeft: '8px' }}>（{item.comment}）</span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      <Tag 
                        color={
                          asset.status === 'checked' ? 'green' : 
                          asset.status === 'returned' ? 'red' : 
                          'orange'
                        }
                        style={{ 
                          textAlign: 'center',
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          minWidth: '60px'
                        }}
                      >
                        {asset.status === 'checked' ? '已完成' : 
                         asset.status === 'returned' ? '已退库' : 
                         '待检查'}
                      </Tag>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 40 }}>暂无数据</div>
        )}
      </Modal>

      {/* 检查类型管理模态框 */}
      <Modal
        title="检查类型管理"
        open={typeManagementVisible}
        onCancel={() => {
          setTypeManagementVisible(false)
          setEditingType(null)
          typeForm.resetFields()
        }}
        width={1000}
        footer={null}
        destroyOnClose
      >
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <div></div>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleTypeAdd}>
            新增检查类型
          </Button>
        </div>

        <Table
          columns={[
            {
              title: '类型名称',
              dataIndex: 'name',
              key: 'name',
              width: 200
            },
            {
              title: '描述',
              dataIndex: 'description',
              key: 'description',
              ellipsis: true
            },
            {
              title: '检查项数量',
              key: 'check_items_count',
              width: 120,
              render: (_, record) => {
                return record.check_items?.length || 0
              }
            },
            {
              title: '状态',
              dataIndex: 'is_active',
              key: 'is_active',
              width: 100,
              render: (isActive) => (
                <span style={{ color: isActive ? '#52c41a' : '#999' }}>
                  {isActive ? '启用' : '停用'}
                </span>
              )
            },
            {
              title: '操作',
              key: 'action',
              width: 150,
              fixed: 'right',
              render: (_, record) => (
                <Space>
                  <Button
                    type="link"
                    icon={<EditOutlined />}
                    onClick={() => handleTypeEdit(record)}
                  >
                    编辑
                  </Button>
                  <Popconfirm
                    title="确定要停用此检查类型吗？"
                    onConfirm={() => handleTypeDelete(record.id)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button type="link" danger icon={<DeleteOutlined />}>
                      停用
                    </Button>
                  </Popconfirm>
                </Space>
              )
            }
          ]}
          dataSource={checkTypes}
          rowKey="id"
          loading={typeManagementLoading}
          scroll={{ x: 1000 }}
        />

        {/* 编辑/新增检查类型表单模态框 */}
        <Modal
          title={editingType ? '编辑检查类型' : '新增检查类型'}
          open={typeFormModalVisible}
          onCancel={() => {
            setEditingType(null)
            setTypeFormModalVisible(false)
            typeForm.resetFields()
          }}
          onOk={() => typeForm.submit()}
          width={800}
          destroyOnClose
        >
          <Form
            form={typeForm}
            layout="vertical"
            onFinish={handleTypeSubmit}
          >
            <Form.Item
              name="name"
              label="类型名称"
              rules={[{ required: true, message: '请输入类型名称' }]}
            >
              <Input placeholder="例如：消防安全检查" />
            </Form.Item>

            <Form.Item
              name="description"
              label="描述"
            >
              <TextArea rows={3} placeholder="检查类型描述（可选）" />
            </Form.Item>

            <Form.Item
              name="is_active"
              label="状态"
              valuePropName="checked"
            >
              <Switch checkedChildren="启用" unCheckedChildren="停用" />
            </Form.Item>

            <Form.Item
              name="check_items"
              label="检查项列表"
            >
              <Form.List name="check_items">
                {(fields, { add, remove }) => (
                  <>
                    {fields.map(({ key, name, ...restField }) => (
                      <div key={key} style={{ marginBottom: 16, padding: 16, border: '1px solid #d9d9d9', borderRadius: 4 }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Form.Item
                            {...restField}
                            name={[name, 'item']}
                            label="检查项内容"
                            rules={[{ required: true, message: '请输入检查项内容' }]}
                            style={{ marginBottom: 8 }}
                          >
                            <Input placeholder="例如：灭火器是否在有效期内" />
                          </Form.Item>
                          <Form.Item
                            {...restField}
                            name={[name, 'required']}
                            valuePropName="checked"
                            style={{ marginBottom: 0 }}
                          >
                            <Switch checkedChildren="必填" unCheckedChildren="可选" />
                          </Form.Item>
                          <Button
                            type="link"
                            danger
                            onClick={() => remove(name)}
                            style={{ padding: 0 }}
                          >
                            删除
                          </Button>
                        </Space>
                      </div>
                    ))}
                    <Button type="dashed" onClick={() => add()} block>
                      添加检查项
                    </Button>
                  </>
                )}
              </Form.List>
            </Form.Item>
          </Form>
        </Modal>
      </Modal>
    </div>
  )
}

export default SafetyCheckTaskManagement

