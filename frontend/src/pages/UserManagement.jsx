import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, Upload, message, Popconfirm, Space, Alert, Descriptions, Tag } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, UploadOutlined, SearchOutlined, ReloadOutlined, UserDeleteOutlined } from '@ant-design/icons'
import api from '../utils/api'
import { useAuth } from '../contexts/AuthContext'

const UserManagement = () => {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [form] = Form.useForm()
  const [filtersForm] = Form.useForm()
  const [filters, setFilters] = useState({})
  const [importErrorModalVisible, setImportErrorModalVisible] = useState(false)
  const [importErrors, setImportErrors] = useState([])
  const [resignationModalVisible, setResignationModalVisible] = useState(false)
  const [resigningUser, setResigningUser] = useState(null)
  const [userAssetCount, setUserAssetCount] = useState(0)
  const [markingResignation, setMarkingResignation] = useState(false)

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async (extraFilters) => {
    setLoading(true)
    try {
      const params = { ...filters, ...(extraFilters || {}) }
      const response = await api.get('/users/', { params })
      // 方案乙：不在用户列表中显示仓库用户
      setUsers((response.data || []).filter(u => u.ehr_number !== '1000000'))
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
      role: values.role || undefined,
      status: values.status || undefined
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
    form.setFieldsValue({ status: '在岗' })
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
      const { success_count, error_count, errors, error_details } = response.data

      if (error_count > 0) {
        // 如果有错误，显示错误详情模态框
        setImportErrors(error_details || errors.map((err, idx) => ({
          row_number: idx + 1,
          error_message: err,
          row_data: {}
        })))
        setImportErrorModalVisible(true)
        message.warning(`导入完成：成功 ${success_count} 条，失败 ${error_count} 条，请查看失败详情`)
      } else {
        message.success(`导入完成：成功 ${success_count} 条`)
      }
      fetchUsers(filters)
    } catch (error) {
      message.error(error.response?.data?.detail || '导入失败')
    }
    return false // 阻止自动上传
  }

  // 获取用户资产数量
  const fetchUserAssetCount = async (userId) => {
    try {
      const response = await api.get('/assets/', { params: { user_id: userId, limit: 10000 } })
      // 只统计有使用人的资产（user_id不为空）
      return response.data.filter(asset => asset.user_id === userId).length
    } catch (error) {
      console.error('获取用户资产数量失败:', error)
      return 0
    }
  }

  // 打开标记离职确认Modal
  const handleOpenMarkResignation = async (user) => {
    setResigningUser(user)
    const count = await fetchUserAssetCount(user.id)
    setUserAssetCount(count)
    setResignationModalVisible(true)
  }

  // 确认标记离职
  const handleConfirmMarkResignation = async () => {
    if (!resigningUser) return

    setMarkingResignation(true)
    try {
      // 调用后端接口（假设路径为 PUT /api/users/{user_id}/mark-resignation）
      const response = await api.put(`/users/${resigningUser.id}/mark-resignation`)

      if (userAssetCount > 0) {
        const taskCount = response.data?.task_count || userAssetCount
        message.success(`标记离职成功，已为该用户创建${taskCount}个安全检查任务`)
      } else {
        message.success('标记离职成功')
      }

      setResignationModalVisible(false)
      setResigningUser(null)
      setUserAssetCount(0)
      fetchUsers()
    } catch (error) {
      const errorMsg = error.response?.data?.detail || '标记离职失败'
      message.error(errorMsg)
    } finally {
      setMarkingResignation(false)
    }
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
      render: (role) => {
        const roleMap = {
          'admin': '管理员',
          'leader': '组长',
          'user': '普通用户'
        }
        return roleMap[role] || role
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const statusConfig = {
          '在岗': { color: 'success', text: '在岗' },
          '离职': { color: 'error', text: '离职' },
          '长期出差': { color: 'processing', text: '长期出差' },
          '借调': { color: 'warning', text: '借调' },
          '产假': { color: 'purple', text: '产假' }
        }
        const config = statusConfig[status] || { color: 'default', text: status || '在岗' }
        return <Tag color={config.color}>{config.text}</Tag>
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => {
        // 仓库用户（EHR号为1000000）不能删除；管理员不能删除自己
        const isWarehouse = record.ehr_number === '1000000'
        const isSelf = record.id === currentUser?.id
        return (
          <Space>
            <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
              编辑
            </Button>
            {record.status !== '离职' && (
              <Button
                type="link"
                danger
                icon={<UserDeleteOutlined />}
                onClick={() => handleOpenMarkResignation(record)}
              >
                标记离职
              </Button>
            )}
            {!isWarehouse && !isSelf && (
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
            <Select.Option value="leader">组长</Select.Option>
            <Select.Option value="user">普通用户</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item label="状态" name="status">
          <Select placeholder="全部" style={{ width: 120 }} allowClear>
            <Select.Option value="在岗">在岗</Select.Option>
            <Select.Option value="离职">离职</Select.Option>
            <Select.Option value="长期出差">长期出差</Select.Option>
            <Select.Option value="借调">借调</Select.Option>
            <Select.Option value="产假">产假</Select.Option>
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
              <Select.Option value="leader">组长</Select.Option>
              <Select.Option value="admin">管理员</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="状态"
            name="status"
            rules={[{ required: true, message: '请选择状态' }]}
            initialValue="在岗"
          >
            <Select>
              <Select.Option value="在岗">在岗</Select.Option>
              <Select.Option value="离职">离职</Select.Option>
              <Select.Option value="长期出差">长期出差</Select.Option>
              <Select.Option value="借调">借调</Select.Option>
              <Select.Option value="产假">产假</Select.Option>
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

      {/* 导入错误详情模态框 */}
      <Modal
        title="导入失败记录详情"
        open={importErrorModalVisible}
        onCancel={() => {
          setImportErrorModalVisible(false)
          setImportErrors([])
        }}
        footer={[
          <Button key="close" onClick={() => {
            setImportErrorModalVisible(false)
            setImportErrors([])
          }}>
            关闭
          </Button>
        ]}
        width={900}
      >
        <Alert
          message={`共 ${importErrors.length} 条记录导入失败`}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Table
          dataSource={importErrors}
          rowKey={(record, index) => `error-${record.row_number || index}`}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条失败记录`
          }}
          scroll={{ x: 800 }}
          size="small"
          columns={[
            {
              title: '行号',
              dataIndex: 'row_number',
              key: 'row_number',
              width: 80,
              fixed: 'left'
            },
            {
              title: '失败原因',
              dataIndex: 'error_message',
              key: 'error_message',
              width: 250,
              ellipsis: true,
              render: (text) => (
                <span style={{ color: '#ff4d4f' }}>{text}</span>
              )
            },
            {
              title: 'EHR号',
              dataIndex: ['row_data', 'EHR号'],
              key: 'ehr_number',
              width: 120
            },
            {
              title: '姓名',
              dataIndex: ['row_data', '姓名'],
              key: 'real_name',
              width: 120
            },
            {
              title: '组别',
              dataIndex: ['row_data', '组别'],
              key: 'group',
              width: 120
            },
            {
              title: '角色',
              dataIndex: ['row_data', '角色'],
              key: 'role',
              width: 100
            },
            {
              title: '其他数据',
              key: 'other_data',
              width: 150,
              ellipsis: true,
              render: (_, record) => {
                const { row_data } = record
                const excludeFields = ['EHR号', '姓名', '组别', '角色']
                const otherFields = Object.entries(row_data || {})
                  .filter(([key]) => !excludeFields.includes(key))
                  .filter(([_, value]) => value && value !== 'nan' && value !== '')
                  .map(([key, value]) => `${key}: ${value}`)
                  .join('; ')
                return otherFields || '-'
              }
            }
          ]}
          expandable={{
            expandedRowRender: (record) => {
              const { row_data } = record
              if (!row_data || Object.keys(row_data).length === 0) {
                return <div style={{ padding: 16 }}>无原始数据</div>
              }
              return (
                <div style={{ padding: 16, background: '#fafafa' }}>
                  <Descriptions bordered column={2} size="small">
                    {Object.entries(row_data).map(([key, value]) => (
                      <Descriptions.Item key={key} label={key} span={1}>
                        {value && value !== 'nan' ? String(value) : '-'}
                      </Descriptions.Item>
                    ))}
                  </Descriptions>
                </div>
              )
            },
            rowExpandable: (record) => record.row_data && Object.keys(record.row_data).length > 0
          }}
        />
      </Modal>

      {/* 标记离职确认Modal */}
      <Modal
        title="标记离职"
        open={resignationModalVisible}
        onCancel={() => {
          setResignationModalVisible(false)
          setResigningUser(null)
          setUserAssetCount(0)
        }}
        onOk={handleConfirmMarkResignation}
        confirmLoading={markingResignation}
        okText="确认标记离职"
        cancelText="取消"
        width={500}
      >
        <div style={{ marginBottom: 16 }}>
          <Alert
            message="是否完成数据安全检查进行资产交接？"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
          {resigningUser && (
            <div style={{ marginBottom: 16 }}>
              <p><strong>用户：</strong>{resigningUser.real_name}（{resigningUser.ehr_number}）</p>
              <p><strong>名下资产数量：</strong>{userAssetCount}个</p>
            </div>
          )}
          <div>
            <p><strong>确认后将：</strong></p>
            <ol style={{ marginLeft: 20, marginTop: 8 }}>
              <li>将该用户状态更新为「离职」</li>
              {userAssetCount > 0 && (
                <>
                  <li>为该用户{userAssetCount}个资产自动创建安全检查任务</li>
                  <li>任务将分配给该用户</li>
                </>
              )}
            </ol>
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default UserManagement


