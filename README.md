# 固定资产管理系统

一个基于Python FastAPI后端和React + Ant Design前端的固定资产管理系统，支持资产的增删改查、交接、审批、退回等功能。

## 功能特性

### 核心功能
- ✅ **资产管理**：资产的增删改查、批量导入
- ✅ **资产交接**：资产从A员工转到B员工的申请流程
- ✅ **资产退回**：员工离职时资产退回仓库的申请流程
- ✅ **流程审批**：管理员审批交接和退回申请
- ✅ **用户管理**：用户增删改查、批量导入（仅管理员）

### 用户角色
- **管理员**：拥有所有权限，包括审批和用户管理
- **普通用户**：可以查看和管理自己的资产，提交交接和退回申请

### 数据模型

#### 用户信息
- EHR号（7位数字，唯一标识）
- 真实姓名
- 组别（如：第1组、管理组）
- 角色（管理员/普通用户）

#### 固定资产信息
**实物情况：**
- 资产编号（唯一）
- 所属大类（如：办公用品、电子设备配件）
- 实物名称
- 规格型号（可选）
- 状态（在用/库存备用）
- MAC地址（可选）
- IP地址（可选）

**盘点情况：**
- 存放办公地点
- 存放楼层
- 使用人
- 使用人组别

## 技术栈

### 后端
- **FastAPI**：现代、快速的Web框架
- **SQLAlchemy**：ORM数据库操作
- **SQLite**：轻量级数据库（可替换为PostgreSQL/MySQL）
- **JWT**：用户认证
- **Pandas + OpenPyXL**：Excel批量导入

### 前端
- **React 18**：UI框架
- **Ant Design 5**：UI组件库
- **React Router**：路由管理
- **Axios**：HTTP客户端
- **Vite**：构建工具

## 项目结构

```
.
├── backend/                 # 后端代码
│   ├── routers/            # API路由
│   │   ├── auth.py         # 认证相关
│   │   ├── users.py        # 用户管理
│   │   ├── assets.py       # 资产管理
│   │   ├── transfers.py    # 资产交接
│   │   ├── returns.py      # 资产退回
│   │   ├── approvals.py    # 审批管理
│   │   └── categories.py   # 资产大类
│   ├── models.py           # 数据库模型
│   ├── schemas.py          # Pydantic模式
│   ├── auth.py             # 认证工具
│   ├── database.py         # 数据库配置
│   ├── main.py             # 应用入口
│   └── requirements.txt    # Python依赖
│
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── pages/          # 页面组件
│   │   │   ├── Login.jsx           # 登录页
│   │   │   ├── Dashboard.jsx       # 首页
│   │   │   ├── UserManagement.jsx  # 用户管理
│   │   │   ├── AssetManagement.jsx  # 资产管理
│   │   │   ├── TransferManagement.jsx  # 资产交接
│   │   │   ├── ReturnManagement.jsx    # 资产退回
│   │   │   └── ApprovalManagement.jsx  # 审批管理
│   │   ├── components/     # 公共组件
│   │   │   ├── Layout.jsx      # 布局组件
│   │   │   └── PrivateRoute.jsx # 路由守卫
│   │   ├── contexts/       # Context
│   │   │   └── AuthContext.jsx  # 认证上下文
│   │   ├── utils/          # 工具函数
│   │   │   └── api.js       # API客户端
│   │   ├── App.jsx         # 应用入口
│   │   └── main.jsx        # 入口文件
│   ├── package.json        # 前端依赖
│   └── vite.config.js     # Vite配置
│
└── README.md              # 项目说明
```

## 安装和运行

### 后端

1. 进入后端目录：
```bash
cd backend
```

2. 创建虚拟环境（如果还没有）：
```bash
python -m venv venv
```

3. 激活虚拟环境：
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

4. 安装依赖：
```bash
pip install -r requirements.txt
```

5. 运行后端服务：
```bash
uvicorn main:app --reload --port 8000
```

后端API文档：http://localhost:8000/docs

### 前端

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 运行开发服务器：
```bash
npm run dev
```

前端应用：http://localhost:3000

## 使用说明

### 登录功能

1. 在登录页面输入7位EHR号
2. 系统会自动验证EHR号，如果存在则显示用户名
3. 输入密码完成登录

### 用户管理（仅管理员）

- **新增用户**：点击"新增用户"按钮，填写用户信息
- **编辑用户**：点击用户列表中的"编辑"按钮
- **删除用户**：点击"删除"按钮（需确认）
- **批量导入**：点击"批量导入"按钮，上传Excel文件

**Excel导入格式：**
| EHR号 | 姓名 | 组别 | 角色 | 密码 |
|-------|------|------|------|------|
| 1234567 | 张三 | 第1组 | user | 123456 |

### 资产管理

- **新增资产**：点击"新增资产"按钮，填写资产信息
- **编辑资产**：点击资产列表中的"编辑"按钮
- **删除资产**：点击"删除"按钮（需确认）
- **批量导入**：点击"批量导入"按钮，上传Excel文件

**Excel导入格式：**
| 资产编号 | 所属大类 | 实物名称 | 规格型号 | 状态 | MAC地址 | IP地址 | 存放办公地点 | 存放楼层 | 使用人EHR号 | 使用人组别 |
|---------|---------|---------|---------|------|---------|--------|------------|---------|------------|-----------|
| ASSET001 | 电子设备配件 | 主机 | i7-9700 | 在用 | 00:11:22:33:44:55 | 192.168.1.100 | 办公楼A | 3楼 | 1234567 | 第1组 |

### 资产交接

1. 点击"申请交接"按钮
2. 选择要交接的资产
3. 选择转入用户
4. 填写交接原因（可选）
5. 提交申请，等待管理员审批

### 资产退回

1. 点击"申请退回"按钮
2. 选择要退回的资产
3. 填写退回原因（可选）
4. 提交申请，等待管理员审批

### 审批管理（仅管理员）

1. 在"审批管理"页面查看待审批的申请
2. 点击"审批"按钮
3. 选择"批准"或"拒绝"
4. 填写审批意见（可选）
5. 提交审批

**审批结果：**
- **批准交接**：资产的使用人更新为转入用户
- **批准退回**：资产退回仓库，状态变为"库存备用"，清空使用人信息
- **拒绝**：申请被拒绝，资产状态不变

## API接口说明

### 认证接口
- `POST /api/auth/check-ehr` - 检查EHR号是否存在
- `POST /api/auth/login` - 用户登录

### 用户管理接口
- `GET /api/users/` - 获取用户列表（管理员）
- `GET /api/users/me` - 获取当前用户信息
- `GET /api/users/{id}` - 获取指定用户
- `POST /api/users/` - 创建用户（管理员）
- `PUT /api/users/{id}` - 更新用户（管理员）
- `DELETE /api/users/{id}` - 删除用户（管理员）
- `POST /api/users/import` - 批量导入用户（管理员）

### 资产管理接口
- `GET /api/assets/` - 获取资产列表
- `GET /api/assets/{id}` - 获取指定资产
- `POST /api/assets/` - 创建资产
- `PUT /api/assets/{id}` - 更新资产
- `DELETE /api/assets/{id}` - 删除资产
- `POST /api/assets/import` - 批量导入资产

### 资产交接接口
- `GET /api/transfers/` - 获取交接申请列表
- `GET /api/transfers/{id}` - 获取指定交接申请
- `POST /api/transfers/` - 创建交接申请

### 资产退回接口
- `GET /api/returns/` - 获取退回申请列表
- `GET /api/returns/{id}` - 获取指定退回申请
- `POST /api/returns/` - 创建退回申请

### 审批接口
- `POST /api/approvals/approve` - 审批申请（管理员）

### 资产大类接口
- `GET /api/categories/` - 获取资产大类列表
- `POST /api/categories/` - 创建资产大类

## 数据库初始化

系统首次运行时会自动创建数据库表。如果需要初始化管理员账户，可以：

1. 通过API创建：
```bash
curl -X POST "http://localhost:8000/api/users/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ehr_number": "0000001",
    "real_name": "管理员",
    "group": "管理组",
    "role": "admin",
    "password": "admin123"
  }'
```

2. 或通过前端界面创建（需要先有一个管理员账户）

## 注意事项

1. **生产环境配置**：
   - 修改 `backend/auth.py` 中的 `SECRET_KEY`
   - 考虑使用PostgreSQL或MySQL替代SQLite
   - 配置HTTPS
   - 设置适当的CORS策略

2. **Excel导入**：
   - 确保Excel文件格式正确
   - 列名必须与文档中的格式一致
   - 导入时会自动创建不存在的资产大类

3. **权限控制**：
   - 普通用户只能查看和管理自己的资产
   - 只有管理员可以审批申请和管理用户

## 开发说明

### 后端开发
- 使用FastAPI的自动文档功能：http://localhost:8000/docs
- 数据库迁移可以使用Alembic（可选）

### 前端开发
- 使用Vite作为构建工具，支持热重载
- Ant Design组件库提供丰富的UI组件
- 使用Context API管理全局状态（认证信息）

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue或Pull Request。



一个基于Python FastAPI后端和React + Ant Design前端的固定资产管理系统，支持资产的增删改查、交接、审批、退回等功能。

## 功能特性

### 核心功能
- ✅ **资产管理**：资产的增删改查、批量导入
- ✅ **资产交接**：资产从A员工转到B员工的申请流程
- ✅ **资产退回**：员工离职时资产退回仓库的申请流程
- ✅ **流程审批**：管理员审批交接和退回申请
- ✅ **用户管理**：用户增删改查、批量导入（仅管理员）

### 用户角色
- **管理员**：拥有所有权限，包括审批和用户管理
- **普通用户**：可以查看和管理自己的资产，提交交接和退回申请

### 数据模型

#### 用户信息
- EHR号（7位数字，唯一标识）
- 真实姓名
- 组别（如：第1组、管理组）
- 角色（管理员/普通用户）

#### 固定资产信息
**实物情况：**
- 资产编号（唯一）
- 所属大类（如：办公用品、电子设备配件）
- 实物名称
- 规格型号（可选）
- 状态（在用/库存备用）
- MAC地址（可选）
- IP地址（可选）

**盘点情况：**
- 存放办公地点
- 存放楼层
- 使用人
- 使用人组别

## 技术栈

### 后端
- **FastAPI**：现代、快速的Web框架
- **SQLAlchemy**：ORM数据库操作
- **SQLite**：轻量级数据库（可替换为PostgreSQL/MySQL）
- **JWT**：用户认证
- **Pandas + OpenPyXL**：Excel批量导入

### 前端
- **React 18**：UI框架
- **Ant Design 5**：UI组件库
- **React Router**：路由管理
- **Axios**：HTTP客户端
- **Vite**：构建工具

## 项目结构

```
.
├── backend/                 # 后端代码
│   ├── routers/            # API路由
│   │   ├── auth.py         # 认证相关
│   │   ├── users.py        # 用户管理
│   │   ├── assets.py       # 资产管理
│   │   ├── transfers.py    # 资产交接
│   │   ├── returns.py      # 资产退回
│   │   ├── approvals.py    # 审批管理
│   │   └── categories.py   # 资产大类
│   ├── models.py           # 数据库模型
│   ├── schemas.py          # Pydantic模式
│   ├── auth.py             # 认证工具
│   ├── database.py         # 数据库配置
│   ├── main.py             # 应用入口
│   └── requirements.txt    # Python依赖
│
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── pages/          # 页面组件
│   │   │   ├── Login.jsx           # 登录页
│   │   │   ├── Dashboard.jsx       # 首页
│   │   │   ├── UserManagement.jsx  # 用户管理
│   │   │   ├── AssetManagement.jsx  # 资产管理
│   │   │   ├── TransferManagement.jsx  # 资产交接
│   │   │   ├── ReturnManagement.jsx    # 资产退回
│   │   │   └── ApprovalManagement.jsx  # 审批管理
│   │   ├── components/     # 公共组件
│   │   │   ├── Layout.jsx      # 布局组件
│   │   │   └── PrivateRoute.jsx # 路由守卫
│   │   ├── contexts/       # Context
│   │   │   └── AuthContext.jsx  # 认证上下文
│   │   ├── utils/          # 工具函数
│   │   │   └── api.js       # API客户端
│   │   ├── App.jsx         # 应用入口
│   │   └── main.jsx        # 入口文件
│   ├── package.json        # 前端依赖
│   └── vite.config.js     # Vite配置
│
└── README.md              # 项目说明
```

## 安装和运行

### 后端

1. 进入后端目录：
```bash
cd backend
```

2. 创建虚拟环境（如果还没有）：
```bash
python -m venv venv
```

3. 激活虚拟环境：
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

4. 安装依赖：
```bash
pip install -r requirements.txt
```

5. 运行后端服务：
```bash
uvicorn main:app --reload --port 8000
```

后端API文档：http://localhost:8000/docs

### 前端

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 运行开发服务器：
```bash
npm run dev
```

前端应用：http://localhost:3000

## 使用说明

### 登录功能

1. 在登录页面输入7位EHR号
2. 系统会自动验证EHR号，如果存在则显示用户名
3. 输入密码完成登录

### 用户管理（仅管理员）

- **新增用户**：点击"新增用户"按钮，填写用户信息
- **编辑用户**：点击用户列表中的"编辑"按钮
- **删除用户**：点击"删除"按钮（需确认）
- **批量导入**：点击"批量导入"按钮，上传Excel文件

**Excel导入格式：**
| EHR号 | 姓名 | 组别 | 角色 | 密码 |
|-------|------|------|------|------|
| 1234567 | 张三 | 第1组 | user | 123456 |

### 资产管理

- **新增资产**：点击"新增资产"按钮，填写资产信息
- **编辑资产**：点击资产列表中的"编辑"按钮
- **删除资产**：点击"删除"按钮（需确认）
- **批量导入**：点击"批量导入"按钮，上传Excel文件

**Excel导入格式：**
| 资产编号 | 所属大类 | 实物名称 | 规格型号 | 状态 | MAC地址 | IP地址 | 存放办公地点 | 存放楼层 | 使用人EHR号 | 使用人组别 |
|---------|---------|---------|---------|------|---------|--------|------------|---------|------------|-----------|
| ASSET001 | 电子设备配件 | 主机 | i7-9700 | 在用 | 00:11:22:33:44:55 | 192.168.1.100 | 办公楼A | 3楼 | 1234567 | 第1组 |

### 资产交接

1. 点击"申请交接"按钮
2. 选择要交接的资产
3. 选择转入用户
4. 填写交接原因（可选）
5. 提交申请，等待管理员审批

### 资产退回

1. 点击"申请退回"按钮
2. 选择要退回的资产
3. 填写退回原因（可选）
4. 提交申请，等待管理员审批

### 审批管理（仅管理员）

1. 在"审批管理"页面查看待审批的申请
2. 点击"审批"按钮
3. 选择"批准"或"拒绝"
4. 填写审批意见（可选）
5. 提交审批

**审批结果：**
- **批准交接**：资产的使用人更新为转入用户
- **批准退回**：资产退回仓库，状态变为"库存备用"，清空使用人信息
- **拒绝**：申请被拒绝，资产状态不变

## API接口说明

### 认证接口
- `POST /api/auth/check-ehr` - 检查EHR号是否存在
- `POST /api/auth/login` - 用户登录

### 用户管理接口
- `GET /api/users/` - 获取用户列表（管理员）
- `GET /api/users/me` - 获取当前用户信息
- `GET /api/users/{id}` - 获取指定用户
- `POST /api/users/` - 创建用户（管理员）
- `PUT /api/users/{id}` - 更新用户（管理员）
- `DELETE /api/users/{id}` - 删除用户（管理员）
- `POST /api/users/import` - 批量导入用户（管理员）

### 资产管理接口
- `GET /api/assets/` - 获取资产列表
- `GET /api/assets/{id}` - 获取指定资产
- `POST /api/assets/` - 创建资产
- `PUT /api/assets/{id}` - 更新资产
- `DELETE /api/assets/{id}` - 删除资产
- `POST /api/assets/import` - 批量导入资产

### 资产交接接口
- `GET /api/transfers/` - 获取交接申请列表
- `GET /api/transfers/{id}` - 获取指定交接申请
- `POST /api/transfers/` - 创建交接申请

### 资产退回接口
- `GET /api/returns/` - 获取退回申请列表
- `GET /api/returns/{id}` - 获取指定退回申请
- `POST /api/returns/` - 创建退回申请

### 审批接口
- `POST /api/approvals/approve` - 审批申请（管理员）

### 资产大类接口
- `GET /api/categories/` - 获取资产大类列表
- `POST /api/categories/` - 创建资产大类

## 数据库初始化

系统首次运行时会自动创建数据库表。如果需要初始化管理员账户，可以：

1. 通过API创建：
```bash
curl -X POST "http://localhost:8000/api/users/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ehr_number": "0000001",
    "real_name": "管理员",
    "group": "管理组",
    "role": "admin",
    "password": "admin123"
  }'
```

2. 或通过前端界面创建（需要先有一个管理员账户）

## 注意事项

1. **生产环境配置**：
   - 修改 `backend/auth.py` 中的 `SECRET_KEY`
   - 考虑使用PostgreSQL或MySQL替代SQLite
   - 配置HTTPS
   - 设置适当的CORS策略

2. **Excel导入**：
   - 确保Excel文件格式正确
   - 列名必须与文档中的格式一致
   - 导入时会自动创建不存在的资产大类

3. **权限控制**：
   - 普通用户只能查看和管理自己的资产
   - 只有管理员可以审批申请和管理用户

## 开发说明

### 后端开发
- 使用FastAPI的自动文档功能：http://localhost:8000/docs
- 数据库迁移可以使用Alembic（可选）

### 前端开发
- 使用Vite作为构建工具，支持热重载
- Ant Design组件库提供丰富的UI组件
- 使用Context API管理全局状态（认证信息）

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue或Pull Request。


