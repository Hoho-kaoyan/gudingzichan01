import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, Upload, message, Popconfirm, Space } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, UploadOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import api from '../utils/api'

const UserManagement = () => {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [form] = Form.useForm()
  const [filtersForm] = Form.useForm()
  const [filters, setFilters] = useState({})

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async (extraFilters) => {
    setLoading(true)
    try {
      const params = { ...filters, ...(extraFilters || {}) }
      const response = await api.get('/users/', { params })
      setUsers(response.data)
    } catch (error) {
      message.error('获取用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    const values = filtersForm.getFieldsValue()
    const payload = {
      search: values.keyword || undefined,
      role: values.role || undefined
    }
    setFilters(payload)
    fetchUsers(payload)
  }

  const handleResetFilters = () => {
    filtersForm.resetFields()
    setFilters({})
    fetchUsers({})
  }

  const handleAdd = () => {
    setEditingUser(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingUser(record)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await api.delete(`/users/${id}`)
      message.success('删除成功')
      fetchUsers()
    } catch (error) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  const handleSubmit = async (values) => {
    try {
      if (editingUser) {
        await api.put(`/users/${editingUser.id}`, values)
        message.success('更新成功')
      } else {
        await api.post('/users/', values)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchUsers()
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const handleImport = async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await api.post('/users/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      const { success_count, error_count, errors } = response.data
      message.success(`导入完成：成功 ${success_count} 条，失败 ${error_count} 条`)
      if (errors.length > 0) {
        console.error('导入错误:', errors)
      }
      fetchUsers(filters)
    } catch (error) {
      message.error('导入失败')
    }
    return false // 阻止自动上传
  }

  const columns = [
    {
      title: 'EHR号',
      dataIndex: 'ehr_number',
      key: 'ehr_number'
    },
    {
      title: '姓名',
      dataIndex: 'real_name',
      key: 'real_name'
    },
    {
      title: '组别',
      dataIndex: 'group',
      key: 'group'
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role) => role === 'admin' ? '管理员' : '普通用户'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => {
        // 仓库用户（EHR号为1000000）不能删除
        const isWarehouse = record.ehr_number === '1000000'
        return (
          <Space>
            <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
              编辑
            </Button>
            {!isWarehouse && (
              <Popconfirm
                title="确定要删除吗？"
                onConfirm={() => handleDelete(record.id)}
              >
                <Button type="link" danger icon={<DeleteOutlined />}>
                  删除
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
        <h1>用户管理</h1>
        <Space>
          <Upload
            accept=".xlsx,.xls"
            beforeUpload={handleImport}
            showUploadList={false}
          >
            <Button icon={<UploadOutlined />}>批量导入</Button>
          </Upload>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增用户
          </Button>
        </Space>
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
            placeholder="搜索EHR号、姓名、组别等"
            style={{ width: 300 }}
            allowClear
          />
        </Form.Item>
        <Form.Item label="角色" name="role">
          <Select placeholder="全部" style={{ width: 120 }} allowClear>
            <Select.Option value="admin">管理员</Select.Option>
            <Select.Option value="user">普通用户</Select.Option>
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
        dataSource={users}
        loading={loading}
        rowKey="id"
      />

      <Modal
        title={editingUser ? '编辑用户' : '新增用户'}
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
            label="EHR号"
            name="ehr_number"
            rules={[
              { required: true, message: '请输入EHR号' },
              { len: 7, message: 'EHR号必须为7位数字' }
            ]}
          >
            <Input disabled={!!editingUser} />
          </Form.Item>
          <Form.Item
            label="姓名"
            name="real_name"
            rules={[{ required: true, message: '请输入姓名' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="组别"
            name="group"
            rules={[{ required: true, message: '请输入组别' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="角色"
            name="role"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select>
              <Select.Option value="user">普通用户</Select.Option>
              <Select.Option value="admin">管理员</Select.Option>
            </Select>
          </Form.Item>
          {!editingUser && (
            <Form.Item
              label="密码"
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password />
            </Form.Item>
          )}
          {editingUser && (
            <Form.Item
              label="新密码（留空则不修改）"
              name="password"
            >
              <Input.Password />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  )
}

export default UserManagement



import { PlusOutlined, EditOutlined, DeleteOutlined, UploadOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import api from '../utils/api'

const UserManagement = () => {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [form] = Form.useForm()
  const [filtersForm] = Form.useForm()
  const [filters, setFilters] = useState({})

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async (extraFilters) => {
    setLoading(true)
    try {
      const params = { ...filters, ...(extraFilters || {}) }
      const response = await api.get('/users/', { params })
      setUsers(response.data)
    } catch (error) {
      message.error('获取用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    const values = filtersForm.getFieldsValue()
    const payload = {
      search: values.keyword || undefined,
      role: values.role || undefined
    }
    setFilters(payload)
    fetchUsers(payload)
  }

  const handleResetFilters = () => {
    filtersForm.resetFields()
    setFilters({})
    fetchUsers({})
  }

  const handleAdd = () => {
    setEditingUser(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingUser(record)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await api.delete(`/users/${id}`)
      message.success('删除成功')
      fetchUsers()
    } catch (error) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  const handleSubmit = async (values) => {
    try {
      if (editingUser) {
        await api.put(`/users/${editingUser.id}`, values)
        message.success('更新成功')
      } else {
        await api.post('/users/', values)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchUsers()
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const handleImport = async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await api.post('/users/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      const { success_count, error_count, errors } = response.data
      message.success(`导入完成：成功 ${success_count} 条，失败 ${error_count} 条`)
      if (errors.length > 0) {
        console.error('导入错误:', errors)
      }
      fetchUsers(filters)
    } catch (error) {
      message.error('导入失败')
    }
    return false // 阻止自动上传
  }

  const columns = [
    {
      title: 'EHR号',
      dataIndex: 'ehr_number',
      key: 'ehr_number'
    },
    {
      title: '姓名',
      dataIndex: 'real_name',
      key: 'real_name'
    },
    {
      title: '组别',
      dataIndex: 'group',
      key: 'group'
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role) => role === 'admin' ? '管理员' : '普通用户'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => {
        // 仓库用户（EHR号为1000000）不能删除
        const isWarehouse = record.ehr_number === '1000000'
        return (
          <Space>
            <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
              编辑
            </Button>
            {!isWarehouse && (
              <Popconfirm
                title="确定要删除吗？"
                onConfirm={() => handleDelete(record.id)}
              >
                <Button type="link" danger icon={<DeleteOutlined />}>
                  删除
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
        <h1>用户管理</h1>
        <Space>
          <Upload
            accept=".xlsx,.xls"
            beforeUpload={handleImport}
            showUploadList={false}
          >
            <Button icon={<UploadOutlined />}>批量导入</Button>
          </Upload>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增用户
          </Button>
        </Space>
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
            placeholder="搜索EHR号、姓名、组别等"
            style={{ width: 300 }}
            allowClear
          />
        </Form.Item>
        <Form.Item label="角色" name="role">
          <Select placeholder="全部" style={{ width: 120 }} allowClear>
            <Select.Option value="admin">管理员</Select.Option>
            <Select.Option value="user">普通用户</Select.Option>
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
        dataSource={users}
        loading={loading}
        rowKey="id"
      />

      <Modal
        title={editingUser ? '编辑用户' : '新增用户'}
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
            label="EHR号"
            name="ehr_number"
            rules={[
              { required: true, message: '请输入EHR号' },
              { len: 7, message: 'EHR号必须为7位数字' }
            ]}
          >
            <Input disabled={!!editingUser} />
          </Form.Item>
          <Form.Item
            label="姓名"
            name="real_name"
            rules={[{ required: true, message: '请输入姓名' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="组别"
            name="group"
            rules={[{ required: true, message: '请输入组别' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="角色"
            name="role"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select>
              <Select.Option value="user">普通用户</Select.Option>
              <Select.Option value="admin">管理员</Select.Option>
            </Select>
          </Form.Item>
          {!editingUser && (
            <Form.Item
              label="密码"
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password />
            </Form.Item>
          )}
          {editingUser && (
            <Form.Item
              label="新密码（留空则不修改）"
              name="password"
            >
              <Input.Password />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  )
}

export default UserManagement


