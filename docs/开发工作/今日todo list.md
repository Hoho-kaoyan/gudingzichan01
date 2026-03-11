# 今日todo

本文档作为当天的待办与规划，作为**当前待完成事项**的唯一清单。agent 可核对已完成内容后更新已完成工作清单。

---

## 需求变化

1. 希望管理员名下可以有自己的资产，可以对自己名下的资产进行检查。
2. 审批完之后应该有一条已审批记录。
3. 管理员菜单添加「我的安全检查任务」入口；组长菜单添加「安全检查任务」入口。
4. 标记离职后，该用户名下所有资产都应生成安全检查任务（含终端/数据安全检查）。
5. 发布安全检查任务时，搜索关键字应该包含所有字段
6. 交接申请需要在它所联动的安全检查完成后发起
7. 安全检查任务模块可以按照状态筛选
8. 发起安全检查任务的时候需要按照执行人发，如果没有执行人则发给使用人
9. 需要修改使用人的场景下也需要同步修改执行人
10. 资产需要添加新的字段：可用状态（或者别的名称）

---

## bug

1. **修改使用人/使用人组别后的提示**：保存时当前提示「成功」→ 应改为提示「已发布检查任务」或类似，以区分普通编辑与触发检查任务的场景。
2. **选择使用人后未自动带出**：选择使用人后应自动填入「使用人组别」「EHR 号」「安全检查执行人」「执行人 EHR 号」等，当前未自动带出。
3. **用户信息栏位名称不明确**：人员相关展示需明确标注「姓名」「EHR 号」等栏位名称，避免混淆。
4. **没有产生编辑申请**：预期为普通用户走编辑申请、组长仅组内直接更新。当前实现已符合；若仍复现，排查 DB 角色、assets.py 的 old_values、前端对 `message: "编辑申请已提交"` 的识别。
5. **时区问题**：已按方案 A 实现——API 返回 datetime 统一为东八区 ISO 字符串（`utils_time.datetime_to_east8_iso` + schemas `East8Datetime`），前端无需改。
6. **联动安全检查问题**：预期只查本单资产。已落实：创建交接/退库均仅校验本单资产是否已完成安检（创建交接去掉全局检查，创建退库改为本单资产检查）；确认与审批交接本就只查本单资产。
7. 发起交接任务，如果联动发起了检查任务，那么交接任务状态应为“待完成联动安全检查”
8. 撤回交接任务应该能同时撤回因发起交接任务而联动发起的检查任务。
9. **安全检查任务在某些情况下没有红点提示**：当前逻辑下管理员不显示「我的安全检查任务」红点（TransferContext 中 role===admin 时待检查数置 0）；与需求 1 一致，应改为管理员也拉取并显示待检查数。见上方实现顺序中 Bug 9 说明。

10. **【已修复】returns.py 缺少 logger 导入**：记录退回历史失败时会报 `NameError: name 'logger' is not defined`，已补 `from logger import logger`。
11. **退库审批使用人置空时未同步清空执行人**：approvals.py 审批退回时，情况2/3（使用人置空、退回在库）只置空了 `user_id`/`user_group`，未置空 `safety_check_executor_id`/`safety_check_executor_name`，与「改使用人时同步改执行人」规则不一致。
12. **审批交接禁止转入人为管理员**：approvals.py 中 to_user.role == "admin" 会直接拒绝，与需求 1（管理员名下可有资产）可能冲突，需确认业务上是否允许交接给管理员。
13. **任务编号并发竞态**：safety_check_tasks 的 generate_task_number 用「今年数量+1」生成编号，高并发下可能重复，触发唯一约束错误；建议用序列或插入失败重试。
14. **资产双可用状态字段**：Asset 同时存在 `available_status` 与 `availability_status`，易混淆且可能导致数据不一致，建议统一或废弃其一。
15. **导入 Excel 单行异常导致前面行被回滚**：assets 导入循环内某行异常时 `db.rollback()` 会回滚本请求内已成功行，当前行为是「任一行失败则本次全部不提交」，若需「尽量保留成功行」需改成分行提交或 savepoint。

**已完成（bug）**：
- Bug 4：编辑申请（当前实现已符合，普通用户走编辑申请、组长组内直接更新）
- Bug 5：时区（已按方案 A 实现，API 返回东八区 ISO）
- Bug 6：联动安检只查本单（创建交接/退库仅校验本单资产已完成）
- Bug 10：returns.py 缺少 logger 导入（已修复）

---

## 实现顺序与风险说明

**已完成（需求/功能）**：
- 3：菜单（管理员「我的安全检查任务」+「安全检查任务」，组长「安全检查任务」）
- 1：管理员资产与自检（使用人可为管理员，可执行分配给自己的任务）
- 7：任务按状态筛选
- 8：按执行人发任务（`safety_check_executor_id or user_id`）
- 9：改使用人时同步改执行人
- 10：资产可用状态
- 2：审批后已审批记录（已审批 Tab）

| 顺序 | 需求/ Bug | 说明与依赖 | 对现有代码的潜在影响 |
|------|-----------|------------|----------------------|
| **1** | **4. 离职全资产生成任务** | 标记离职后该用户**全部**资产生成安全检查任务，且含终端/数据类。核对现有离职联动是否已覆盖全部资产、检查类型是否含终端/数据。 | 若当前按「部分资产」或部分类型创建，改为全量/全类型可能增加任务量，需确认业务与性能。 |
| **2** | **5. 任务搜索全字段** | 发布安全检查任务时搜索关键字覆盖所有相关字段。后端/前端搜索参数与接口扩展。 | 仅扩展搜索条件，注意 SQL 与索引，避免全表模糊查。 |
| **3** | **6 + Bug 7/8** | 6：交接需联动安检完成后发起（状态与体验）。Bug 7：交接单状态展示「待完成联动安全检查」。Bug 8：撤回交接时同时撤回因该交接联动的检查任务。 | **Bug 8** 需建立「交接单 ↔ 联动任务」关联（如 TransferRequest 存关联 task_id，或 SafetyCheckTask 存 source_extra）；取消任务/撤回交接顺序要约定，避免状态不一致。**Bug 7** 依赖能否查到「该交接单关联的未完成任务」，与 Bug 8 共用关联数据。 |

### 待修复 Bug 实现顺序（原因与需改代码）

| 顺序 | Bug | 原因 | 需改代码/位置 |
|------|-----|------|----------------|
| **B1** | **Bug 1 修改使用人后的提示** | 前端资产保存后统一用「更新成功」，未区分「仅编辑」与「触发检查任务」两种场景，用户无法感知已下发安检任务。 | 前端 `AssetManagement.jsx`：PUT 成功后根据 payload 是否包含使用人/组别变更（或后端返回 `triggered_safety_check: true`），提示「已发布检查任务」而非「更新成功」；或后端在更新资产接口返回该标识，前端据此分支提示。 |
| **B2** | **Bug 2 选择使用人后未自动带出** | 表单中「使用人」与「使用人组别」「EHR」「检查执行人」「执行人 EHR」独立填写，未做联动回填。 | 前端 `AssetManagement.jsx`：使用人 `select_user` 变更时，根据选中 user 自动 setFieldsValue 填入 `user_group`、`safety_check_executor_id`/`safety_check_executor_name` 及 EHR（需用户列表或详情含 ehr_number/real_name/group）。 |
| **B3** | **Bug 3 用户信息栏位名称不明确** | 人员相关展示未统一标注「姓名」「EHR 号」等，易与编号/ID 混淆。 | 前端：资产/交接/审批等涉及人员展示的列表与表单，为「姓名」「EHR 号」等加 label 或表头明确标注（如 `姓名(real_name)`、`EHR号(ehr_number)`）。 |
| **B4** | **Bug 7 交接单状态「待完成联动安全检查」** | 创建交接时若联动下发了安检任务，交接单状态仍为「待转入人确认」等，未体现「待完成联动安检」。 | 后端：`TransferRequest` 增加可选字段如 `linked_safety_task_id`；创建交接且 `create_system_allocated_task` 返回 task 后写入并 commit。状态逻辑：若存在未完成的 linked 任务则展示/计算为「待完成联动安全检查」。前端：交接列表/详情根据该字段或接口返回的派生状态展示「待完成联动安全检查」。 |
| **B5** | **Bug 8 撤回交接同时撤回联动检查任务** | 撤回交接只删除了 `TransferRequest`，未处理创建交接时联动的 SafetyCheckTask，导致任务仍存在。 | 后端：`TransferRequest` 存 `linked_safety_task_id`（与 Bug 7 一起）。`cancel_transfer_request` 中：若 `request.linked_safety_task_id` 存在，将对应 `SafetyCheckTask` 状态置为 `cancelled`（并可选将关联 `TaskAsset` 一并取消），再删除交接。需迁移为 `transfer_requests` 表增加 `linked_safety_task_id`。 |
| **B6** | **Bug 9 红点提示（管理员）** | `TransferContext` 中 `fetchPendingSafetyChecks` 在 `user.role === 'admin'` 时直接 `setPendingSafetyCheckCount(0)`，管理员不拉取待检查数。 | 前端 `contexts/TransferContext.jsx`：去掉 `if (!user || user.role === 'admin') { setPendingSafetyCheckCount(0); return }`，管理员也调用 `/safety-check-results/my-tasks`（或等价接口）拉取待检查数并展示红点。 |
| **B7** | **Bug 11 退库审批未清空执行人** | 退库审批通过时情况2/3 只置空 `user_id`/`user_group`，未置空执行人，与「使用人置空则执行人同步」不一致。 | 后端 `routers/approvals.py`：在「情况2」与「情况3」分支中，`asset.user_id = None`、`asset.user_group = None` 后增加 `asset.safety_check_executor_id = None`、`asset.safety_check_executor_name = None`。 |
| **B8** | **Bug 12 审批交接禁止转入人为管理员** | 需求 1 允许管理员名下可有资产，审批逻辑仍禁止 to_user.role == "admin"，与需求冲突。 | 后端 `routers/approvals.py`：审批交接通过处删除或注释 `if to_user.role == "admin": raise HTTPException(..., "使用人不能是管理员")`；若业务确需禁止，则保留并在文档注明。 |
| **B9** | **Bug 13 任务编号并发竞态** | `generate_task_number` 用「今年任务 count+1」生成编号，并发请求可能得到相同 count，插入时唯一约束冲突。 | 后端 `routers/safety_check_tasks.py`：方案一：生成编号后插入，若唯一约束冲突则重试生成（如带随机后缀或时间戳）。方案二：用数据库序列/自增或 `SELECT MAX(task_number)+1 FOR UPDATE` 等保证唯一。 |
| **B10** | **Bug 14 资产双可用状态字段** | `Asset` 同时有 `available_status` 与 `availability_status`，语义重叠，易导致展示/导入不一致。 | 后端：统一只保留 `available_status`（枚举：可用/维修中/已报废）。`models.py`/schemas 中废弃或删除 `availability_status`；迁移历史数据到 `available_status` 后删列；`asset_history`、`assets` 导入导出、冲突解析等处去掉对 `availability_status` 的引用。 |
| **B11** | **Bug 15 导入 Excel 单行异常导致前面行回滚** | 导入循环内某行异常时 `db.rollback()` 会回滚整个事务，本请求内已成功写入的行也被撤销。 | 后端 `routers/assets.py` 导入：若希望「尽量保留成功行」，可改为每行在 savepoint 内处理，失败只回滚到 savepoint；或每行单独 commit（需注意会话与性能）。若保持「任一行失败则本次全部不提交」，在文档中明确说明即可，可不改代码。 |

**Bug 9（红点提示）**：与上表 B6 一致，管理员也拉取并显示「我的安全检查任务」待检查数。

**小结**：需求实现顺序 1 → 2 → 3（离职全资产生成任务 → 任务搜索全字段 → 6 与 Bug 7/8）。待修复 Bug 可按 B1～B11 排期；B4/B5 依赖同一数据（TransferRequest 存 linked_safety_task_id），建议一起做；B7、B8 为后端小改动可优先。

