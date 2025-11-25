import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import './index.css'


ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          fontSize: 16,
          colorPrimary: '#c41d3f', // 深红色主色调
          colorSuccess: '#52c41a',
          colorWarning: '#faad14',
          colorError: '#c41d3f', // 错误色也用深红色
          colorInfo: '#1890ff',
          colorBgBase: '#ffffff', // 白色背景
          colorBgContainer: '#ffffff',
          borderRadius: 6,
        },
        components: {
          Button: {
            primaryColor: '#ffffff', // 按钮文字颜色
          },
          Menu: {
            itemSelectedBg: '#fff1f0', // 菜单选中背景（浅红色）
            itemSelectedColor: '#c41d3f', // 菜单选中文字颜色
            itemHoverBg: '#fff1f0', // 菜单悬停背景
          },
          Layout: {
            headerBg: '#ffffff', // 头部背景白色
            siderBg: '#c41d3f', // 侧边栏背景深红色
            triggerBg: '#c41d3f', // 折叠触发器背景
            triggerColor: '#ffffff', // 折叠触发器图标颜色
          },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>
)
