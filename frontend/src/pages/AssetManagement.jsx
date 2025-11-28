import React, { useState, useEffect, useCallback } from 'react'
import { Table, Button, Modal, Form, Input, Select, Upload, message, Popconfirm, Space, Tag, Descriptions, Divider } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, UploadOutlined, DownloadOutlined, SearchOutlined, ReloadOutlined, HistoryOutlined, FileTextOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api from '../utils/api'
import { useAuth } from '../contexts/AuthContext'
import ResizableTitle from '../components/ResizableTitle'
import dayjs from 'dayjs'

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
  const [editRequests, setEditRequests] = useState([]) // 存储编辑申请列表
  const [editRequestModalVisible, setEditRequestModalVisible] = useState(false)
  const [currentEditRequest, setCurrentEditRequest] = useState(null)

  useEffect(() => {
    if (currentUser) {
      fetchAssets()
      fetchCategories()
      fetchUsers()
      // 普通用户获取编辑申请列表
      if (!isAdmin) {
        fetchEditRequests()
      }
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

  const fetchEditRequests = async () => {
    try {
      const response = await api.get('/edit-requests/')
      setEditRequests(response.data || [])
    } catch (error) {
      console.error('获取编辑申请列表失败:', error)
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
        // 普通用户不能修改状态，移除status字段
        if (values.status) {
          delete values.status
        }
      }
      if (editingAsset) {
        try {
          const response = await api.put(`/assets/${editingAsset.id}`, values)
          // 检查是否是编辑申请（普通用户提交申请）
          if (response.data && response.data.message && response.data.message.includes('编辑申请已提交')) {
            message.success('编辑申请已提交，等待管理员审批')
          } else {
            message.success('更新成功')
          }
        } catch (error) {
          // 如果后端返回200但包含编辑申请信息，也视为成功
          if (error.response && error.response.status === 200 && error.response.data && error.response.data.message) {
            if (error.response.data.message.includes('编辑申请已提交')) {
              message.success('编辑申请已提交，等待管理员审批')
              setModalVisible(false)
              fetchAssets()
              // 刷新编辑申请列表
              if (!isAdmin) {
                fetchEditRequests()
              }
              return
            }
          }
          throw error
        }
      } else {
        // 新增资产时，普通用户不能设置状态
        if (!isAdmin && values.status) {
          delete values.status
        }
        await api.post('/assets/', values)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchAssets()
      // 普通用户提交编辑申请后，刷新编辑申请列表
      if (!isAdmin) {
        fetchEditRequests()
      }
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

  // 获取资产的编辑申请状态
  const getAssetEditRequest = (assetId) => {
    return editRequests.find(req => req.asset_id === assetId)
  }

  // 查看编辑申请详情
  const handleViewEditRequest = async (assetId) => {
    const request = getAssetEditRequest(assetId)
    if (request) {
      try {
        // 获取完整的申请详情
        const response = await api.get(`/edit-requests/${request.id}`)
        setCurrentEditRequest(response.data)
        setEditRequestModalVisible(true)
      } catch (error) {
        message.error('获取编辑申请详情失败')
      }
    }
  }

  // 定义列配置
  const getBaseColumns = () => {
    const baseColumns = [
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
    }
    ]

    // 普通用户添加编辑申请状态列
    if (!isAdmin) {
      baseColumns.push({
        title: '编辑申请',
        key: 'edit_request',
        width: 100,
        render: (_, record) => {
          const request = getAssetEditRequest(record.id)
          if (request) {
            let statusColor = 'default'
            let statusText = '待审批'
            if (request.status === 'approved') {
              statusColor = 'success'
              statusText = '已通过'
            } else if (request.status === 'rejected') {
              statusColor = 'error'
              statusText = '已拒绝'
            }
            return (
              <Space size="small" direction="vertical">
                <Tag color={statusColor}>{statusText}</Tag>
                <Button
                  type="link"
                  icon={<FileTextOutlined />}
                  onClick={() => handleViewEditRequest(record.id)}
                  size="small"
                  style={{ padding: 0, fontSize: '12px' }}
                >
                  查看详情
                </Button>
              </Space>
            )
          }
          return null
        }
      })
    }

    baseColumns.push({
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
    })

    return baseColumns
  }

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
          {isAdmin && (
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
          )}
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

      {/* 编辑申请详情模态框 */}
      <Modal
        title="编辑申请详情"
        open={editRequestModalVisible}
        onCancel={() => {
          setEditRequestModalVisible(false)
          setCurrentEditRequest(null)
        }}
        footer={[
          <Button key="close" onClick={() => {
            setEditRequestModalVisible(false)
            setCurrentEditRequest(null)
          }}>
            关闭
          </Button>
        ]}
        width={700}
      >
        {currentEditRequest && (
          <div>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="资产编号" span={2}>
                {currentEditRequest.asset?.asset_number || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="资产名称" span={2}>
                {currentEditRequest.asset?.name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="申请时间">
                {currentEditRequest.created_at ? dayjs(currentEditRequest.created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="审批状态">
                {currentEditRequest.status === 'pending' && <Tag color="orange">待审批</Tag>}
                {currentEditRequest.status === 'approved' && <Tag color="green">已通过</Tag>}
                {currentEditRequest.status === 'rejected' && <Tag color="red">已拒绝</Tag>}
              </Descriptions.Item>
              {currentEditRequest.approver && (
                <>
                  <Descriptions.Item label="审批人">
                    {currentEditRequest.approver.real_name} ({currentEditRequest.approver.ehr_number})
                  </Descriptions.Item>
                  <Descriptions.Item label="审批时间">
                    {currentEditRequest.approved_at ? dayjs(currentEditRequest.approved_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
                  </Descriptions.Item>
                </>
              )}
              {currentEditRequest.approval_comment && (
                <Descriptions.Item label="审批意见" span={2}>
                  {currentEditRequest.approval_comment}
                </Descriptions.Item>
              )}
            </Descriptions>

            {currentEditRequest.edit_data && Object.keys(currentEditRequest.edit_data).length > 0 && (
              <>
                <Divider>申请修改的字段</Divider>
                <Descriptions bordered column={2} size="small">
                  {Object.entries(currentEditRequest.edit_data).map(([key, value]) => {
                    // 字段名称映射
                    const fieldNames = {
                      name: '实物名称',
                      specification: '规格型号',
                      status: '状态',
                      mac_address: 'MAC地址',
                      ip_address: 'IP地址',
                      office_location: '存放办公地点',
                      floor: '存放楼层',
                      seat_number: '座位号',
                      user_group: '使用人组别',
                      remark: '备注说明'
                    }
                    return (
                      <Descriptions.Item key={key} label={fieldNames[key] || key}>
                        {value || '-'}
                      </Descriptions.Item>
                    )
                  })}
                </Descriptions>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default AssetManagement
