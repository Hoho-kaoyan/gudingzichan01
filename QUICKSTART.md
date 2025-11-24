# 快速启动指南

## 第一步：初始化后端

1. 进入后端目录：
```bash
cd backend
```

2. 激活虚拟环境（如果还没有）：
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. 安装依赖（如果还没有）：
```bash
pip install -r requirements.txt
```

4. 初始化数据库（创建管理员账户和资产大类）：
```bash
python init_db.py
```

5. 启动后端服务：
```bash
uvicorn main:app --reload --port 8000
```

后端服务将在 http://localhost:8000 启动
API文档：http://localhost:8000/docs

## 第二步：启动前端

1. 打开新的终端窗口，进入前端目录：
```bash
cd frontend
```

2. 安装依赖（首次运行）：
```bash
npm install
```

3. 启动前端开发服务器：
```bash
npm run dev
```

前端应用将在 http://localhost:3000 启动

## 第三步：登录系统

使用默认管理员账户登录：
- **EHR号**：0000001
- **密码**：admin123

登录后，您可以：
1. 在"用户管理"中创建更多用户
2. 在"资产管理"中添加资产
3. 测试资产交接和退回功能
4. 在"审批管理"中审批申请

## 常见问题

### 后端启动失败
- 确保已安装所有依赖：`pip install -r requirements.txt`
- 检查端口8000是否被占用
- 确保虚拟环境已激活

### 前端启动失败
- 确保已安装Node.js和npm
- 删除node_modules文件夹，重新运行`npm install`
- 检查端口3000是否被占用

### 无法登录
- 确保已运行`python init_db.py`初始化数据库
- 检查后端服务是否正常运行
- 查看浏览器控制台和网络请求

### Excel导入失败
- 确保Excel文件格式正确
- 检查列名是否与文档中的格式一致
- 查看后端日志了解具体错误信息

## 下一步

- 阅读完整的README.md了解详细功能
- 查看API文档：http://localhost:8000/docs
- 根据需要修改配置和扩展功能



## 第一步：初始化后端

1. 进入后端目录：
```bash
cd backend
```

2. 激活虚拟环境（如果还没有）：
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. 安装依赖（如果还没有）：
```bash
pip install -r requirements.txt
```

4. 初始化数据库（创建管理员账户和资产大类）：
```bash
python init_db.py
```

5. 启动后端服务：
```bash
uvicorn main:app --reload --port 8000
```

后端服务将在 http://localhost:8000 启动
API文档：http://localhost:8000/docs

## 第二步：启动前端

1. 打开新的终端窗口，进入前端目录：
```bash
cd frontend
```

2. 安装依赖（首次运行）：
```bash
npm install
```

3. 启动前端开发服务器：
```bash
npm run dev
```

前端应用将在 http://localhost:3000 启动

## 第三步：登录系统

使用默认管理员账户登录：
- **EHR号**：0000001
- **密码**：admin123

登录后，您可以：
1. 在"用户管理"中创建更多用户
2. 在"资产管理"中添加资产
3. 测试资产交接和退回功能
4. 在"审批管理"中审批申请

## 常见问题

### 后端启动失败
- 确保已安装所有依赖：`pip install -r requirements.txt`
- 检查端口8000是否被占用
- 确保虚拟环境已激活

### 前端启动失败
- 确保已安装Node.js和npm
- 删除node_modules文件夹，重新运行`npm install`
- 检查端口3000是否被占用

### 无法登录
- 确保已运行`python init_db.py`初始化数据库
- 检查后端服务是否正常运行
- 查看浏览器控制台和网络请求

### Excel导入失败
- 确保Excel文件格式正确
- 检查列名是否与文档中的格式一致
- 查看后端日志了解具体错误信息

## 下一步

- 阅读完整的README.md了解详细功能
- 查看API文档：http://localhost:8000/docs
- 根据需要修改配置和扩展功能




