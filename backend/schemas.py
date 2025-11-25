"""
Pydantic模式定义
用于API请求和响应的数据验证
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# 用户相关模式
class UserBase(BaseModel):
    ehr_number: str = Field(..., min_length=7, max_length=7, description="7位数字EHR号")
    real_name: str = Field(..., description="真实姓名")
    group: str = Field(..., description="组别")
    role: str = Field(default="user", description="角色：admin或user")
    
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
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
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
    created_at: datetime
    
    class Config:
        from_attributes = True


# 资产相关模式
class AssetBase(BaseModel):
    asset_number: str = Field(..., description="资产编号")
    category_id: int = Field(..., description="所属大类ID")
    name: str = Field(..., description="实物名称")
    specification: Optional[str] = Field(None, description="规格型号")
    status: str = Field(default="在用", description="状态：在用或库存备用")
    mac_address: Optional[str] = Field(None, description="MAC地址")
    ip_address: Optional[str] = Field(None, description="IP地址")
    office_location: Optional[str] = Field(None, description="存放办公地点")
    floor: Optional[str] = Field(None, description="存放楼层")
    seat_number: Optional[str] = Field(None, description="座位号（非必填）")
    user_id: Optional[int] = Field(None, description="使用人ID")
    user_group: Optional[str] = Field(None, description="使用人组别")
    remark: Optional[str] = Field(None, description="备注说明（非必填）")


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    specification: Optional[str] = None
    status: Optional[str] = None
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    office_location: Optional[str] = None
    floor: Optional[str] = None
    seat_number: Optional[str] = None
    user_id: Optional[int] = None
    user_group: Optional[str] = None
    remark: Optional[str] = None


class AssetResponse(AssetBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional[AssetCategoryResponse] = None
    user: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True


# 交接申请模式
class TransferRequestCreate(BaseModel):
    asset_id: int = Field(..., description="资产ID")
    to_user_id: int = Field(..., description="转入用户ID")
    reason: Optional[str] = Field(None, description="交接原因")


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
    created_at: datetime
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
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
    created_at: datetime
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
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
class ImportResponse(BaseModel):
    success_count: int
    error_count: int
    errors: List[str] = []


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
    created_at: datetime
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    edit_data: dict
    asset: Optional[AssetResponse] = None
    user: Optional[UserResponse] = None
    approver: Optional[UserResponse] = None
    
    class Config:
        from_attributes = True
