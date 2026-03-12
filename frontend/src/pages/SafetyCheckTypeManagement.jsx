import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Switch, message, Popconfirm, Space, Card, Select, Divider, Alert } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, SettingOutlined } from '@ant-design/icons'
import api from '../utils/api'
import { useAuth } from '../contexts/AuthContext'

const { TextArea } = Input

const SafetyCheckTypeManagement = () => {
  const { isAdmin } = useAuth()
  const [checkTypes, setCheckTypes] = useState([])
  const [categories, setCategories] = useState([])
  const [autoConfig, setAutoConfig] = useState({ default_type_id: null })
  const [mappings, setMappings] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [mappingModalVisible, setMappingModalVisible] = useState(false)
  const [editingType, setEditingType] = useState(null)
  const [form] = Form.useForm()
  const [mappingForm] = Form.useForm()

  useEffect(() => {
    if (isAdmin) {
      fetchCheckTypes()
      fetchCategories()
      fetchAutoConfig()
      fetchMappings()
    }
  }, [isAdmin])

  const fetchCheckTypes = async () => {
    setLoading(true)
    try {
      const response = await api.get('/safety-check-types/')
      setCheckTypes(response.data)
    } catch (error) {
      message.error('获取检查类型列表失败')
    } finally {
      setLoading(false)
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

  const fetchAutoConfig = async () => {
    try {
      const response = await api.get('/safety-check-auto-config/')
      setAutoConfig(response.data || { default_type_id: null })
    } catch (error) {
      console.error('获取自动配置失败:', error)
    }
  }

  const fetchMappings = async () => {
    try {
      const response = await api.get('/safety-check-auto-config/asset-type-mappings')
      setMappings(response.data || [])
    } catch (error) {
      console.error('获取映射列表失败:', error)
    }
  }

  const handleUpdateDefaultType = async (value) => {
    try {
      await api.put('/safety-check-auto-config', { default_check_type_id: value })
      message.success('默认检查类型已更新')
      fetchAutoConfig()
    } catch (error) {
      message.error('更新失败')
    }
  }

  const handleAddMapping = async (values) => {
    try {
      // 后端逻辑映射是基于 asset_type 字符串，这里将选取的大类 ID 转换为名称
      const category = categories.find(c => c.id === values.category_id)
      if (!category) return

      await api.post('/safety-check-auto-config/asset-type-mappings', {
        asset_type: category.name,
        check_type_id: values.check_type_id
      })
      message.success('映射添加成功')
      setMappingModalVisible(false)
      mappingForm.resetFields()
      fetchMappings()
    } catch (error) {
      message.error(error.response?.data?.detail || '添加失败')
    }
  }

  const handleDeleteMapping = async (id) => {
    try {
      await api.delete(`/safety-check-auto-config/asset-type-mappings/${id}`)
      message.success('映射已删除')
      fetchMappings()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleAdd = () => {
    setEditingType(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true, check_items: [] })
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingType(record)
    form.setFieldsValue({
      name: record.name,
      description: record.description,
      is_active: record.is_active,
      check_items: record.check_items || []
    })
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await api.delete(`/safety-check-types/${id}`)
      message.success('检查类型已停用')
      fetchCheckTypes()
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const handleSubmit = async (values) => {
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
      setModalVisible(false)
      fetchCheckTypes()
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const columns = [
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
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要停用此检查类型吗？"
            onConfirm={() => handleDelete(record.id)}
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
  ]

  const mappingColumns = [
    {
      title: '资产大类',
      dataIndex: ['category', 'name'],
      key: 'category'
    },
    {
      title: '联动检查类型',
      dataIndex: ['check_type', 'name'],
      key: 'check_type'
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record) => (
        <Popconfirm title="确定删除此映射吗？" onConfirm={() => handleDeleteMapping(record.id)}>
          <Button type="link" danger icon={<DeleteOutlined />} size="small" />
        </Popconfirm>
      )
    }
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2>安全检查联动配置</h2>
        <Alert
          message="配置说明"
          description="在此配置资产管理与安全检查的自动化联动规则。当管理员标记用户离职时，系统将根据配置自动创建检查任务。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Card size="small" title="基础配置" style={{ marginBottom: 16 }}>
          <Space align="center" size="large">
            <span>
              <strong>默认检查类型：</strong>
              <Select
                placeholder="请选择离职时的默认检查类型"
                style={{ width: 250, marginLeft: 8 }}
                value={autoConfig.default_type_id}
                onChange={handleUpdateDefaultType}
                allowClear
              >
                {checkTypes.map(t => (
                  <Select.Option key={t.id} value={t.id}>{t.name}</Select.Option>
                ))}
              </Select>
            </span>
            <Button type="primary" ghost icon={<SettingOutlined />} onClick={() => setMappingModalVisible(true)}>
              管理大类映射
            </Button>
          </Space>
        </Card>
      </div>

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>检查类型库</h3>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新增检查类型
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={checkTypes}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1000 }}
        size="small"
        bordered
      />

      {/* 映射管理 Modal */}
      <Modal
        title="资产大类 - 检查类型映射管理"
        open={mappingModalVisible}
        onCancel={() => setMappingModalVisible(false)}
        footer={null}
        width={600}
      >
        <div style={{ marginBottom: 16 }}>
          <Form form={mappingForm} layout="inline" onFinish={handleAddMapping}>
            <Form.Item name="category_id" rules={[{ required: true, message: '选择大类' }]}>
              <Select placeholder="选择资产大类" style={{ width: 180 }}>
                {categories.map(c => (
                  <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="check_type_id" rules={[{ required: true, message: '选择类型' }]}>
              <Select placeholder="选择检查类型" style={{ width: 180 }}>
                {checkTypes.map(t => (
                  <Select.Option key={t.id} value={t.id}>{t.name}</Select.Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit">添加映射</Button>
            </Form.Item>
          </Form>
        </div>
        <Table
          columns={mappingColumns}
          dataSource={mappings}
          rowKey="id"
          size="small"
          pagination={false}
          bordered
        />
      </Modal>

      {/* 编辑/新增检查类型 Modal */}
      <Modal
        title={editingType ? '编辑检查类型' : '新增检查类型'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={800}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="name"
            label="类型名称"
            rules={[{ required: true, message: '请输入类型名称' }]}
          >
            <Input placeholder="例如：数据安全检查" />
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
    </div>
  )
}

export default SafetyCheckTypeManagement

