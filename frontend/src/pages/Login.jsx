import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'

const Login = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [ehrChecked, setEhrChecked] = useState(false)
  const [userName, setUserName] = useState('')
  const navigate = useNavigate()
  const { login, checkEHR } = useAuth()

  const handleEHRBlur = async () => {
    const ehrNumber = form.getFieldValue('ehr_number')
    if (ehrNumber && ehrNumber.length === 7) {
      const result = await checkEHR(ehrNumber)
      if (result.exists) {
        setEhrChecked(true)
        setUserName(result.real_name)
        message.success(`欢迎，${result.real_name}`)
      } else {
        setEhrChecked(false)
        setUserName('')
        message.error('EHR号不存在')
      }
    }
  }

  const handleSubmit = async (values) => {
    if (!ehrChecked) {
      message.warning('请先验证EHR号')
      return
    }

    setLoading(true)
    const success = await login(values.ehr_number, values.password)
    setLoading(false)

    if (success) {
      navigate('/dashboard')
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card
        title="固定资产管理系统"
        style={{ width: 520, boxShadow: '0 10px 30px rgba(0,0,0,0.08)', borderRadius: 12 }}
        headStyle={{ fontSize: 24, textAlign: 'center', fontWeight: 600 }}
        bodyStyle={{ padding: '40px 48px' }}
      >
        <Form
          form={form}
          name="login"
          onFinish={handleSubmit}
          autoComplete="off"
          layout="vertical"
          style={{ fontSize: 16 }}
        >
          <Form.Item
            label={<span style={{ fontSize: 16, fontWeight: 500 }}>EHR号</span>}
            name="ehr_number"
            rules={[
              { required: true, message: '请输入EHR号' },
              { len: 7, message: 'EHR号必须为7位数字' },
              { pattern: /^\d+$/, message: 'EHR号必须为数字' }
            ]}
          >
            <Input
              size="large"
              prefix={<UserOutlined />}
              placeholder="请输入7位EHR号"
              maxLength={7}
              onBlur={handleEHRBlur}
            />
          </Form.Item>

          {ehrChecked && userName && (
            <div style={{ marginBottom: 16, padding: 8, background: '#e6f7ff', borderRadius: 4 }}>
              <span>用户名：<strong>{userName}</strong></span>
            </div>
          )}

          <Form.Item
            label={<span style={{ fontSize: 16, fontWeight: 500 }}>密码</span>}
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              size="large"
              prefix={<LockOutlined />}
              placeholder="请输入密码"
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading} size="large" style={{ fontSize: 16, height: 48 }}>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default Login

