import React, { useState, useEffect } from 'react'
import { Table, Tabs, Button, Modal, Form, Input, message, Tag, Space, Descriptions, Divider } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import api from '../utils/api'

const ApprovalManagement = () => {
  const [transfers, setTransfers] = useState([])
  const [returns, setReturns] = useState([])
  const [loading, setLoading] = useState(false)
  const [approvalModalVisible, setApprovalModalVisible] = useState(false)
  const [currentRequest, setCurrentRequest] = useState(null)
  const [approvalDecision, setApprovalDecision] = useState(true)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchTransfers()
    fetchReturns()
  }, [])

  const fetchTransfers = async () => {
    setLoading(true)
    try {
      const response = await api.get('/transfers/', { params: { status: 'pending' } })
      setTransfers(response.data)
    } catch (error) {
      message.error('获取交接申请列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchReturns = async () => {
    setLoading(true)
    try {
      const response = await api.get('/returns/', { params: { status: 'pending' } })
      setReturns(response.data)
    } catch (error) {
      message.error('获取退回申请列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = (request, type) => {
    setCurrentRequest({ ...request, type })
    setApprovalDecision(true)
    form.setFieldsValue({ approved: true, comment: '' })
    setApprovalModalVisible(true)
  }

  const handleApprovalSubmit = async (values) => {
    try {
      await api.post('/approvals/approve', {
        request_id: currentRequest.id,
        request_type: currentRequest.type,
        approved: values.approved,
        comment: values.comment
      })
      message.success('审批完成')
      setApprovalModalVisible(false)
      fetchTransfers()
      fetchReturns()
    } catch (error) {
      message.error(error.response?.data?.detail || '审批失败')
    }
  }

  const transferColumns = [
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
      title: '转出人',
      dataIndex: ['from_user', 'real_name'],
      key: 'from_user'
    },
    {
      title: '转入人',
      dataIndex: ['to_user', 'real_name'],
      key: 'to_user'
    },
    {
      title: '交接原因',
      dataIndex: 'reason',
      key: 'reason'
    },
    {
      title: '申请时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) => text ? new Date(text).toLocaleString('zh-CN') : '-'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            onClick={() => handleApprove(record, 'transfer')}
          >
            审批
          </Button>
        </Space>
      )
    }
  ]

  const returnColumns = [
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
      key: 'reason'
    },
    {
      title: '申请时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) => text ? new Date(text).toLocaleString('zh-CN') : '-'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            onClick={() => handleApprove(record, 'return')}
          >
            审批
          </Button>
        </Space>
      )
    }
  ]

  const tabItems = [
    {
      key: 'transfers',
      label: `交接申请 (${transfers.length})`,
      children: (
        <Table
          columns={transferColumns}
          dataSource={transfers}
          loading={loading}
          rowKey="id"
        />
      )
    },
    {
      key: 'returns',
      label: `退回申请 (${returns.length})`,
      children: (
        <Table
          columns={returnColumns}
          dataSource={returns}
          loading={loading}
          rowKey="id"
        />
      )
    },
    {
      key: 'edits',
      label: `编辑申请 (${edits.length})`,
      children: (
        <Table
          columns={editColumns}
          dataSource={edits}
          loading={loading}
          rowKey="id"
        />
      )
    }
  ]

  return (
    <div>
      <h1>审批管理</h1>
      <Tabs items={tabItems} />

      <Modal
        title={`审批${currentRequest?.type === 'transfer' ? '交接' : currentRequest?.type === 'return' ? '退回' : '编辑'}申请`}
        open={approvalModalVisible}
        onCancel={() => setApprovalModalVisible(false)}
        onOk={() => form.submit()}
        width={700}
      >
        {/* 显示申请详情 */}
        {currentRequest && (
          <>
            <Descriptions title="申请信息" bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="资产编号">
                {currentRequest.asset?.asset_number || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="资产名称">
                {currentRequest.asset?.name || '-'}
              </Descriptions.Item>
              {currentRequest.type === 'transfer' ? (
                <>
                  <Descriptions.Item label="转出人">
                    {currentRequest.from_user?.real_name || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="转入人">
                    {currentRequest.to_user?.real_name || '-'}
                  </Descriptions.Item>
                </>
              ) : currentRequest.type === 'return' ? (
                <>
                  <Descriptions.Item label="退回人">
                    {currentRequest.user?.real_name || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="退回原因">
                    {currentRequest.reason || '-'}
                  </Descriptions.Item>
                </>
              ) : (
                <>
                  <Descriptions.Item label="申请人">
                    {currentRequest.user?.real_name || '-'}
                  </Descriptions.Item>
                </>
              )}
            </Descriptions>

            {/* 显示申请人修改的字段（退回申请和编辑申请） */}
            {(currentRequest.type === 'return' || currentRequest.type === 'edit') && (
              <>
                <Divider orientation="left" style={{ margin: '16px 0' }}>
                  <span style={{ fontSize: '14px', fontWeight: 'bold' }}>申请人修改的信息</span>
                </Divider>
                <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
                  {/* 编辑申请显示 edit_data */}
                  {currentRequest.type === 'edit' && currentRequest.edit_data && (
                    <>
                      {Object.entries(currentRequest.edit_data).map(([key, value]) => {
                        const labelMap = {
                          name: '实物名称',
                          specification: '规格型号',
                          status: '状态',
                          mac_address: 'MAC地址',
                          ip_address: 'IP地址',
                          office_location: '存放地点',
                          floor: '存放楼层',
                          seat_number: '座位号',
                          remark: '备注说明'
                        }
                        return (
                          <Descriptions.Item key={key} label={labelMap[key] || key} span={key === 'remark' ? 2 : 1}>
                            {value === null || value === '' ? '(清空)' : String(value)}
                          </Descriptions.Item>
                        )
                      })}
                    </>
                  )}
                  {/* 退回申请显示修改的字段 */}
                  {currentRequest.type === 'return' && currentRequest.mac_address !== undefined && currentRequest.mac_address !== null && (
                    <Descriptions.Item label="MAC地址">
                      {currentRequest.mac_address || '(清空)'}
                    </Descriptions.Item>
                  )}
                  {currentRequest.ip_address !== undefined && currentRequest.ip_address !== null && (
                    <Descriptions.Item label="IP地址">
                      {currentRequest.ip_address || '(清空)'}
                    </Descriptions.Item>
                  )}
                  {currentRequest.office_location !== undefined && currentRequest.office_location !== null && (
                    <Descriptions.Item label="存放地点">
                      {currentRequest.office_location || '(清空)'}
                    </Descriptions.Item>
                  )}
                  {currentRequest.floor !== undefined && currentRequest.floor !== null && (
                    <Descriptions.Item label="存放楼层">
                      {currentRequest.floor || '(清空)'}
                    </Descriptions.Item>
                  )}
                  {currentRequest.seat_number !== undefined && currentRequest.seat_number !== null && (
                    <Descriptions.Item label="座位号">
                      {currentRequest.seat_number || '(清空)'}
                    </Descriptions.Item>
                  )}
                  {currentRequest.new_user_id && (
                    <Descriptions.Item label="新保管人">
                      {currentRequest.new_user?.real_name || `ID: ${currentRequest.new_user_id}`}
                      {currentRequest.new_user?.group && ` (${currentRequest.new_user.group})`}
                    </Descriptions.Item>
                  )}
                  {currentRequest.remark !== undefined && currentRequest.remark !== null && (
                    <Descriptions.Item label="备注说明" span={2}>
                      {currentRequest.remark || '(清空)'}
                    </Descriptions.Item>
                  )}
                  {currentRequest.mac_address === undefined && 
                   currentRequest.ip_address === undefined && 
                   currentRequest.office_location === undefined && 
                   currentRequest.floor === undefined && 
                   currentRequest.seat_number === undefined && 
                   !currentRequest.new_user_id && 
                   currentRequest.remark === undefined && (
                    <Descriptions.Item span={2}>
                      <span style={{ color: '#999' }}>申请人未修改任何字段，审批通过后资产将退回仓库</span>
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </>
            )}
          </>
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={handleApprovalSubmit}
          initialValues={{ approved: true }}
        >
          <Form.Item
            label="审批结果"
            name="approved"
            rules={[{ required: true }]}
          >
            <Space>
              <Button
                type={approvalDecision === true ? 'primary' : 'default'}
                onClick={() => {
                  setApprovalDecision(true)
                  form.setFieldsValue({ approved: true })
                }}
                icon={<CheckCircleOutlined />}
              >
                批准
              </Button>
              <Button
                type={approvalDecision === false ? 'primary' : 'default'}
                danger
                onClick={() => {
                  setApprovalDecision(false)
                  form.setFieldsValue({ approved: false })
                }}
                icon={<CloseCircleOutlined />}
              >
                拒绝
              </Button>
            </Space>
          </Form.Item>
          <Form.Item
            label="审批意见"
            name="comment"
          >
            <Input.TextArea rows={4} placeholder="请输入审批意见（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ApprovalManagement


import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import api from '../utils/api'

const ApprovalManagement = () => {
  const [transfers, setTransfers] = useState([])
  const [returns, setReturns] = useState([])
  const [loading, setLoading] = useState(false)
  const [approvalModalVisible, setApprovalModalVisible] = useState(false)
  const [currentRequest, setCurrentRequest] = useState(null)
  const [approvalDecision, setApprovalDecision] = useState(true)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchTransfers()
    fetchReturns()
  }, [])

  const fetchTransfers = async () => {
    setLoading(true)
    try {
      const response = await api.get('/transfers/', { params: { status: 'pending' } })
      setTransfers(response.data)
    } catch (error) {
      message.error('获取交接申请列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchReturns = async () => {
    setLoading(true)
    try {
      const response = await api.get('/returns/', { params: { status: 'pending' } })
      setReturns(response.data)
    } catch (error) {
      message.error('获取退回申请列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = (request, type) => {
    setCurrentRequest({ ...request, type })
    setApprovalDecision(true)
    form.setFieldsValue({ approved: true, comment: '' })
    setApprovalModalVisible(true)
  }

  const handleApprovalSubmit = async (values) => {
    try {
      await api.post('/approvals/approve', {
        request_id: currentRequest.id,
        request_type: currentRequest.type,
        approved: values.approved,
        comment: values.comment
      })
      message.success('审批完成')
      setApprovalModalVisible(false)
      fetchTransfers()
      fetchReturns()
    } catch (error) {
      message.error(error.response?.data?.detail || '审批失败')
    }
  }

  const transferColumns = [
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
      title: '转出人',
      dataIndex: ['from_user', 'real_name'],
      key: 'from_user'
    },
    {
      title: '转入人',
      dataIndex: ['to_user', 'real_name'],
      key: 'to_user'
    },
    {
      title: '交接原因',
      dataIndex: 'reason',
      key: 'reason'
    },
    {
      title: '申请时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) => text ? new Date(text).toLocaleString('zh-CN') : '-'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            onClick={() => handleApprove(record, 'transfer')}
          >
            审批
          </Button>
        </Space>
      )
    }
  ]

  const returnColumns = [
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
      key: 'reason'
    },
    {
      title: '申请时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) => text ? new Date(text).toLocaleString('zh-CN') : '-'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            onClick={() => handleApprove(record, 'return')}
          >
            审批
          </Button>
        </Space>
      )
    }
  ]

  const tabItems = [
    {