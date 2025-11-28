import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Timeline, Tag, Button, message, Spin, Descriptions } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import api from '../utils/api'

const AssetHistory = () => {
  const { assetId } = useParams()
  const navigate = useNavigate()
  const [history, setHistory] = useState([])
  const [asset, setAsset] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (assetId) {
      fetchAssetHistory()
      fetchAssetInfo()
    }
  }, [assetId])

  const fetchAssetHistory = async () => {
    setLoading(true)
    try {
      const response = await api.get(`/asset-history/asset/${assetId}`)
      setHistory(response.data)
    } catch (error) {
      message.error(error.response?.data?.detail || '获取流转记录失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchAssetInfo = async () => {
    try {
      const response = await api.get(`/assets/${assetId}`)
      setAsset(response.data)
    } catch (error) {
      console.error('获取资产信息失败:', error)
    }
  }

  const getActionTypeColor = (actionType) => {
    const colorMap = {
      create: 'green',
      edit: 'blue',
      transfer: 'orange',
      return: 'purple',
      approve: 'cyan',
      delete: 'red'
    }
    return colorMap[actionType] || 'default'
  }

  const getActionTypeText = (actionType) => {
    const textMap = {
      create: '创建资产',
      edit: '编辑资产',
      transfer: '资产交接',
      return: '资产退回',
      approve: '审批操作',
      delete: '删除资产'
    }
    return textMap[actionType] || actionType
  }

  // 字段名映射：将数据库字段名转换为表单上的中文名称
  const getFieldLabel = (fieldName) => {
    const fieldMap = {
      asset_number: '资产编号',
      category_id: '所属大类',
      name: '实物名称',
      specification: '规格型号',
      status: '状态',
      mac_address: 'MAC地址',
      ip_address: 'IP地址',
      office_location: '存放办公地点',
      floor: '存放楼层',
      seat_number: '座位号',
      user_id: '使用人',
      user_group: '组别',
      remark: '备注说明'
    }
    return fieldMap[fieldName] || fieldName
  }

  // 格式化字段值显示（处理特殊字段）
  const formatFieldValue = (fieldName, value) => {
    if (value == null || value === '') {
      return '(空)'
    }
    // 对于 user_id，可能需要显示用户名称，但这里先显示ID，因为历史记录中可能没有用户对象
    // 如果后续需要显示用户名称，可以在后端返回时关联用户信息
    return value
  }

  const renderHistoryItem = (item) => {
    let content = item.action_description || ''
    const details = []

    // 解析新旧值
    let oldValue = null
    let newValue = null
    try {
      if (item.old_value) oldValue = JSON.parse(item.old_value)
      if (item.new_value) newValue = JSON.parse(item.new_value)
    } catch (e) {
      console.error('解析JSON失败:', e)
    }

    // 根据操作类型显示详细信息
    if (item.action_type === 'edit' && oldValue && newValue) {
      const changedFields = Object.keys(newValue).filter(key => oldValue[key] !== newValue[key])
      if (changedFields.length > 0) {
        details.push(
          <div key="changes" style={{ marginTop: 8, padding: 8, background: '#f5f5f5', borderRadius: 4 }}>
            {changedFields.map(field => (
              <div key={field} style={{ marginBottom: 4 }}>
                <strong>{getFieldLabel(field)}:</strong> {formatFieldValue(field, oldValue[field])} → {formatFieldValue(field, newValue[field])}
              </div>
            ))}
          </div>
        )
      }
    } else if (item.action_type === 'transfer' && oldValue && newValue) {
      details.push(
        <div key="transfer" style={{ marginTop: 8, padding: 8, background: '#fff7e6', borderRadius: 4 }}>
          <div>从: {oldValue.user_name || '(空)'}</div>
          <div>到: {newValue.user_name || '(空)'}</div>
        </div>
      )
    } else if (item.action_type === 'return' && oldValue && newValue) {
      details.push(
        <div key="return" style={{ marginTop: 8, padding: 8, background: '#f6ffed', borderRadius: 4 }}>
          <div>退回人: {oldValue.user_name || '(空)'}</div>
          <div>状态变更: {oldValue.status} → {newValue.status}</div>
        </div>
      )
    }

    return (
      <div>
        <div>{content}</div>
        {details}
        <div style={{ marginTop: 8, fontSize: '12px', color: '#999' }}>
          {item.operator && `操作人: ${item.operator.real_name} (${item.operator.ehr_number})`}
          {item.approver && ` | 审批人: ${item.approver.real_name} (${item.approver.ehr_number})`}
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/assets')}>
          返回
        </Button>
        <h1 style={{ margin: 0 }}>资产流转记录</h1>
      </div>

      {asset && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions title="资产信息" bordered column={3}>
            <Descriptions.Item label="资产编号">{asset.asset_number}</Descriptions.Item>
            <Descriptions.Item label="资产名称">{asset.name}</Descriptions.Item>
            <Descriptions.Item label="所属大类">{asset.category?.name}</Descriptions.Item>
            <Descriptions.Item label="规格型号">{asset.specification || '-'}</Descriptions.Item>
            <Descriptions.Item label="状态">{asset.status}</Descriptions.Item>
            <Descriptions.Item label="使用人">{asset.user?.real_name || '-'}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Card>
        <Spin spinning={loading}>
          {history.length > 0 ? (
            <Timeline
              mode="left"
              items={history.map((item, index) => ({
                color: getActionTypeColor(item.action_type),
                children: (
                  <div>
                    <div style={{ marginBottom: 8 }}>
                      <Tag color={getActionTypeColor(item.action_type)}>
                        {getActionTypeText(item.action_type)}
                      </Tag>
                      <span style={{ marginLeft: 8, color: '#666' }}>
                        {new Date(item.created_at).toLocaleString('zh-CN')}
                      </span>
                    </div>
                    {renderHistoryItem(item)}
                  </div>
                )
              }))}
            />
          ) : (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              暂无流转记录
            </div>
          )}
        </Spin>
      </Card>
    </div>
  )
}

export default AssetHistory
