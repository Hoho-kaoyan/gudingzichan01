import React, { useState, useEffect } from 'react'
import { Card, Button, Tabs, Row, Col, Modal, Form, Radio, Input, message, Space, Tag, Steps } from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  FileTextOutlined,
  SafetyCertificateOutlined,
  UnorderedListOutlined,
  CalendarOutlined,
  PlayCircleOutlined,
  HistoryOutlined
} from '@ant-design/icons'
import api from '../utils/api'
import { useAuth } from '../contexts/AuthContext'
import { useTransfer } from '../contexts/TransferContext'
import dayjs from 'dayjs'

const { TextArea } = Input

const MySafetyCheckTasks = () => {
  const { user } = useAuth()
  const { refreshPendingSafetyChecks, syncPendingSafetyCheckCountFromTasks } = useTransfer()
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('pending')
  const [checkModalVisible, setCheckModalVisible] = useState(false)
  const [currentTask, setCurrentTask] = useState(null)
  const [currentAssets, setCurrentAssets] = useState([])
  const [currentAssetIndex, setCurrentAssetIndex] = useState(0)
  const [form] = Form.useForm()

  // 一次拉取全部任务，用于 Tab 计数与按 Tab 过滤展示，避免切换 Tab 时另一侧数字变 0
  useEffect(() => {
    fetchMyTasks()
  }, [])

  const fetchMyTasks = async () => {
    setLoading(true)
    try {
      const response = await api.get('/safety-check-results/my-tasks')
      const items = response.data?.items ?? []
      console.log('[侧栏-待检查] MySafetyCheckTasks fetchMyTasks 成功', { itemsLength: items.length, pendingCounts: items.map(t => t?.pending_count ?? t?.pendingCount) })
      setTasks(items)
      syncPendingSafetyCheckCountFromTasks(items)
    } catch (error) {
      console.error('[侧栏-待检查] MySafetyCheckTasks fetchMyTasks 失败', error?.response?.status, error?.response?.data)
      message.error('获取任务列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleStartCheck = async (taskId) => {
    try {
      const response = await api.get(`/safety-check-results/task/${taskId}/assets`)
      const assets = response.data.assets || []
      if (assets.length === 0) {
        message.warning('该任务没有分配的资产')
        return
      }
      setCurrentTask({
        ...response.data.task,
        check_type: response.data.check_type
      })
      setCurrentAssets(assets)
      setCurrentAssetIndex(0)
      form.resetFields()
      setCheckModalVisible(true)
      
      // 如果有未完成的资产（待检查或已逾期），定位到第一个
      const firstUnfinishedIndex = assets.findIndex(a => a.status === 'pending' || a.status === 'overdue')
      if (firstUnfinishedIndex >= 0) {
        setCurrentAssetIndex(firstUnfinishedIndex)
      }
    } catch (error) {
      console.error('获取任务详情失败:', error)
      message.error(error.response?.data?.detail || '获取任务详情失败')
    }
  }

  const handleNextAsset = () => {
    if (currentAssetIndex < currentAssets.length - 1) {
      setCurrentAssetIndex(currentAssetIndex + 1)
      form.resetFields()
      loadCurrentAssetData()
    }
  }

  const handlePrevAsset = () => {
    if (currentAssetIndex > 0) {
      setCurrentAssetIndex(currentAssetIndex - 1)
      form.resetFields()
      loadCurrentAssetData()
    }
  }

  const loadCurrentAssetData = () => {
    if (currentAssets.length === 0 || currentAssetIndex < 0 || currentAssetIndex >= currentAssets.length) {
      form.resetFields()
      return
    }
    const currentAsset = currentAssets[currentAssetIndex]
    if (currentAsset && Array.isArray(currentAsset.check_items_result) && currentAsset.check_items_result.length > 0) {
      // 如果有已保存的结果，加载到表单
      const itemsResult = {}
      currentAsset.check_items_result.forEach((item, index) => {
        if (item && item.result) {
          itemsResult[`item_${index}`] = item.result
          itemsResult[`comment_${index}`] = item.comment || ''
        }
      })
      form.setFieldsValue({
        check_comment: currentAsset.check_comment || '',
        ...itemsResult
      })
    } else {
      form.resetFields()
    }
  }

  useEffect(() => {
    if (checkModalVisible && currentAssets.length > 0 && currentAssetIndex >= 0 && currentAssetIndex < currentAssets.length) {
      loadCurrentAssetData()
    }
  }, [currentAssetIndex, checkModalVisible, currentAssets.length])

  const handleSubmitCheck = async () => {
    try {
      const values = await form.validateFields()
      const currentAsset = currentAssets[currentAssetIndex]
      const checkType = currentTask?.check_type

      // 构建检查项结果
      const checkItemsResult = []
      if (checkType && checkType.check_items) {
        checkType.check_items.forEach((item, index) => {
          const result = values[`item_${index}`]
          const comment = values[`comment_${index}`]
          if (result) {
            checkItemsResult.push({
              item: item.item,
              result: result,
              comment: comment || ''
            })
          }
        })
      }

      const overallResult = checkItemsResult.some(item => item.result === 'no') ? 'no' : 'yes'

      const payload = {
        task_asset_id: currentAsset.id,
        check_result: overallResult,
        check_comment: values.check_comment,
        check_items_result: checkItemsResult
      }

      await api.post('/safety-check-results/submit', payload)
      message.success('检查结果提交成功')

      // 更新本地状态
      const updatedAssets = [...currentAssets]
      updatedAssets[currentAssetIndex] = {
        ...currentAsset,
        status: 'checked',
        check_result: overallResult,
        check_comment: values.check_comment,
        check_items_result: checkItemsResult
      }
      setCurrentAssets(updatedAssets)

      // 如果还有未完成的资产（待检查或已逾期），继续下一个
      const nextUnfinishedIndex = updatedAssets.findIndex((a, idx) => idx > currentAssetIndex && (a.status === 'pending' || a.status === 'overdue'))
      if (nextUnfinishedIndex >= 0) {
        setCurrentAssetIndex(nextUnfinishedIndex)
        form.resetFields()
      } else {
        // 全部完成，关闭弹窗
        setCheckModalVisible(false)
        fetchMyTasks()
      }
      // 刷新待检查任务数量
      refreshPendingSafetyChecks()
    } catch (error) {
      message.error(error.response?.data?.detail || '提交失败')
    }
  }

  // 待检查数/红点仅统计 pending；已逾期单独 Tab（方案 B）
  const pendingTasks = tasks.filter(t => (t.pending_count || 0) > 0)
  const overdueTasks = tasks.filter(t => (t.overdue_count || 0) > 0)
  const completedTasks = tasks.filter(t => (t.pending_count || 0) === 0 && (t.overdue_count || 0) === 0)

  const displayedTasks = activeTab === 'pending'
    ? pendingTasks
    : activeTab === 'overdue'
      ? overdueTasks
      : activeTab === 'checked'
        ? completedTasks
        : tasks

  const tabLabelStyle = { display: 'inline-flex', alignItems: 'center', gap: 8 }
  const tabItems = [
    {
      key: 'pending',
      label: (
        <span style={tabLabelStyle}>
          <ClockCircleOutlined />
          待检查 ({pendingTasks.length})
        </span>
      )
    },
    {
      key: 'overdue',
      label: (
        <span style={tabLabelStyle}>
          <HistoryOutlined />
          已逾期 ({overdueTasks.length})
        </span>
      )
    },
    {
      key: 'checked',
      label: (
        <span style={tabLabelStyle}>
          <CheckCircleOutlined />
          已完成 ({completedTasks.length})
        </span>
      )
    }
  ]

  // 方案二：大卡片 + 明确信息层级（2~3 列网格，顶部标题+状态，中部信息+图标，底部操作）
  const renderTaskCard = (task) => {
    const isPending = (task.pending_count || 0) > 0
    const isOverdue = (task.overdue_count || 0) > 0

    return (
      <Card
        key={task.task_id}
        style={{ marginBottom: 16 }}
        actions={[
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleStartCheck(task.task_id)}
          >
            查看详情
          </Button>,
          (isPending || isOverdue) && (
            <Button
              type="primary"
              onClick={() => handleStartCheck(task.task_id)}
            >
              {isOverdue ? '补检' : '开始检查'}
            </Button>
          )
        ].filter(Boolean)}
      >
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <h3>{task.task_title}</h3>
            <Space>
              {isPending && <Tag color="processing">待检查</Tag>}
              {isOverdue && <Tag color="error">已逾期</Tag>}
              {!isPending && !isOverdue && <Tag color="success">已完成</Tag>}
            </Space>
          </div>
          <p><strong>任务编号:</strong> {task.task_number}</p>
          <p><strong>检查类型:</strong> {task.check_type?.name || '-'}</p>
          <p><strong>{isOverdue ? '已逾期:' : '待检查:'}</strong> {isOverdue ? (task.overdue_count || 0) : (task.pending_count || 0)}项</p>
          {task.deadline && (
            <p><strong>截止时间:</strong> {dayjs(task.deadline).format('YYYY-MM-DD HH:mm')}</p>
          )}
        </div>
      </Card>
    )
  }

  const currentAsset = currentAssets.length > 0 && currentAssetIndex >= 0 && currentAssetIndex < currentAssets.length 
    ? currentAssets[currentAssetIndex] 
    : null
  const checkType = currentTask?.check_type || null

  return (
    <div>
      <style>{`
        .my-safety-check-task-card:hover {
          box-shadow: 0 4px 16px rgba(0,0,0,0.12);
          border-color: #d9d9d9 !important;
        }
      `}</style>
      <h2>我的安全检查任务</h2>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        style={{ marginTop: 16 }}
      />

      <div style={{ marginTop: 16 }}>
        {displayedTasks.length === 0 ? (
          <Card>
            <div style={{ textAlign: 'center', padding: 40 }}>
              <p>暂无任务</p>
            </div>
          </Card>
        ) : (
          <Row gutter={[20, 20]}>
            {displayedTasks.map(task => renderTaskCard(task))}
          </Row>
        )}
      </div>

      <Modal
        title={`安全检查: ${currentTask?.task_number || currentTask?.task_title || ''}`}
        open={checkModalVisible}
        onCancel={() => {
          setCheckModalVisible(false)
          setCurrentTask(null)
          setCurrentAssets([])
          setCurrentAssetIndex(0)
          form.resetFields()
        }}
        width={900}
        footer={null}
        destroyOnClose
      >
        {currentAssets.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <p>暂无资产数据</p>
          </div>
        ) : currentAsset ? (
          <div>
            <div style={{ marginBottom: 24 }}>
              <Steps
                current={currentAssetIndex}
                items={currentAssets.map((asset, index) => {
                  let status = 'wait'; // 默认等待状态
                  
                  if (index === currentAssetIndex) {
                    // 当前正在检查的资产
                    status = 'process';
                  } else if (asset.status === 'checked') {
                    // 已完成的资产
                    status = 'finish';
                  }
                  // 其他情况保持 wait 状态
                  
                  return {
                    title: asset.asset?.asset_number || `资产${index + 1}`,
                    status: status
                  };
                })}
              />
            </div>

            <Card title={`资产: ${currentAsset.asset?.asset_number} - ${currentAsset.asset?.name}`}>
              <div style={{ marginBottom: 16 }}>
                <p><strong>使用人:</strong> {currentAsset.asset?.user?.real_name || '-'}</p>
                <p><strong>存放地点:</strong> {currentAsset.asset?.office_location || '-'} {currentAsset.asset?.floor || ''}</p>
              </div>

              <Form form={form} layout="vertical">
                {checkType && Array.isArray(checkType.check_items) && checkType.check_items.length > 0 && (
                  <div style={{ marginBottom: 24 }}>
                    <h4>检查项:</h4>
                    {checkType.check_items.map((item, index) => (
                      <div key={index} style={{ marginBottom: 16, padding: 16, border: '1px solid #d9d9d9', borderRadius: 4 }}>
                        <Form.Item
                          label={
                            <span>
                              {index + 1}. {item.item}
                              {item.required && <Tag color="red" style={{ marginLeft: 8 }}>必填</Tag>}
                            </span>
                          }
                          name={`item_${index}`}
                          rules={item.required ? [{ required: true, message: '请选择检查结果' }] : []}
                        >
                          <Radio.Group>
                            <Radio value="yes">是</Radio>
                            <Radio value="no">否</Radio>
                          </Radio.Group>
                        </Form.Item>
                        <Form.Item
                          label="备注"
                          name={`comment_${index}`}
                        >
                          <TextArea rows={2} placeholder="备注（可选）" />
                        </Form.Item>
                      </div>
                    ))}
                  </div>
                )}

                <Form.Item
                  label="检查备注"
                  name="check_comment"
                >
                  <TextArea rows={3} placeholder="检查备注（可选）" />
                </Form.Item>
              </Form>
            </Card>

            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                <Button onClick={() => setCheckModalVisible(false)}>取消</Button>
                {currentAssetIndex > 0 && (
                  <Button onClick={handlePrevAsset}>上一个</Button>
                )}
                {currentAssetIndex < currentAssets.length - 1 && (
                  <Button onClick={handleNextAsset}>下一个</Button>
                )}
                {currentAsset.status === 'pending' && (
                  <Button type="primary" onClick={handleSubmitCheck}>
                    提交检查结果
                  </Button>
                )}
                {currentAsset.status === 'checked' && (
                  <Tag color="success">已检查</Tag>
                )}
              </Space>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <p>加载中...</p>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default MySafetyCheckTasks

