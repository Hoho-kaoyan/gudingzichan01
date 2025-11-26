import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Switch, message, Popconfirm, Space } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import api from '../utils/api'
import { useAuth } from '../contexts/AuthContext'

const { TextArea } = Input

const SafetyCheckTypeManagement = () => {
  const { isAdmin } = useAuth()
  const [checkTypes, setCheckTypes] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingType, setEditingType] = useState(null)
  const [form] = Form.useForm()

  useEffect(() => {
    if (isAdmin) {
      fetchCheckTypes()
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

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>安全检查类型管理</h2>
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
      />

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
    </div>
  )
}

export default SafetyCheckTypeManagement

