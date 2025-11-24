import React, { useState, useEffect, useCallback } from 'react'
import { Table, Button, Modal, Form, Input, Select, Upload, message, Popconfirm, Space } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, UploadOutlined, DownloadOutlined, SearchOutlined, ReloadOutlined, HistoryOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api from '../utils/api'
import { useAuth } from '../contexts/AuthContext'
import ResizableTitle from '../components/ResizableTitle'

const AssetManagement = () => {
  const { user: currentUser, isAdmin } = useAuth()
  const navigate = useNavigate()
  const [assets, setAssets] = useState([])
  const [categories, setCategories] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingAsset, setEditingAsset] = useState(null)
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [form] = Form.useForm()
  const [filtersForm] = Form.useForm()
  const [filters, setFilters] = useState({})
  const [columns, setColumns] = useState([])

  useEffect(() => {
    if (currentUser) {
      fetchAssets()
      fetchCategories()
      fetchUsers()
    }
  }, [currentUser])

  const fetchAssets = async (extraFilters) => {
    setLoading(true)
    try {
      const params = { ...filters, ...(extraFilters || {}) }
      const response = await api.get('/assets/', { params })
      setAssets(response.data)
      if (isAdmin) {
        setSelectedRowKeys([])
      }
    } catch (error) {
      message.error('获取资产列表失败')
    } finally {
      setLoading(false)
    }
  }
  const handleSearch = () => {
    const values = filtersForm.getFieldsValue()
    const payload = {
      search: values.keyword || undefined,
      category_id: values.category_id || undefined,
      status: values.status || undefined
    }
    setFilters(payload)
    fetchAssets(payload)
  }

  const handleResetFilters = () => {
    filtersForm.resetFields()
    setFilters({})
    fetchAssets({})
  }


  const fetchCategories = async () => {
    try {
      const response = await api.get('/categories/')
      setCategories(response.data)
    } catch (error) {
      console.error('获取资产大类失败:', error)
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
    setEditingAsset(null)
    form.resetFields()
    if (!isAdmin && currentUser) {
      form.setFieldsValue({ user_id: currentUser.id })
    }
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    // 普通用户只能编辑自己名下的资产
    if (!isAdmin && record.user?.id !== currentUser?.id) {
      message.error('只能编辑自己名下的资产')
      return
    }
    setEditingAsset(record)
    form.setFieldsValue({
      ...record,
      category_id: record.category?.id,
      user_id: record.user?.id
    })
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await api.delete(`/assets/${id}`)
      message.success('删除成功')
      fetchAssets()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values) => {
    try {
      // 普通用户创建/编辑资产时强制绑定到自己
      if (!isAdmin && currentUser) {
        values.user_id = currentUser.id
      }
      if (editingAsset) {
        // 普通用户编辑时提交编辑申请，管理员直接更新
        try {
          const response = await api.put(`/assets/${editingAsset.id}`, values)
          // 检查是否是编辑申请（返回消息包含"编辑申请已提交"）
          if (response.data?.message && response.data.message.includes('编辑申请已提交')) {
            message.success('编辑申请已提交，等待管理员审批')
          } else {
            message.success('更新成功')
          }
        } catch (error) {
          // 处理编辑申请的情况（后端返回200但包含消息）
          if (error.response?.status === 200 && error.response?.data?.message) {
            if (error.response.data.message.includes('编辑申请已提交')) {
              message.success('编辑申请已提交，等待管理员审批')
              setModalVisible(false)
              fetchAssets()
              return
            }
          }
          throw error
        }
      } else {
        await api.post('/assets/', values)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchAssets()
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const handleImport = async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await api.post('/assets/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      const { success_count, error_count, errors } = response.data
      message.success(`导入完成：成功 ${success_count} 条，失败 ${error_count} 条`)
      if (errors.length > 0) {
        console.error('导入错误:', errors)
      }
      fetchAssets()
    } catch (error) {
      message.error('导入失败')
    }
    return false
  }

  const handleExport = async () => {
    if (!isAdmin) return
    try {
      const params = {}
      if (selectedRowKeys.length > 0) {
        params.asset_ids = selectedRowKeys.join(',')
      }
      const response = await api.get('/assets/export', {
        params,
        responseType: 'blob'
      })
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      const timestamp = new Date().toISOString().replace(/[:T]/g, '-').slice(0, 19)
      link.href = url
      link.download = `资产导出_${timestamp}.xlsx`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      message.success('导出成功')
    } catch (error) {
      message.error(error.response?.data?.detail || '导出失败')
    }
  }

  // 处理列宽调整
  const handleResize = useCallback((index) => (e, { size }) => {
    setColumns(prevColumns => {
      const newColumns = [...prevColumns]
      newColumns[index] = {
        ...newColumns[index],
        width: size.width
      }
      return newColumns
    })
  }, [])

  // 定义列配置
  const getBaseColumns = () => [
    {
      title: '资产编号',
      dataIndex: 'asset_number',
      key: 'asset_number',
      width: 90
    },
    {
      title: '所属大类',
      dataIndex: ['category', 'name'],
      key: 'category',
      width: 80
    },
    {
      title: '实物名称',
      dataIndex: 'name',
      key: 'name',
      width: 110,
      ellipsis: true
    },
    {
      title: '规格型号',
      dataIndex: 'specification',
      key: 'specification',
      width: 90,
      ellipsis: true
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 65
    },
    {
      title: '使用人',
      dataIndex: ['user', 'real_name'],
      key: 'user',
      width: 80
    },
    {
      title: '组别',
      dataIndex: 'user_group',
      key: 'user_group',
      width: 80
    },
    {
      title: '存放地点',
      dataIndex: 'office_location',
      key: 'office_location',
      width: 90,
      ellipsis: true
    },
    {
      title: '存放楼层',
      dataIndex: 'floor',
      key: 'floor',
      width: 65
    },
    {
      title: '座位号',
      dataIndex: 'seat_number',
      key: 'seat_number',
      width: 65
    },
    {
      title: '备注说明',
      dataIndex: 'remark',
      key: 'remark',
      width: 90,
      ellipsis: true
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right',
      resizable: false, // 操作列不需要调整宽度
      render: (_, record) => {
        // 普通用户只能编辑自己名下的资产，不能删除
        const canEdit = isAdmin || record.user?.id === currentUser?.id
        const canDelete = isAdmin
        
        return (
          <Space size="small">
            <Button 
              type="link" 
              icon={<HistoryOutlined />} 
              onClick={() => navigate(`/assets/${record.id}/history`)}
              size="small"
              style={{ padding: 0 }}
            >
              流转记录
            </Button>
            {canEdit && (
              <Button 
                type="link" 
                icon={<EditOutlined />} 
                onClick={() => handleEdit(record)} 
                size="small"
                style={{ padding: 0 }}
              >
                编辑
              </Button>
            )}
            {canDelete && (
              <Popconfirm
                title="确定要删除吗？"
                onConfirm={() => handleDelete(record.id)}
              >
                <Button 
                  type="link" 
                  danger 
                  icon={<DeleteOutlined />} 
                  size="small"
                  style={{ padding: 0 }}
                >
                  删除
                </Button>
              </Popconfirm>
            )}
          </Space>
        )
      }
    }
  ]

  // 初始化列配置
  useEffect(() => {
    const baseColumns = getBaseColumns()
    const mergedColumns = baseColumns.map((col, index) => {
      // 操作列不需要resize功能
      if (col.resizable === false || col.fixed) {
        return col
      }
      return {
        ...col,
        onHeaderCell: (column) => ({
          width: column.width,
          onResize: handleResize(index)
        })
      }
    })
    setColumns(mergedColumns)
  }, [isAdmin, currentUser?.id, handleResize])

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h1>资产管理</h1>
        <Space>
          {isAdmin && (
            <Upload
              accept=".xlsx,.xls"
              beforeUpload={handleImport}
              showUploadList={false}
            >
              <Button icon={<UploadOutlined />}>批量导入</Button>
            </Upload>
          )}
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增资产
          </Button>
          {isAdmin && (
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExport}
              disabled={isAdmin && !assets.length}
            >
              导出Excel{selectedRowKeys.length > 0 ? `（已选${selectedRowKeys.length}条）` : ''}
            </Button>
          )}
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
            placeholder="搜索资产编号、名称、规格、使用人、组别、存放地点、座位号、备注等"
            style={{ width: 300 }}
            allowClear
          />
        </Form.Item>
        <Form.Item label="所属大类" name="category_id">
          <Select placeholder="全部" style={{ width: 150 }} allowClear>
            {categories.map(cat => (
              <Select.Option key={cat.id} value={cat.id}>{cat.name}</Select.Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item label="状态" name="status">
          <Select placeholder="全部" style={{ width: 120 }} allowClear>
            <Select.Option value="在用">在用</Select.Option>
            <Select.Option value="库存备用">库存备用</Select.Option>
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
        dataSource={assets}
        loading={loading}
        rowKey="id"
        rowSelection={isAdmin ? {
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys)
        } : undefined}
        scroll={{ x: 1055 }}
        components={{
          header: {
            cell: ResizableTitle
          }
        }}
        bordered
        size="small"
      />

      <Modal
        title={editingAsset ? '编辑资产' : '新增资产'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            label="资产编号"
            name="asset_number"
            rules={[{ required: true, message: '请输入资产编号' }]}
          >
            <Input disabled={!!editingAsset} />
          </Form.Item>
          <Form.Item
            label="所属大类"
            name="category_id"
            rules={[{ required: true, message: '请选择所属大类' }]}
          >
            <Select>
              {categories.map(cat => (
                <Select.Option key={cat.id} value={cat.id}>{cat.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="实物名称"
            name="name"
            rules={[{ required: true, message: '请输入实物名称' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="规格型号"
            name="specification"
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="状态"
            name="status"
            rules={[{ required: true, message: '请选择状态' }]}
          >
            <Select>
              <Select.Option value="在用">在用</Select.Option>
              <Select.Option value="库存备用">库存备用</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="MAC地址"
            name="mac_address"
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="IP地址"
            name="ip_address"
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="存放办公地点"
            name="office_location"
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="存放楼层"
            name="floor"
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="座位号"
            name="seat_number"
          >
            <Input placeholder="非必填" />
          </Form.Item>
          <Form.Item
            label="使用人"
            name="user_id"
          >
            <Select allowClear disabled={!isAdmin}>
              {users.map(user => (
                <Select.Option key={user.id} value={user.id}>{user.real_name} ({user.ehr_number})</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="备注说明"
            name="remark"
          >
            <Input.TextArea rows={3} placeholder="非必填" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AssetManagement


import { PlusOutlined, EditOutlined, DeleteOutlined, UploadOutlined, DownloadOutlined, SearchOutlined, ReloadOutlined, HistoryOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api from '../utils/api'
import { useAuth } from '../contexts/AuthContext'
import ResizableTitle from '../components/ResizableTitle'

const AssetManagement = () => {
  const { user: currentUser, isAdmin } = useAuth()
  const navigate = useNavigate()
  const [assets, setAssets] = useState([])
  const [categories, setCategories] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingAsset, setEditingAsset] = useState(null)
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [form] = Form.useForm()
  const [filtersForm] = Form.useForm()
  const [filters, setFilters] = useState({})
  const [columns, setColumns] = useState([])

  useEffect(() => {
    if (currentUser) {
      fetchAssets()
      fetchCategories()
      fetchUsers()
    }
  }, [currentUser])

  const fetchAssets = async (extraFilters) => {
    setLoading(true)
    try {
      const params = { ...filters, ...(extraFilters || {}) }
      const response = await api.get('/assets/', { params })
      setAssets(response.data)
      if (isAdmin) {
        setSelectedRowKeys([])
      }
    } catch (error) {
      message.error('获取资产列表失败')
    } finally {
      setLoading(false)
    }
  }
  const handleSearch = () => {
    const values = filtersForm.getFieldsValue()
    const payload = {
      search: values.keyword || undefined,
      category_id: values.category_id || undefined,
      status: values.status || undefined
    }
    setFilters(payload)
    fetchAssets(payload)
  }

  const handleResetFilters = () => {
    filtersForm.resetFields()
    setFilters({})
    fetchAssets({})
  }


  const fetchCategories = async () => {
    try {
      const response = await api.get('/categories/')
      setCategories(response.data)
    } catch (error) {
      console.error('获取资产大类失败:', error)
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
    setEditingAsset(null)
    form.resetFields()
    if (!isAdmin && currentUser) {
      form.setFieldsValue({ user_id: currentUser.id })
    }
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    // 普通用户只能编辑自己名下的资产
    if (!isAdmin && record.user?.id !== currentUser?.id) {
      message.error('只能编辑自己名下的资产')
      return
    }
    setEditingAsset(record)
    form.setFieldsValue({
      ...record,
      category_id: record.category?.id,
      user_id: record.user?.id
    })
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await api.delete(`/assets/${id}`)
      message.success('删除成功')
      fetchAssets()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values) => {
    try {
      // 普通用户创建/编辑资产时强制绑定到自己
      if (!isAdmin && currentUser) {
        values.user_id = currentUser.id
      }
      if (editingAsset) {
        // 普通用户编辑时提交编辑申请，管理员直接更新
        try {
          const response = await api.put(`/assets/${editingAsset.id}`, values)
          // 检查是否是编辑申请（返回消息包含"编辑申请已提交"）
          if (response.data?.message && response.data.message.includes('编辑申请已提交')) {
            message.success('编辑申请已提交，等待管理员审批')
          } else {
            message.success('更新成功')
          }
        } catch (error) {
          // 处理编辑申请的情况（后端返回200但包含消息）
          if (error.response?.status === 200 && error.response?.data?.message) {
            if (error.response.data.message.includes('编辑申请已提交')) {
              message.success('编辑申请已提交，等待管理员审批')
              setModalVisible(false)
              fetchAssets()
              return
            }
          }
          throw error
        }
      } else {
        await api.post('/assets/', values)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchAssets()
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const handleImport = async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await api.post('/assets/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      const { success_count, error_count, errors } = response.data
      message.success(`导入完成：成功 ${success_count} 条，失败 ${error_count} 条`)
      if (errors.length > 0) {
        console.error('导入错误:', errors)
      }
      fetchAssets()
    } catch (error) {
      message.error('导入失败')
    }
    return false
  }

  const handleExport = async () => {
    if (!isAdmin) return
    try {
      const params = {}
      if (selectedRowKeys.length > 0) {
        params.asset_ids = selectedRowKeys.join(',')
      }
      const response = await api.get('/assets/export', {
        params,
        responseType: 'blob'
      })
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      const timestamp = new Date().toISOString().replace(/[:T]/g, '-').slice(0, 19)
      link.href = url
      link.download = `资产导出_${timestamp}.xlsx`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      message.success('导出成功')
    } catch (error) {
      message.error(error.response?.data?.detail || '导出失败')
    }
  }

  // 处理列宽调整
  const handleResize = useCallback((index) => (e, { size }) => {
    setColumns(prevColumns => {
      const newColumns = [...prevColumns]
      newColumns[index] = {
        ...newColumns[index],
        width: size.width
      }
      return newColumns
    })
  }, [])

  // 定义列配置
  const getBaseColumns = () => [
    {
      title: '资产编号',
      dataIndex: 'asset_number',
      key: 'asset_number',
      width: 90
    },
    {
      title: '所属大类',
      dataIndex: ['category', 'name'],
      key: 'category',
      width: 80
    },
    {
      title: '实物名称',
      dataIndex: 'name',
      key: 'name',
      width: 110,
      ellipsis: true
    },
    {
      title: '规格型号',
      dataIndex: 'specification',
      key: 'specification',
      width: 90,
      ellipsis: true
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 65
    },
    {
      title: '使用人',
      dataIndex: ['user', 'real_name'],
      key: 'user',
      width: 80
    },
    {
      title: '组别',
      dataIndex: 'user_group',
      key: 'user_group',
      width: 80
    },
    {
      title: '存放地点',
      dataIndex: 'office_location',
      key: 'office_location',
      width: 90,
      ellipsis: true
    },
    {
      title: '存放楼层',
      dataIndex: 'floor',
      key: 'floor',
      width: 65
    },
    {
      title: '座位号',
      dataIndex: 'seat_number',
      key: 'seat_number',
      width: 65
    },
    {
      title: '备注说明',
      dataIndex: 'remark',
      key: 'remark',
      width: 90,
      ellipsis: true
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right',
      resizable: false, // 操作列不需要调整宽度
      render: (_, record) => {
        // 普通用户只能编辑自己名下的资产，不能删除
        const canEdit = isAdmin || record.user?.id === currentUser?.id
        const canDelete = isAdmin
        
        return (
          <Space size="small">
            <Button 
              type="link" 
              icon={<HistoryOutlined />} 
              onClick={() => navigate(`/assets/${record.id}/history`)}
              size="small"
              style={{ padding: 0 }}
            >
              流转记录
            </Button>
            {canEdit && (
              <Button 
                type="link" 
                icon={<EditOutlined />} 
                onClick={() => handleEdit(record)} 
                size="small"
                style={{ padding: 0 }}
              >
                编辑
              </Button>
            )}
            {canDelete && (
              <Popconfirm
                title="确定要删除吗？"
                onConfirm={() => handleDelete(record.id)}
              >
                <Button 
                  type="link" 
                  danger 
                  icon={<DeleteOutlined />} 
                  size="small"
                  style={{ padding: 0 }}
                >
                  删除
                </Button>
              </Popconfirm>
            )}
          </Space>
        )
      }
    }
  ]

  // 初始化列配置
  useEffect(() => {
    const baseColumns = getBaseColumns()
    const mergedColumns = baseColumns.map((col, index) => {
      // 操作列不需要resize功能
      if (col.resizable === false || col.fixed) {
        return col
      }
      return {
        ...col,
        onHeaderCell: (column) => ({
          width: column.width,
          onResize: handleResize(index)
        })
      }
    })
    setColumns(mergedColumns)
  }, [isAdmin, currentUser?.id, handleResize])

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h1>资产管理</h1>
        <Space>
          {isAdmin && (
            <Upload
              accept=".xlsx,.xls"
              beforeUpload={handleImport}
              showUploadList={false}
            >
              <Button icon={<UploadOutlined />}>批量导入</Button>
            </Upload>
          )}
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增资产
          </Button>
          {isAdmin && (
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExport}
              disabled={isAdmin && !assets.length}
            >
              导出Excel{selectedRowKeys.length > 0 ? `（已选${selectedRowKeys.length}条）` : ''}
            </Button>
          )}
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
            placeholder="搜索资产编号、名称、规格、使用人、组别、存放地点、座位号、备注等"
            style={{ width: 300 }}
            allowClear
          />
        </Form.Item>
        <Form.Item label="所属大类" name="category_id">
          <Select placeholder="全部" style={{ width: 150 }} allowClear>
            {categories.map(cat => (
              <Select.Option key={cat.id} value={cat.id}>{cat.name}</Select.Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item label="状态" name="status">
          <Select placeholder="全部" style={{ width: 120 }} allowClear>
            <Select.Option value="在用">在用</Select.Option>
            <Select.Option value="库存备用">库存备用</Select.Option>
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
        dataSource={assets}
        loading={loading}
        rowKey="id"
        rowSelection={isAdmin ? {
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys)
        } : undefined}
        scroll={{ x: 1055 }}
        components={{
          header: {
            cell: ResizableTitle
          }
        }}
        bordered
        size="small"
      />

      <Modal
        title={editingAsset ? '编辑资产' : '新增资产'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            label="资产编号"
            name="asset_number"
            rules={[{ required: true, message: '请输入资产编号' }]}
          >
            <Input disabled={!!editingAsset} />
          </Form.Item>
          <Form.Item
            label="所属大类"
            name="category_id"
            rules={[{ required: true, message: '请选择所属大类' }]}
          >
            <Select>
              {categories.map(cat => (
                <Select.Option key={cat.id} value={cat.id}>{cat.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="实物名称"
            name="name"
            rules={[{ required: true, message: '请输入实物名称' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="规格型号"
            name="specification"
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="状态"
            name="status"
            rules={[{ required: true, message: '请选择状态' }]}
          >
            <Select>
              <Select.Option value="在用">在用</Select.Option>
              <Select.Option value="库存备用">库存备用</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="MAC地址"
            name="mac_address"
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="IP地址"
            name="ip_address"
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="存放办公地点"
            name="office_location"
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="存放楼层"
            name="floor"
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="座位号"
            name="seat_number"
          >
            <Input placeholder="非必填" />
          </Form.Item>
          <Form.Item
            label="使用人"
            name="user_id"
          >
            <Select allowClear disabled={!isAdmin}>
              {users.map(user => (
                <Select.Option key={user.id} value={user.id}>{user.real_name} ({user.ehr_number})</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="备注说明"
            name="remark"
          >
            <Input.TextArea rows={3} placeholder="非必填" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AssetManagement

