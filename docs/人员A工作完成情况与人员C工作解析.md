# 人员A工作完成情况与人员C工作详细解析

## 一、人员A工作完成情况分析

根据文档《文档一致性与联动安全检查实现方案》第6.1节，人员A的职责范围是：
- **数据库表结构**
- **Model层**
- **联动任务类型配置解析**
- **配置相关API**

### ✅ 已完成的工作

#### 1. 数据库表结构 ✅

**已创建的新表：**
- ✅ `safety_check_auto_config` - 系统自动分配任务类型配置（全局单行）
  - 字段：id, default_check_type_id, created_at, updated_at
  - 位置：`backend/models.py` 第332-342行

- ✅ `safety_check_asset_type_mapping` - 实物名称→检查类型映射
  - 字段：id, asset_type, check_type_id, created_at
  - 位置：`backend/models.py` 第345-356行
  - **注意**：文档中说的是按`category_id`（资产大类）映射，但实际实现是按`asset_type`（实物名称）映射

- ✅ `pending_reallocations` - 待生效调拨
  - 字段：id, asset_id, new_user_id, task_id, created_at
  - 位置：`backend/models.py` 第358-371行

**已有表的字段调整：**
- ✅ `users`表增加`status`字段
  - 字段：status (VARCHAR(20), default="在岗")
  - 位置：`backend/models.py` 第44行

- ✅ `users`表`role`字段增加`LEADER`枚举值
  - 枚举：UserRole.LEADER = "leader"
  - 位置：`backend/models.py` 第13-17行

- ✅ `safety_check_tasks`表增加`source`字段
  - 字段：source (VARCHAR(20), nullable=True)
  - 位置：`backend/models.py` 第247行

#### 2. Model层 ✅

所有新增表都有对应的SQLAlchemy Model类：
- ✅ `SafetyCheckAutoConfig` - 配置Model
- ✅ `SafetyCheckAssetTypeMapping` - 映射Model
- ✅ `PendingReallocation` - 待生效调拨Model
- ✅ `User` - 已包含status和role字段
- ✅ `SafetyCheckTask` - 已包含source字段

#### 3. 配置解析逻辑 ✅

**实现位置：** `backend/safety_check_linkage.py`

**函数：** `get_check_type_for_asset_name(db: Session, asset_name: str) -> Optional[int]`

**逻辑流程：**
1. 先查「实物名称→检查类型」映射表 (`SafetyCheckAssetTypeMapping`)
2. 若无映射，则查全局默认检查类型 (`SafetyCheckAutoConfig.default_check_type_id`)
3. 校验检查类型存在且启用 (`is_active = True`)
4. 无配置或无效时返回None并打日志

**注意差异：**
- 文档方案说的是按`category_id`（资产大类）解析
- 实际实现是按`asset_name`（实物名称）解析
- 这是一个实现差异，需要确认是否符合需求

#### 4. 配置相关API ✅

**实现位置：** `backend/routers/safety_check_auto_config.py`

**已实现的接口：**

**全局默认检查类型：**
- ✅ `GET /api/safety-check-auto-config` - 获取全局配置
- ✅ `PUT /api/safety-check-auto-config` - 创建或更新全局配置

**实物名称→检查类型映射：**
- ✅ `GET /api/safety-check-auto-config/asset-type-mappings` - 获取映射列表
- ✅ `POST /api/safety-check-auto-config/asset-type-mappings` - 新增映射
- ✅ `PUT /api/safety-check-auto-config/asset-type-mappings/{mapping_id}` - 更新映射
- ✅ `DELETE /api/safety-check-auto-config/asset-type-mappings/{mapping_id}` - 删除映射

**路由注册：** ✅ 已在`backend/main.py`第42行注册

### ⚠️ 需要注意的问题

1. **映射方式差异**
   - 文档方案：按`category_id`（资产大类）映射
   - 实际实现：按`asset_name`（实物名称）映射
   - **建议**：需要与产品确认哪种方式更符合业务需求

2. **Schema定义**
   - 需要检查`backend/schemas.py`中是否已定义对应的Schema类
   - 需要确认UserUpdate Schema是否包含status字段

---

## 二、人员C工作详细解析

根据文档《文档一致性与联动安全检查实现方案》第6.1节和第6.2节，人员C的职责范围是：
- **联动任务类型配置页**
- **用户状态与标记离职**
- **组长角色相关前端**

### 📋 工作清单（按文档第2阶段）

#### 任务7：管理员「联动任务类型配置」页

**目标：** 创建前端配置页面，让管理员可以配置默认检查类型和实物名称→检查类型映射

**需要实现的功能：**

1. **创建新页面组件**
   - 文件路径：`frontend/src/pages/SafetyCheckAutoConfig.jsx`
   - 路由：需要在`App.jsx`中添加路由配置

2. **全局默认检查类型配置**
   - 显示当前默认检查类型（如果有）
   - 下拉选择框选择检查类型
   - 保存按钮更新配置
   - 调用接口：`GET /api/safety-check-auto-config` 和 `PUT /api/safety-check-auto-config`

3. **实物名称→检查类型映射管理**
   - 表格展示所有映射关系
   - 支持新增映射（实物名称 + 检查类型）
   - 支持编辑映射（修改检查类型）
   - 支持删除映射
   - 调用接口：
     - `GET /api/safety-check-auto-config/asset-type-mappings` - 列表
     - `POST /api/safety-check-auto-config/asset-type-mappings` - 新增
     - `PUT /api/safety-check-auto-config/asset-type-mappings/{mapping_id}` - 更新
     - `DELETE /api/safety-check-auto-config/asset-type-mappings/{mapping_id}` - 删除

4. **获取检查类型列表**
   - 调用接口：`GET /api/safety-check-types/` 获取所有启用的检查类型
   - 用于下拉选择框

**UI设计建议：**
- 使用Ant Design的Card组件分区域展示
- 全局配置区域：Form + Select + Button
- 映射管理区域：Table + Modal（新增/编辑表单）
- 参考`SafetyCheckTaskManagement.jsx`的样式风格

**页面入口：**
- 可以在「安全检查任务管理」页面添加「联动配置」按钮
- 或者添加到侧边栏菜单（仅管理员可见）

---

#### 任务8：用户管理 - 用户状态与标记离职

**目标：** 在用户管理页面增加状态字段，支持标记离职并触发批量创建检查任务

**需要修改的文件：** `frontend/src/pages/UserManagement.jsx`

**需要实现的功能：**

1. **用户列表增加状态列**
   - 在表格columns中添加状态列
   - 显示用户状态（在岗/离职/长期出差/借调/产假等）
   - 状态值来自`user.status`字段

2. **用户表单增加状态字段**
   - 在新增/编辑用户的Modal中增加状态选择框
   - 使用Select组件，选项：在岗、离职、长期出差、借调、产假等
   - 默认值：在岗

3. **标记离职功能**
   - 在用户列表的操作列添加「标记离职」按钮（仅对状态不是「离职」的用户显示）
   - 点击后弹出确认Modal，提示：
     ```
     是否完成数据安全检查进行资产交接？
     
     确认后将：
     1. 将该用户状态更新为「离职」
     2. 为该用户名下所有资产自动创建安全检查任务
     3. 任务将分配给该用户
     ```
   - 确认后调用后端接口（需要人员B实现）：
     - `PUT /api/users/{user_id}/mark-resignation` 或类似接口
   - 显示成功/失败提示

4. **状态筛选功能**
   - 在查询表单中增加「状态」筛选下拉框
   - 支持按状态筛选用户列表

**后端接口依赖：**
- 需要人员B实现标记离职接口，接口应：
  1. 更新用户status为「离职」
  2. 查询该用户名下所有资产
  3. 为每条资产调用创建系统任务的服务（4.2.2）
  4. 返回创建的任务数量

**UI设计建议：**
- 状态列可以使用Tag组件显示，不同状态不同颜色
- 「标记离职」按钮使用警告色（warning/danger）
- 确认Modal使用Modal.confirm或自定义Modal

---

#### 任务9：组长角色相关前端

**目标：** 在用户管理和资产管理中支持组长角色，组长只能管理本组资产

**需要修改的文件：**
1. `frontend/src/pages/UserManagement.jsx` - 用户管理
2. `frontend/src/pages/AssetManagement.jsx` - 资产管理
3. `frontend/src/contexts/AuthContext.jsx` - 可能需要添加isLeader判断

**需要实现的功能：**

1. **用户管理 - 角色选项增加组长**
   - 在新增/编辑用户的角色选择框中增加「组长」选项
   - 当前代码位置：`UserManagement.jsx` 第262-265行
   - 修改为：
     ```jsx
     <Select>
       <Select.Option value="user">普通用户</Select.Option>
       <Select.Option value="admin">管理员</Select.Option>
       <Select.Option value="leader">组长</Select.Option>
     </Select>
     ```
   - 在用户列表的角色列显示中，增加组长显示：
     ```jsx
     render: (role) => {
       const roleMap = {
         'admin': '管理员',
         'user': '普通用户',
         'leader': '组长'
       }
       return roleMap[role] || role
     }
     ```
   - 在角色筛选下拉框中增加组长选项

2. **资产管理 - 组长权限控制**
   - **使用人修改权限：**
     - 管理员：可以修改任意资产的使用人
     - 组长：只能修改本组资产的使用人（`asset.user_group == current_user.group`）
     - 普通用户：不能修改使用人
   
   - **实现位置：** `AssetManagement.jsx` 的编辑资产功能
   - **需要检查：**
     - 编辑资产时，如果当前用户是组长，使用人选择框应该：
       1. 只显示本组用户（`user.group == currentUser.group`）
       2. 或者后端接口已经做了权限校验，前端只需要禁用/隐藏即可
   
   - **资产列表权限：**
     - 管理员：查看所有资产
     - 组长：查看本组资产（`asset.user_group == currentUser.group`）
     - 普通用户：查看自己名下的资产
   - **注意：** 这个权限控制可能在后端接口中已经实现，前端需要确认

3. **调拨相关按钮与权限**
   - 组长可以对本组资产进行调拨（修改使用人）
   - 调拨逻辑与管理员一致，但范围限定在本组
   - **需要确认：** 是否有独立的调拨页面，还是通过资产管理页面的编辑功能实现

**权限判断辅助函数：**
- 在`AuthContext.jsx`中可能需要添加：
  ```jsx
  const isLeader = user?.role === 'leader'
  const isAdminOrLeader = isAdmin || isLeader
  ```

**后端接口依赖：**
- 需要人员B在资产管理接口中实现组长权限校验：
  - 组长只能修改本组资产的使用人
  - 组长只能查看本组资产

---

### 📋 工作清单（按文档第3阶段）

#### 任务12相关：组长权限前端展示

虽然任务12是人员B的工作（后端权限校验），但前端需要配合：
- 如果组长尝试修改非本组资产的使用人，后端会返回403错误
- 前端需要捕获错误并提示：「您只能修改本组资产的使用人」

---

## 三、实现顺序建议

### 第1步：联动任务类型配置页（任务7）
**优先级：高**
- 这是基础配置功能，其他功能依赖此配置
- 完成后可以测试配置接口是否正常工作

### 第2步：用户状态与标记离职（任务8）
**优先级：高**
- 依赖人员B实现标记离职接口
- 可以先实现状态字段的显示和编辑
- 标记离职功能等后端接口就绪后再实现

### 第3步：组长角色（任务9）
**优先级：中**
- 依赖人员B实现组长权限的后端校验
- 可以先实现前端的角色选项和显示
- 权限控制等后端接口就绪后再完善

---

## 四、技术要点

### 1. API调用
- 使用`api.js`中的axios实例
- 错误处理使用`message.error()`显示提示
- 成功操作使用`message.success()`显示提示

### 2. 状态管理
- 使用React Hooks（useState, useEffect）
- 表单使用Ant Design的Form组件
- 表格使用Ant Design的Table组件

### 3. 权限控制
- 使用`useAuth()`获取当前用户信息
- 使用`isAdmin`判断管理员权限
- 需要添加`isLeader`判断组长权限

### 4. 路由配置
- 在`App.jsx`中添加新页面路由
- 在`Layout.jsx`的侧边栏菜单中添加入口（如果需要）

---

## 五、注意事项

1. **与人员B的协作**
   - 标记离职接口需要人员B实现
   - 组长权限校验需要人员B在后端实现
   - 建议先实现前端UI，等后端接口就绪后再联调

2. **与人员A的确认**
   - 确认映射方式：是按`category_id`还是`asset_name`？
   - 确认Schema是否完整

3. **测试要点**
   - 配置页面：增删改查功能是否正常
   - 用户状态：状态字段是否正确显示和保存
   - 标记离职：是否能正确触发批量创建任务
   - 组长权限：组长是否能正确看到和操作本组资产

---

## 六、参考文件

- **后端配置接口：** `backend/routers/safety_check_auto_config.py`
- **用户管理页面：** `frontend/src/pages/UserManagement.jsx`
- **资产管理页面：** `frontend/src/pages/AssetManagement.jsx`
- **安全检查任务管理：** `frontend/src/pages/SafetyCheckTaskManagement.jsx`（参考样式）
- **认证上下文：** `frontend/src/contexts/AuthContext.jsx`

---

## 七、总结

**人员A工作完成情况：** ✅ 基本完成
- 数据库表结构：✅ 完成
- Model层：✅ 完成
- 配置解析逻辑：✅ 完成（注意实现方式与文档有差异）
- 配置API：✅ 完成

**人员C需要完成的工作：**
1. ✅ 创建联动任务类型配置页面
2. ✅ 用户管理增加状态字段和标记离职功能
3. ✅ 组长角色相关前端功能

**建议开始顺序：**
1. 先做配置页面（任务7）
2. 再做用户状态（任务8）
3. 最后做组长角色（任务9）

**关键依赖：**
- 标记离职接口需要人员B实现
- 组长权限校验需要人员B实现
- 建议先做前端UI，等后端接口就绪后联调

---

## 八、人员C工作完成情况详细分析

### ✅ 已完成的工作

#### 1. 任务8：用户状态与标记离职 ✅ **已完成**

**实现位置：** `frontend/src/pages/UserManagement.jsx`

**已完成的功能：**

1. **用户列表状态列** ✅
   - 位置：第193-208行
   - 使用Tag组件显示状态，不同状态不同颜色
   - 支持的状态：在岗（success）、离职（error）、长期出差（processing）、借调（warning）、产假（purple）

2. **用户表单状态字段** ✅
   - 位置：第357-370行
   - 在新增/编辑用户的Modal中增加了状态选择框
   - 包含所有状态选项：在岗、离职、长期出差、借调、产假
   - 默认值：在岗

3. **状态筛选功能** ✅
   - 位置：第284-292行
   - 在查询表单中增加了「状态」筛选下拉框
   - 支持按状态筛选用户列表

4. **标记离职功能** ✅
   - 位置：第134-168行（处理函数）、第220-229行（按钮）、第507-548行（确认Modal）
   - 在用户列表的操作列添加了「标记离职」按钮
   - 仅对状态不是「离职」的用户显示
   - 点击后弹出确认Modal，显示：
     - 用户信息
     - 名下资产数量
     - 确认后的操作说明
   - 调用后端接口：`PUT /api/users/{user_id}/mark-resignation`
   - 显示成功/失败提示

**注意：** 
- ⚠️ 后端接口`PUT /api/users/{user_id}/mark-resignation`尚未实现（人员B任务13未完成）
- 前端代码已准备好，等待人员B实现后端接口后即可联调
- **联动状态：** 前端已完成，等待后端接口

#### 2. 任务7：联动任务类型配置页 ⚠️ **部分完成**

**实现位置：** `frontend/src/pages/SafetyCheckTaskManagement.jsx`

**已完成的功能：**

1. **联动配置功能集成** ✅
   - 位置：第297-1197行
   - 在「安全检查任务管理」页面中添加了「联动任务配置」按钮（第534行）
   - 点击后打开配置Modal，包含：
     - 全局默认检查类型配置（第1036-1073行）
     - 实物名称→检查类型映射管理（第1075-1145行）

2. **全局默认检查类型配置** ✅
   - 显示当前默认检查类型
   - 下拉选择框选择检查类型
   - 保存按钮更新配置
   - 调用接口：`GET /api/safety-check-auto-config` 和 `PUT /api/safety-check-auto-config`

3. **实物名称→检查类型映射管理** ✅
   - 表格展示所有映射关系
   - 支持新增映射（实物名称 + 检查类型）
   - 支持编辑映射（修改检查类型）
   - 支持删除映射
   - 调用所有必要的接口

**未完成的部分：**

1. **独立页面组件** ❌
   - 文档要求创建独立的页面组件：`frontend/src/pages/SafetyCheckAutoConfig.jsx`
   - 当前实现是集成在`SafetyCheckTaskManagement.jsx`中的Modal
   - **建议：** 可以保持当前实现方式（Modal），或者创建独立页面（根据产品需求决定）

2. **路由配置** ❌
   - 如果创建独立页面，需要在`App.jsx`中添加路由配置
   - 当前通过Modal方式访问，无需路由

3. **菜单入口** ❌
   - 如果创建独立页面，可以在侧边栏菜单中添加入口（仅管理员可见）
   - 当前通过「安全检查任务管理」页面的按钮访问

**评估：** 
- 功能已完整实现，只是实现方式与文档建议不同（Modal vs 独立页面）
- 如果产品接受Modal方式，则任务7可视为完成
- 如果需要独立页面，需要将Modal内容提取为独立页面组件

---

### ❌ 待完成的工作

#### 1. 任务9：组长角色相关前端 ❌ **未完成**

**需要修改的文件：**

1. **`frontend/src/pages/UserManagement.jsx`** ❌
   - **角色列显示：** 第190行，当前只显示admin和普通用户，需要增加组长显示
   - **角色筛选：** 第278-282行，当前只有admin和user选项，需要增加leader选项
   - **角色选择框：** 第352-355行，当前只有user和admin选项，需要增加leader选项

2. **`frontend/src/pages/AssetManagement.jsx`** ❌
   - **权限判断：** 第11行，当前只使用`isAdmin`，需要增加`isLeader`判断
   - **使用人选择框：** 第683行，当前`disabled={!isAdmin}`，需要支持组长权限
   - **资产列表权限：** 需要确认组长是否能正确查看本组资产（可能后端已实现）

3. **`frontend/src/contexts/AuthContext.jsx`** ❌
   - **isLeader判断：** 第88行，当前只有`isAdmin`，需要增加`isLeader`和`isAdminOrLeader`

**具体需要实现：**

1. **AuthContext.jsx**
   ```jsx
   // 需要添加：
   isLeader: user?.role === 'leader',
   isAdminOrLeader: user?.role === 'admin' || user?.role === 'leader'
   ```

2. **UserManagement.jsx**
   - 角色列显示增加组长（第190行）
   - 角色筛选增加组长选项（第278-282行）
   - 角色选择框增加组长选项（第352-355行）

3. **AssetManagement.jsx**
   - 使用`isLeader`和`isAdminOrLeader`进行权限判断
   - 组长编辑资产时，使用人选择框只显示本组用户
   - 组长只能编辑本组资产（可能需要后端配合）

**后端接口依赖：**
- ⚠️ 人员B任务12未完成：需要在资产管理接口中实现组长权限校验
- 组长只能修改本组资产的使用人
- 组长只能查看本组资产
- **联动状态：** 双方都未完成，需要协调实现

---

### 📊 完成情况统计

| 任务 | 状态 | 完成度 | 备注 |
|------|------|--------|------|
| 任务7：联动任务类型配置页 | ⚠️ 部分完成 | 90% | 功能完整，但实现方式为Modal而非独立页面 |
| 任务8：用户状态与标记离职 | ✅ 已完成 | 100% | 前端完成，等待人员B实现后端接口（任务13） |
| 任务9：组长角色相关前端 | ❌ 未完成 | 0% | 需要修改3个文件，等待人员B实现权限校验（任务12） |

**总体完成度：** 约63%（2/3任务完成，其中1个部分完成）

**与人员B的联动状态：**
- 任务8：前端✅ → 等待后端❌（人员B任务13）
- 任务9：前端❌ ← 依赖 → 后端❌（人员B任务12）

---

### 🎯 下一步工作建议

#### 优先级1：完成任务9（组长角色相关前端）

**步骤：**

1. **修改AuthContext.jsx**
   - 添加`isLeader`和`isAdminOrLeader`判断
   - 导出供其他组件使用

2. **修改UserManagement.jsx**
   - 角色列显示增加组长
   - 角色筛选增加组长选项
   - 角色选择框增加组长选项

3. **修改AssetManagement.jsx**
   - 使用`isLeader`和`isAdminOrLeader`进行权限判断
   - 组长编辑资产时，使用人选择框过滤为本组用户
   - 添加组长权限的错误提示

**预计工作量：** 2-3小时

#### 优先级2：确认任务7的实现方式

**选项A：保持Modal方式（推荐）**
- 优点：无需修改，功能完整
- 缺点：不符合文档建议的独立页面

**选项B：改为独立页面**
- 需要创建`SafetyCheckAutoConfig.jsx`
- 需要添加路由配置
- 需要添加菜单入口
- 需要将Modal内容提取为页面组件

**建议：** 与产品确认是否需要独立页面，如果不需要，则任务7可视为完成。

---

### ⚠️ 注意事项

1. **后端接口依赖**
   - 标记离职接口（`PUT /api/users/{user_id}/mark-resignation`）需要人员B实现
   - 组长权限校验需要人员B在后端实现
   - 前端代码已准备好，等待后端接口就绪后联调

2. **测试要点**
   - 用户状态：状态字段是否正确显示和保存 ✅
   - 标记离职：是否能正确触发批量创建任务（等待后端接口）
   - 组长权限：组长是否能正确看到和操作本组资产（待实现）
   - 联动配置：增删改查功能是否正常 ✅

3. **代码质量**
   - 已完成的功能代码质量良好
   - 标记离职功能有完善的错误处理和用户提示
   - 联动配置功能UI设计合理，用户体验良好

---

## 九、人员B工作完成情况详细分析

根据文档《文档一致性与联动安全检查实现方案》第6.1节和第6.2节，人员B的职责范围是：
- **共用「创建系统任务」服务（4.2.2）**
- **入库/交接/调拨/离职四大场景的后端逻辑**
- **4.2.2～4.2.6 全部联动接口与校验逻辑**

### ✅ 已完成的工作

#### 1. 任务4：实现共用「创建系统任务」服务（4.2.2）✅ **已完成**

**实现位置：** `backend/safety_check_linkage.py`

**函数：** `create_system_allocated_task(db: Session, asset_id: int, assigned_user_id: int, source: str, title_prefix: str = "")`

**功能：**
- ✅ 获取资产信息并验证存在性
- ✅ 调用`get_check_type_for_asset`解析检查类型（调用人员A的4.2.1）
- ✅ 创建安全检查任务（`SafetyCheckTask`），设置source字段
- ✅ 创建任务资产关联（`TaskAsset`），分配给指定用户
- ✅ 支持多种source：inbound、transfer、reallocation、resignation
- ✅ 生成任务编号和标题
- ✅ 完整的日志记录

**代码位置：** 第53-119行

---

#### 2. 任务5：场景一 - 入库联动 ✅ **已完成**

**实现位置：** `backend/routers/assets.py`

**功能：**
- ✅ 单个资产创建成功后，如果使用人非空，调用`create_system_allocated_task`创建任务（source=inbound）
- ✅ 批量导入成功后，同样为有使用人的资产创建任务

**代码位置：**
- 单个创建：第234-243行
- 批量导入：第633行附近（需要确认）

**实现逻辑：**
```python
if db_asset.user_id:
    try:
        create_system_allocated_task(
            db=db,
            asset_id=db_asset.id,
            assigned_user_id=db_asset.user_id,
            source="inbound"
        )
    except Exception as e:
        logger.error(f"创建资产时触发系统安检任务下发失败: {e}", exc_info=True)
```

---

#### 3. 任务6：场景二情况一 - 交接联动 ✅ **已完成**

**实现位置：** `backend/routers/transfers.py`

**功能：**
- ✅ 创建交接申请前，校验该资产对转出人是否有未完成任务，有则返回400错误
- ✅ 校验通过后，调用`create_system_allocated_task`创建任务（source=transfer）
- ✅ 任务分配给转出人（from_user_id）

**代码位置：**
- 校验函数：第19-35行 `check_unfinished_tasks_for_asset_user`
- 创建申请：第127-218行 `create_transfer_request`
- 创建任务：第187-197行

**实现逻辑：**
```python
# 校验未完成任务
check_unfinished_tasks_for_asset_user(db, asset.id, from_user_id)

# 创建交接申请后，创建任务
create_system_allocated_task(
    db=db,
    asset_id=asset.id,
    assigned_user_id=from_user_id,
    source="transfer"
)
```

**注意：** 
- ⚠️ 转入人确认和管理员审批前的校验逻辑需要确认是否已实现

---

### ❌ 待完成的工作

#### 1. 任务11：场景二情况二 - 调拨联动（reallocation）❌ **未完成**

**需要实现的位置：** `backend/routers/assets.py` 的 `update_asset` 函数

**当前实现：**
- ✅ 管理员修改使用人时，直接更新资产（第386-391行）
- ✅ 更新未完成的安全检查任务到新接收人（第395-404行）
- ❌ **缺少：** 调拨联动逻辑（创建任务 + 写入pending_reallocations）

**需要实现的功能：**

1. **修改使用人时的调拨逻辑**
   - 当管理员/组长修改资产使用人时，不应该直接更新`asset.user_id`
   - 应该：
     - 如果有原所有人A → 新所有人B：调用`create_system_allocated_task`创建任务（assigned_user_id = A，source=reallocation），插入`pending_reallocations`
     - 如果无使用人 → 新所有人B：调用`create_system_allocated_task`创建任务（assigned_user_id = B，source=reallocation），插入`pending_reallocations`
   - 不直接更新`asset.user_id`，等待任务完成后处理

2. **提交检查结果时处理pending**
   - 在`backend/routers/safety_check_results.py`的`submit_check_result`函数中
   - 当任务完成时，检查是否存在`pending_reallocations`记录
   - 如果存在，更新对应资产的`user_id`和`user_group`，并删除pending记录

**当前代码问题：**
- `update_asset`函数第386-404行直接更新了资产使用人，不符合调拨联动的要求
- `submit_check_result`函数第245-256行只检查任务是否完成，没有处理pending_reallocations

**需要修改：**
- `backend/routers/assets.py` 第386-404行：改为调拨联动逻辑
- `backend/routers/safety_check_results.py` 第245-256行：添加pending处理逻辑

---

#### 2. 任务12：组长权限校验 ❌ **未完成**

**需要实现的位置：** `backend/routers/assets.py` 的 `update_asset` 函数

**当前实现：**
- ✅ 管理员可以直接更新资产（第361行）
- ✅ 普通用户只能编辑自己名下的资产（第265-266行）
- ❌ **缺少：** 组长权限校验

**需要实现的功能：**

1. **组长修改使用人权限**
   - 组长只能修改本组资产的使用人（`asset.user_group == current_user.group`）
   - 如果组长尝试修改非本组资产的使用人，返回403错误

2. **组长查看资产权限**
   - 在`get_assets`函数中，需要添加组长权限逻辑
   - 组长只能查看本组资产（`asset.user_group == current_user.group`）

**当前代码问题：**
- `update_asset`函数第361行只判断了`current_user.role != "admin"`，没有考虑组长角色
- `get_assets`函数第27-78行没有组长权限过滤逻辑

**需要修改：**
- `backend/routers/assets.py` 第361行：添加组长权限判断
- `backend/routers/assets.py` 第27-78行：添加组长资产列表过滤

---

#### 3. 任务13：场景三 - 标记离职接口 ❌ **未完成**

**需要实现的位置：** `backend/routers/users.py`

**当前实现：**
- ❌ **完全未实现**：在`users.py`中没有找到标记离职接口

**需要实现的功能：**

1. **创建接口：** `PUT /api/users/{user_id}/mark-resignation`

2. **接口逻辑：**
   - 更新用户status为「离职」
   - 查询该用户名下所有资产
   - 为每条资产调用`create_system_allocated_task`（source=resignation）
   - 任务分配给该用户（assigned_user_id = user_id）
   - 返回创建的任务数量

3. **权限控制：**
   - 仅管理员可以调用此接口

**需要创建：**
- 在`backend/routers/users.py`中添加新接口函数

---

### 📊 人员B工作完成情况统计

| 任务 | 状态 | 完成度 | 备注 |
|------|------|--------|------|
| 任务4：创建系统任务服务 | ✅ 已完成 | 100% | 功能完整，代码质量良好 |
| 任务5：入库联动 | ✅ 已完成 | 100% | 单个创建和批量导入都已实现 |
| 任务6：交接联动 | ✅ 已完成 | 90% | 创建申请时已实现，确认/审批前校验需确认 |
| 任务11：调拨联动 | ❌ 未完成 | 0% | 需要实现调拨逻辑和pending处理 |
| 任务12：组长权限校验 | ❌ 未完成 | 0% | 需要添加组长权限判断 |
| 任务13：标记离职接口 | ❌ 未完成 | 0% | 需要创建新接口 |

**总体完成度：** 约50%（3/6任务完成，其中1个部分完成）

---

## 十、人员C与人员B工作联动分析

### 🔗 已完成的联动

#### 1. 任务8：用户状态与标记离职

**人员C前端：** ✅ 已完成
- 用户列表状态列显示
- 用户表单状态字段
- 状态筛选功能
- 标记离职按钮和确认Modal
- 调用接口：`PUT /api/users/{user_id}/mark-resignation`

**人员B后端：** ❌ 未完成
- 标记离职接口尚未实现

**联动状态：** ⚠️ **前端已就绪，等待后端接口**

**下一步：**
- 人员B需要实现标记离职接口
- 接口路径：`PUT /api/users/{user_id}/mark-resignation`
- 接口应返回：`{"message": "标记离职成功", "task_count": 5}` 或类似格式

---

#### 2. 任务9：组长角色相关前端

**人员C前端：** ❌ 未完成
- 需要添加组长角色选项和显示
- 需要实现组长权限控制

**人员B后端：** ❌ 未完成
- 组长权限校验尚未实现

**联动状态：** ⚠️ **双方都未完成，需要协调实现**

**实现顺序建议：**

1. **第一步：人员B实现组长权限校验**
   - 在资产管理接口中添加组长权限判断
   - 组长只能修改本组资产的使用人
   - 组长只能查看本组资产

2. **第二步：人员C实现前端组长角色支持**
   - 添加`isLeader`判断到`AuthContext.jsx`
   - 在用户管理页面添加组长角色选项
   - 在资产管理页面实现组长权限控制
   - 组长编辑资产时，使用人选择框只显示本组用户

3. **第三步：联调测试**
   - 测试组长是否能正确查看和操作本组资产
   - 测试组长尝试操作非本组资产时是否正确返回403错误
   - 前端需要捕获403错误并提示：「您只能修改本组资产的使用人」

---

### 📋 待完成的联动工作清单

#### 优先级1：标记离职功能联动（高优先级）

**人员B需要完成：**
1. 实现`PUT /api/users/{user_id}/mark-resignation`接口
2. 接口逻辑：
   - 更新用户status为「离职」
   - 查询该用户名下所有资产
   - 为每条资产调用`create_system_allocated_task`（source=resignation）
   - 返回创建的任务数量

**人员C需要完成：**
- ✅ 前端已完成，无需修改

**预计工作量：**
- 人员B：2-3小时
- 人员C：0小时（已完成）

---

#### 优先级2：组长权限功能联动（中优先级）

**人员B需要完成：**
1. 在`update_asset`函数中添加组长权限校验
2. 在`get_assets`函数中添加组长资产列表过滤
3. 组长只能修改本组资产的使用人
4. 组长只能查看本组资产

**人员C需要完成：**
1. 在`AuthContext.jsx`中添加`isLeader`和`isAdminOrLeader`
2. 在`UserManagement.jsx`中添加组长角色选项和显示
3. 在`AssetManagement.jsx`中实现组长权限控制
4. 组长编辑资产时，使用人选择框过滤为本组用户
5. 添加403错误提示

**预计工作量：**
- 人员B：2-3小时
- 人员C：2-3小时

---

#### 优先级3：调拨联动功能（中优先级）

**人员B需要完成：**
1. 在`update_asset`函数中实现调拨逻辑（创建任务 + pending_reallocations）
2. 在`submit_check_result`函数中处理pending_reallocations

**人员C需要完成：**
- 前端无需修改（调拨通过资产管理页面的编辑功能实现）

**预计工作量：**
- 人员B：3-4小时
- 人员C：0小时

---

### ⚠️ 关键依赖关系

1. **标记离职功能**
   - 人员C前端 ✅ → 等待人员B后端接口 ❌
   - **阻塞状态：** 前端已就绪，等待后端实现

2. **组长权限功能**
   - 人员C前端 ❌ ← 依赖 → 人员B后端 ❌
   - **建议：** 人员B先实现后端权限校验，人员C再实现前端配合

3. **调拨联动功能**
   - 人员B后端 ❌（前端无需修改）
   - **独立实现：** 不影响前端工作

---

### 🎯 建议实现顺序

1. **第一步：人员B实现标记离职接口**（优先级最高）
   - 人员C前端已就绪，可以立即联调
   - 预计1-2天完成

2. **第二步：人员B实现组长权限校验**（优先级高）
   - 完成后，人员C可以开始实现前端配合
   - 预计1-2天完成

3. **第三步：人员C实现组长角色前端**（优先级高）
   - 依赖人员B的权限校验完成
   - 预计1天完成

4. **第四步：人员B实现调拨联动**（优先级中）
   - 不影响前端工作，可以并行进行
   - 预计1-2天完成

---

### 📝 接口规范建议

#### 标记离职接口

**接口路径：** `PUT /api/users/{user_id}/mark-resignation`

**请求：** 无请求体

**响应：**
```json
{
  "message": "标记离职成功",
  "task_count": 5,
  "user": {
    "id": 1,
    "ehr_number": "1234567",
    "real_name": "张三",
    "status": "离职"
  }
}
```

**错误响应：**
- 404：用户不存在
- 400：用户已经是离职状态
- 403：无权限（非管理员）

---

#### 组长权限错误响应

**当组长尝试修改非本组资产的使用人时：**

**响应：** 403 Forbidden
```json
{
  "detail": "您只能修改本组资产的使用人"
}
```

**前端处理：**
```javascript
catch (error) {
  if (error.response?.status === 403) {
    message.error('您只能修改本组资产的使用人')
  } else {
    message.error(error.response?.data?.detail || '操作失败')
  }
}
```

---

## 十一、人员C可独立完成的工作清单

基于人员B当前工作进度，以下工作**不依赖人员B未完成的工作**，人员C可以独立完成：

### ✅ 可以立即完成的工作

#### 1. 任务7的完善：将Modal改为独立页面 ⚠️ **可选完成**

**当前状态：** 功能已完整实现，但以Modal方式集成在安全检查任务管理页面中

**可以完成的工作：**

1. **创建独立页面组件**
   - 文件路径：`frontend/src/pages/SafetyCheckAutoConfig.jsx`
   - 将`SafetyCheckTaskManagement.jsx`中的Modal内容（第1021-1197行）提取为独立页面组件
   - 保持所有功能不变，只是从Modal改为页面

2. **添加路由配置**
   - 在`frontend/src/App.jsx`中添加路由：
     ```jsx
     <Route path="safety-check-auto-config" element={<SafetyCheckAutoConfig />} />
     ```

3. **添加菜单入口**
   - 在`frontend/src/components/Layout.jsx`的菜单中添加入口（仅管理员可见）
   - 可以在「安全检查任务」菜单项下添加子菜单，或作为独立菜单项

**工作量：** 2-3小时

**优先级：** 中（功能已可用，改为独立页面主要是符合文档要求）

**是否必须：** 否（如果产品接受Modal方式，可以不修改）

---

#### 2. 任务9的部分工作：组长角色UI展示 ⚠️ **可以部分完成**

**当前状态：** 组长权限控制需要等待人员B实现，但UI展示部分可以独立完成

**可以完成的工作（不依赖后端）：**

1. **AuthContext.jsx - 添加isLeader判断** ✅ **可独立完成**
   - 添加`isLeader`和`isAdminOrLeader`判断
   - 这只是前端状态判断，不依赖后端接口
   - 代码位置：第88行
   - 修改内容：
     ```jsx
     const value = {
       user,
       loading,
       login,
       logout,
       checkEHR,
       isAdmin: user?.role === 'admin',
       isLeader: user?.role === 'leader',
       isAdminOrLeader: user?.role === 'admin' || user?.role === 'leader'
     }
     ```

2. **UserManagement.jsx - 添加组长角色选项和显示** ✅ **可独立完成**
   - 角色列显示增加组长（第190行）
   - 角色筛选增加组长选项（第278-282行）
   - 角色选择框增加组长选项（第352-355行）
   - 这些都是UI展示，不依赖后端权限校验

3. **AssetManagement.jsx - 部分UI调整** ⚠️ **部分可完成**
   - 可以添加`isLeader`和`isAdminOrLeader`的使用
   - 但是组长权限控制（如使用人选择框过滤、资产列表过滤）需要等待人员B实现后端权限校验
   - 可以先添加基本的UI结构，等后端接口就绪后再完善权限控制逻辑

**工作量：** 1-2小时

**优先级：** 高（为后续权限控制功能做准备）

**注意事项：**
- 这些UI修改不会影响现有功能
- 组长角色的显示和选择已经可以正常工作
- 但是组长的权限控制（如只能编辑本组资产）需要等待人员B实现后端校验

---

### ❌ 不能独立完成的工作

#### 1. 任务8：标记离职功能

**状态：** 前端已完成，等待人员B实现后端接口（任务13）

**原因：** 需要调用后端接口`PUT /api/users/{user_id}/mark-resignation`，该接口尚未实现

**可以做什么：**
- ✅ 前端代码已完成，无需修改
- ⚠️ 可以编写测试用例或文档，但无法实际测试功能

---

#### 2. 任务9：组长权限控制

**状态：** UI展示部分可以完成，但权限控制需要等待人员B实现（任务12）

**不能独立完成的部分：**
- 组长只能编辑本组资产的权限控制
- 组长编辑资产时，使用人选择框只显示本组用户
- 组长只能查看本组资产的列表过滤
- 这些都需要后端接口支持

**原因：**
- 需要后端在`get_assets`接口中实现组长资产列表过滤
- 需要后端在`update_asset`接口中实现组长权限校验
- 前端无法独立实现这些权限控制逻辑

---

### 📋 推荐完成顺序

#### 优先级1：任务9的UI展示部分（推荐立即完成）

**理由：**
- 不依赖人员B的工作
- 为后续权限控制功能做准备
- 工作量小，收益大

**具体工作：**
1. 修改`AuthContext.jsx`添加`isLeader`判断（15分钟）
2. 修改`UserManagement.jsx`添加组长角色选项和显示（30分钟）
3. 修改`AssetManagement.jsx`添加基本的`isLeader`使用（30分钟）

**总工作量：** 约1-1.5小时

---

#### 优先级2：任务7的完善（可选）

**理由：**
- 功能已可用，改为独立页面主要是符合文档要求
- 如果产品接受Modal方式，可以不修改

**具体工作：**
1. 创建`SafetyCheckAutoConfig.jsx`页面组件（1小时）
2. 添加路由配置（15分钟）
3. 添加菜单入口（15分钟）

**总工作量：** 约1.5小时

---

### 📊 完成情况预测

**如果完成优先级1的工作：**

| 任务 | 当前状态 | 完成后的状态 | 完成度提升 |
|------|---------|-------------|-----------|
| 任务7 | ⚠️ 90% | ⚠️ 90% | 0% |
| 任务8 | ✅ 100% | ✅ 100% | 0% |
| 任务9 | ❌ 0% | ⚠️ 60% | +60% |

**总体完成度：** 从63%提升到约83%

**如果同时完成优先级1和优先级2：**

| 任务 | 当前状态 | 完成后的状态 | 完成度提升 |
|------|---------|-------------|-----------|
| 任务7 | ⚠️ 90% | ✅ 100% | +10% |
| 任务8 | ✅ 100% | ✅ 100% | 0% |
| 任务9 | ❌ 0% | ⚠️ 60% | +60% |

**总体完成度：** 从63%提升到约87%

---

### ⚠️ 注意事项

1. **组长权限控制**
   - UI展示部分可以完成，但实际的权限控制需要等待人员B实现后端校验
   - 完成UI后，组长角色可以正常显示和选择，但权限控制功能暂时不可用

2. **测试限制**
   - 标记离职功能无法测试（等待后端接口）
   - 组长权限控制无法测试（等待后端权限校验）

3. **代码质量**
   - 建议在完成UI展示部分时，添加注释说明哪些功能需要等待后端支持
   - 为后续权限控制功能的实现预留接口

---

### 🎯 建议行动方案

**方案A：完成优先级1（推荐）**
- 立即完成任务9的UI展示部分
- 预计工作量：1-1.5小时
- 完成度提升：从63%到83%

**方案B：完成优先级1+2（全面）**
- 完成任务9的UI展示部分 + 任务7的完善
- 预计工作量：2.5-3小时
- 完成度提升：从63%到87%

**方案C：等待人员B完成后再继续（保守）**
- 等待人员B完成标记离职接口和组长权限校验
- 然后一次性完成所有剩余工作
- 风险：可能延长整体项目周期
