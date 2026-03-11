"""
Pydantic模式定义
用于API请求和响应的数据验证
"""
from pydantic import BaseModel, Field, validator, field_validator, PlainSerializer
from typing import Optional, List, Literal, Annotated
from datetime import datetime, date
from enum import Enum
import json

from utils_time import datetime_to_east8_iso


def _serialize_east8(v: Optional[datetime]) -> Optional[str]:
    """序列化 datetime 为东八区 ISO 字符串（API 返回用）"""
    return datetime_to_east8_iso(v)


# 用于 Response 的 datetime：JSON 序列化时统一输出东八区带时区字符串（如 2026-03-10T10:00:00+08:00）
East8Datetime = Annotated[
    datetime,
    PlainSerializer(_serialize_east8, return_type=str, when_used="json"),
]


# 用户相关模式
class UserBase(BaseModel):
    ehr_number: str = Field(..., min_length=7, max_length=7, description="7位数字EHR号")
    real_name: str = Field(..., description="真实姓名")
    group: str = Field(..., description="组别")
    role: str = Field(default="user", description="角色：admin或user")
    status: str = Field(default="在岗", description="状态：在岗/离职/长期出差/借调/产假等")
    
    @validator('ehr_number')
    def validate_ehr_number(cls, v):
        if not v.isdigit():
            raise ValueError('EHR号必须为7位数字')
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="密码")


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    group: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = None


class PasswordChange(BaseModel):
    """当前用户修改自己的密码"""
    old_password: str = Field(..., description="原密码")
    new_password: str = Field(..., min_length=6, description="新密码")


class UserResponse(UserBase):
    id: int
    created_at: East8Datetime
    updated_at: Optional[East8Datetime] = None
    
    class Config:
        from_attributes = True


# 登录相关模式
class EHRCheck(BaseModel):
    ehr_number: str = Field(..., min_length=7, max_length=7)
    
    @validator('ehr_number')
    def validate_ehr_number(cls, v):
        if not v.isdigit():
            raise ValueError('EHR号必须为7位数字')
        return v


class EHRCheckResponse(BaseModel):
    exists: bool
    real_name: Optional[str] = None


class LoginRequest(BaseModel):
    ehr_number: str = Field(..., min_length=7, max_length=7)
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# 资产大类模式
class AssetCategoryBase(BaseModel):
    name: str = Field(..., description="大类名称")


class AssetCategoryCreate(AssetCategoryBase):
    pass


class AssetCategoryResponse(AssetCategoryBase):
    id: int
    created_at: East8Datetime
    
    class Config:
        from_attributes = True


# 资产相关模式
class AssetBase(BaseModel):
    asset_number: str = Field(..., description="资产编号")
    category_id: int = Field(..., description="所属大类ID")
    name: str = Field(..., description="实物名称")
    specification: Optional[str] = Field(None, description="规格型号")
    status: str = Field(default="在用", description="状态：在用或在库")
    available_status: str = Field(default="可用", description="可用状态：可用/维修中/已报废")
    availability_status: Optional[str] = Field(None, description="可用状态：如可用/不可用/维修中等")
    mac_address: Optional[str] = Field(None, description="MAC地址")
    ip_address: Optional[str] = Field(None, description="IP地址")
    office_location: Optional[str] = Field(None, description="存放办公地点")
    floor: Optional[str] = Field(None, description="存放楼层")
    seat_number: Optional[str] = Field(None, description="座位号（非必填）")
    user_id: Optional[int] = Field(None, description="使用人ID")
    user_group: Optional[str] = Field(None, description="使用人组别")
    remark: Optional[str] = Field(None, description="备注说明（非必填）")
    quantity: Optional[int] = Field(None, description="件数")
    team: Optional[str] = Field(None, description="所在团队")
    purchase_date: Optional[date] = Field(None, description="购置日期")
    card_number: Optional[str] = Field(None, description="卡片编号")
    safety_check_executor_id: Optional[int] = Field(None, description="检查执行人ID")
    safety_check_executor_name: Optional[str] = Field(None, description="检查执行人姓名")
    computer_type: Optional[str] = Field(None, description="电脑类型")
    computer_usage: Optional[str] = Field(None, description="电脑应用")
    computer_name: Optional[str] = Field(None, description="计算机名")
    monitor1_model: Optional[str] = Field(None, description="连接显示器1型号")
    monitor1_asset_number: Optional[str] = Field(None, description="连接显示器1资产编号")
    monitor1_serial: Optional[str] = Field(None, description="显示器1序列号")
    monitor2_model: Optional[str] = Field(None, description="连接显示器2型号")
    monitor2_asset_number: Optional[str] = Field(None, description="连接显示器2资产编号")
    monitor2_serial: Optional[str] = Field(None, description="显示器2序列号")
    asset_contact: Optional[str] = Field(None, description="资产管理联系人")
    reserve_1: Optional[str] = Field(None, description="预留1")
    reserve_2: Optional[str] = Field(None, description="预留2")
    reserve_3: Optional[str] = Field(None, description="预留3")
    reserve_4: Optional[str] = Field(None, description="预留4")
    reserve_5: Optional[str] = Field(None, description="预留5")
    reserve_6: Optional[str] = Field(None, description="预留6")


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    specification: Optional[str] = None
    status: Optional[str] = None
    available_status: Optional[str] = None
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    office_location: Optional[str] = None
    floor: Optional[str] = None
    seat_number: Optional[str] = None
    user_id: Optional[int] = None
    user_group: Optional[str] = None
    remark: Optional[str] = None
    quantity: Optional[int] = None
    team: Optional[str] = None
    purchase_date: Optional[date] = None
    card_number: Optional[str] = None
    safety_check_executor_id: Optional[int] = None
    safety_check_executor_name: Optional[str] = None
    computer_type: Optional[str] = None
    computer_usage: Optional[str] = None
    computer_name: Optional[str] = None
    monitor1_model: Optional[str] = None
    monitor1_asset_number: Optional[str] = None
    monitor1_serial: Optional[str] = None
    monitor2_model: Optional[str] = None
    monitor2_asset_number: Optional[str] = None
    monitor2_serial: Optional[str] = None
    asset_contact: Optional[str] = None
    reserve_1: Optional[str] = None
    reserve_2: Optional[str] = None
    reserve_3: Optional[str] = None
    reserve_4: Optional[str] = None
    reserve_5: Optional[str] = None
    reserve_6: Optional[str] = None


class AssetResponse(AssetBase):
    id: int
    created_at: East8Datetime
    updated_at: Optional[East8Datetime] = None
    category: Optional[AssetCategoryResponse] = None
    user: Optional[UserResponse] = None
    safety_check_executor: Optional["UserResponse"] = None
    
    class Config:
        from_attributes = True


# 交接申请模式
class TransferRequestCreate(BaseModel):
    asset_id: int = Field(..., description="资产ID")
    to_user_id: int = Field(..., description="转入用户ID")
    reason: Optional[str] = Field(None, description="交接原因")


class TransferConfirmationRequest(BaseModel):
    """转入人确认请求"""
    confirmed: bool = Field(..., description="是否确认：true-确认，false-拒绝")
    comment: Optional[str] = Field(None, description="确认备注")


class TransferRequestResponse(BaseModel):
    id: int
    asset_id: int
    from_user_id: int
    to_user_id: int
    created_by_id: Optional[int] = None
    reason: Optional[str] = None
    status: str
    approver_id: Optional[int] = None
    approval_comment: Optional[str] = None
    to_user_confirmed: Optional[int] = None
    to_user_confirm_comment: Optional[str] = None
    to_user_confirmed_at: Optional[East8Datetime] = None
    created_at: East8Datetime
    updated_at: Optional[East8Datetime] = None
    approved_at: Optional[East8Datetime] = None
    asset: Optional[AssetResponse] = None
    from_user: Optional[UserResponse] = None
    to_user: Optional[UserResponse] = None
    created_by: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


# 退回申请模式
class ReturnRequestCreate(BaseModel):
    asset_id: int = Field(..., description="资产ID")
    reason: Optional[str] = Field(None, description="退回原因")
    # 申请人可修改的字段
    mac_address: Optional[str] = Field(None, description="申请人修改的MAC地址")
    ip_address: Optional[str] = Field(None, description="申请人修改的IP地址")
    office_location: Optional[str] = Field(None, description="申请人修改的存放办公地点")
    floor: Optional[str] = Field(None, description="申请人修改的存放楼层")
    seat_number: Optional[str] = Field(None, description="申请人修改的座位号")
    new_user_id: Optional[int] = Field(None, description="申请人修改的保管人ID")
    remark: Optional[str] = Field(None, description="申请人修改的备注说明")


class ReturnRequestResponse(BaseModel):
    id: int
    asset_id: int
    user_id: int
    reason: Optional[str] = None
    status: str
    approver_id: Optional[int] = None
    approval_comment: Optional[str] = None
    created_at: East8Datetime
    updated_at: Optional[East8Datetime] = None
    approved_at: Optional[East8Datetime] = None
    # 申请人修改的字段
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    office_location: Optional[str] = None
    floor: Optional[str] = None
    seat_number: Optional[str] = None
    new_user_id: Optional[int] = None
    remark: Optional[str] = None
    asset: Optional[AssetResponse] = None
    user: Optional[UserResponse] = None
    new_user: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


# 审批模式
class ApprovalRequest(BaseModel):
    request_id: int = Field(..., description="申请ID")
    request_type: str = Field(..., description="申请类型：transfer、return或edit")
    approved: bool = Field(..., description="是否批准")
    comment: Optional[str] = Field(None, description="审批意见")


# 批量导入响应
class ImportErrorDetail(BaseModel):
    """导入错误详情"""
    row_number: int = Field(..., description="行号（Excel中的行号，从2开始，第1行是表头）")
    error_message: str = Field(..., description="错误信息")
    row_data: dict = Field(default_factory=dict, description="该行的原始数据")


class ImportConflictDiff(BaseModel):
    """导入冲突：单个字段的数据库值与导入值差异"""
    field_label: str = Field(..., description="字段中文名")
    db_value: str = Field(..., description="数据库中当前值（展示用）")
    import_value: str = Field(..., description="导入文件中的值（展示用）")


class ImportConflictDetail(BaseModel):
    """导入冲突详情：资产已存在且部分字段与导入数据不一致"""
    row_number: int = Field(..., description="Excel 行号")
    asset_number: str = Field(..., description="资产编号")
    asset_id: int = Field(..., description="资产ID，用于解决冲突时指定")
    diffs: List[ImportConflictDiff] = Field(default_factory=list, description="不一致的字段列表")
    row_data: dict = Field(default_factory=dict, description="该行原始数据，解决覆盖时需回传")


class ImportResponse(BaseModel):
    success_count: int
    error_count: int
    skip_count: int = Field(default=0, description="静默跳过的重复行数（已存在且完全一致）")
    errors: List[str] = []  # 保持向后兼容
    error_details: List[ImportErrorDetail] = Field(default_factory=list, description="详细的失败原因")
    conflict_count: int = Field(default=0, description="与数据库存在差异的条数（待用户选择覆盖或保持）")
    conflict_details: List[ImportConflictDetail] = Field(default_factory=list, description="冲突详情，含差异字段与行数据")


# 导入冲突解决请求
class ImportResolveDecision(BaseModel):
    asset_id: int = Field(..., description="资产ID")
    action: Literal["overwrite", "keep"] = Field(..., description="overwrite=用导入数据覆盖，keep=保持数据库不变")
    row_data: Optional[dict] = Field(None, description="覆盖时必传，与 conflict_details 中该条的 row_data 一致")


class ImportResolveRequest(BaseModel):
    decisions: List[ImportResolveDecision] = Field(..., description="每条冲突的选择")


# 资产编辑申请模式
class AssetEditRequestCreate(BaseModel):
    asset_id: int = Field(..., description="资产ID")
    edit_data: dict = Field(..., description="编辑数据（JSON格式）")


class AssetEditRequestResponse(BaseModel):
    id: int
    asset_id: int
    user_id: int
    status: str
    approver_id: Optional[int] = None
    approval_comment: Optional[str] = None
    created_at: East8Datetime
    updated_at: Optional[East8Datetime] = None
    approved_at: Optional[East8Datetime] = None
    edit_data: dict
    asset: Optional[AssetResponse] = None
    user: Optional[UserResponse] = None
    approver: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


# 安全检查相关模式
class CheckItem(BaseModel):
    """检查项"""
    item: str = Field(..., description="检查项内容")
    required: bool = Field(default=False, description="是否必填")


class SafetyCheckTypeBase(BaseModel):
    name: str = Field(..., description="检查类型名称")
    description: Optional[str] = Field(None, description="检查类型描述")
    check_items: Optional[List[CheckItem]] = Field(None, description="检查项列表")
    is_active: bool = Field(default=True, description="是否启用")

    @field_validator("check_items", mode="before")
    @classmethod
    def parse_check_items(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                data = json.loads(v)
                return data
            except Exception:
                return None
        return v

class SafetyCheckTypeCreate(SafetyCheckTypeBase):
    pass


class SafetyCheckTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    check_items: Optional[List[CheckItem]] = None
    is_active: Optional[bool] = None


class SafetyCheckTypeResponse(SafetyCheckTypeBase):
    id: int
    created_at: East8Datetime
    updated_at: Optional[East8Datetime] = None
    created_by_id: Optional[int] = None
    created_by: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


class SafetyCheckTaskCreate(BaseModel):
    check_type_id: int = Field(..., description="检查类型ID")
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    asset_ids: List[int] = Field(..., description="资产ID列表")
    deadline: Optional[datetime] = Field(None, description="截止时间")

    @field_validator("deadline", mode="before")
    @classmethod
    def parse_deadline(cls, v):
        if v in (None, "", "null"):
            return None
        return v


class SafetyCheckTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    status: Optional[str] = None

    @field_validator("deadline", mode="before")
    @classmethod
    def parse_deadline(cls, v):
        if v in (None, "", "null"):
            return None
        return v


class SafetyCheckTaskResponse(BaseModel):
    id: int
    task_number: str
    check_type_id: int
    title: str
    description: Optional[str] = None
    deadline: Optional[East8Datetime] = None
    status: str
    source: Optional[str] = None  # manual/inbound/transfer/reallocation/resignation
    created_by_id: int
    created_at: East8Datetime
    updated_at: Optional[East8Datetime] = None
    completed_at: Optional[East8Datetime] = None
    check_type: Optional[SafetyCheckTypeResponse] = None
    created_by: Optional[UserResponse] = None
    total_assets: Optional[int] = None  # 总资产数
    completed_assets: Optional[int] = None  # 已完成资产数
    pending_assets: Optional[int] = None  # 待检查资产数
    my_assets_count: Optional[int] = None  # 当前用户的资产数（普通用户）
    my_completed_count: Optional[int] = None  # 当前用户已完成的资产数
    
    class Config:
        from_attributes = True


# ---------- 联动安全检查配置 ----------
class SafetyCheckAutoConfigResponse(BaseModel):
    id: int
    default_check_type_id: Optional[int] = None
    created_at: Optional[East8Datetime] = None
    updated_at: Optional[East8Datetime] = None
    default_check_type: Optional[SafetyCheckTypeResponse] = None

    class Config:
        from_attributes = True


class SafetyCheckAutoConfigUpdate(BaseModel):
    default_check_type_id: Optional[int] = None


class SafetyCheckAssetTypeMappingCreate(BaseModel):
    asset_type: str = Field(..., description="实物名称，如终端、显示器")
    check_type_id: int = Field(..., description="检查类型ID")


class SafetyCheckAssetTypeMappingUpdate(BaseModel):
    check_type_id: int = Field(..., description="检查类型ID")


class SafetyCheckAssetTypeMappingResponse(BaseModel):
    id: int
    asset_type: str
    check_type_id: int
    created_at: East8Datetime
    check_type: Optional[SafetyCheckTypeResponse] = None

    class Config:
        from_attributes = True


class TaskAssetResponse(BaseModel):
    id: int
    task_id: int
    asset_id: int
    assigned_user_id: int
    status: str
    check_result: Optional[str] = None
    check_comment: Optional[str] = None
    check_items_result: Optional[List[dict]] = None
    checked_at: Optional[East8Datetime] = None
    created_at: East8Datetime
    updated_at: Optional[East8Datetime] = None
    asset: Optional[AssetResponse] = None
    assigned_user: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


class CheckItemResult(BaseModel):
    """检查项结果"""
    item: str = Field(..., description="检查项内容")
    result: str = Field(..., description="检查结果：yes/no")
    comment: Optional[str] = Field(None, description="备注")


class SafetyCheckResultSubmit(BaseModel):
    """提交检查结果"""
    task_asset_id: int = Field(..., description="任务资产关联ID")
    check_result: str = Field(..., description="整体检查结果：yes/no")
    check_comment: Optional[str] = Field(None, description="检查备注")
    check_items_result: List[CheckItemResult] = Field(..., description="检查项结果列表")


class SafetyCheckHistoryResponse(BaseModel):
    id: int
    task_id: int
    task_asset_id: int
    asset_id: int
    check_type_id: int
    checked_by_id: int
    check_result: str
    check_comment: Optional[str] = None
    check_items_result: Optional[List[dict]] = None
    checked_at: East8Datetime
    created_at: East8Datetime
    task_number: Optional[str] = None
    check_type: Optional[SafetyCheckTypeResponse] = None
    asset: Optional[AssetResponse] = None
    checked_by: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True
