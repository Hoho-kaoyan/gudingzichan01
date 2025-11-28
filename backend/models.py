"""
数据库模型定义
包含用户、资产、审批流程等模型
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
import json


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    ADMIN = "admin"  # 管理员
    USER = "user"    # 普通用户


class AssetStatus(str, enum.Enum):
    """资产状态枚举"""
    IN_USE = "在用"      # 在用
    IN_STOCK = "库存备用"  # 库存备用


class ApprovalStatus(str, enum.Enum):
    """审批状态枚举"""
    WAITING_CONFIRMATION = "waiting_confirmation"  # 待转入人确认
    PENDING = "pending"    # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    CONFIRMATION_REJECTED = "confirmation_rejected"  # 转入人拒绝


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    ehr_number = Column(String(7), unique=True, index=True, nullable=False, comment="7位数字EHR号")
    real_name = Column(String(100), nullable=False, comment="真实姓名")
    group = Column(String(50), nullable=False, comment="组别")
    role = Column(String(20), default=UserRole.USER.value, nullable=False, comment="角色：admin或user")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    assets = relationship("Asset", back_populates="user", foreign_keys="Asset.user_id")
    transfer_requests = relationship("TransferRequest", back_populates="from_user", foreign_keys="TransferRequest.from_user_id")
    received_transfers = relationship("TransferRequest", back_populates="to_user", foreign_keys="TransferRequest.to_user_id")


class AssetCategory(Base):
    """资产大类模型"""
    __tablename__ = "asset_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, comment="大类名称，如：办公用品、电子设备配件")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    assets = relationship("Asset", back_populates="category")


class Asset(Base):
    """固定资产模型"""
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 实物情况
    asset_number = Column(String(100), unique=True, index=True, nullable=False, comment="资产编号")
    category_id = Column(Integer, ForeignKey("asset_categories.id"), nullable=False, comment="所属大类ID")
    name = Column(String(200), nullable=False, comment="实物名称")
    specification = Column(String(200), nullable=True, comment="规格型号（可为空）")
    status = Column(String(20), default=AssetStatus.IN_USE.value, nullable=False, comment="状态：在用或库存备用")
    mac_address = Column(String(50), nullable=True, comment="MAC地址")
    ip_address = Column(String(50), nullable=True, comment="IP地址")
    
    # 盘点情况
    office_location = Column(String(200), nullable=True, comment="存放办公地点")
    floor = Column(String(50), nullable=True, comment="存放楼层")
    seat_number = Column(String(50), nullable=True, comment="座位号（非必填）")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="使用人ID（为空表示在仓库）")
    user_group = Column(String(50), nullable=True, comment="使用人组别")
    remark = Column(Text, nullable=True, comment="备注说明（非必填）")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, comment="删除时间（软删除）")
    deleted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="删除人ID")
    
    # 关系
    category = relationship("AssetCategory", back_populates="assets")
    user = relationship("User", back_populates="assets", foreign_keys=[user_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])


class TransferRequest(Base):
    """资产交接申请模型"""
    __tablename__ = "transfer_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, comment="资产ID")
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="转出用户ID")
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="转入用户ID")
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="申请创建人ID（可能是管理员代为申请）")
    reason = Column(Text, nullable=True, comment="交接原因")
    status = Column(String(20), default=ApprovalStatus.WAITING_CONFIRMATION.value, nullable=False, comment="审批状态")
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="审批人ID")
    approval_comment = Column(Text, nullable=True, comment="审批意见")
    to_user_confirmed = Column(Integer, nullable=True, comment="转入人确认状态：1-已确认，0-已拒绝，NULL-待确认")
    to_user_confirm_comment = Column(Text, nullable=True, comment="转入人确认备注")
    to_user_confirmed_at = Column(DateTime(timezone=True), nullable=True, comment="转入人确认时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True, comment="审批时间")
    
    # 关系
    asset = relationship("Asset")
    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="transfer_requests")
    to_user = relationship("User", foreign_keys=[to_user_id], back_populates="received_transfers")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approver = relationship("User", foreign_keys=[approver_id])


class ReturnRequest(Base):
    """资产退回仓库申请模型"""
    __tablename__ = "return_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, comment="资产ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="退回用户ID")
    reason = Column(Text, nullable=True, comment="退回原因")
    status = Column(String(20), default=ApprovalStatus.PENDING.value, nullable=False, comment="审批状态")
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="审批人ID")
    approval_comment = Column(Text, nullable=True, comment="审批意见")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True, comment="审批时间")
    
    # 申请人修改的字段（可选，用于审批时更新资产）
    mac_address = Column(String(50), nullable=True, comment="申请人修改的MAC地址")
    ip_address = Column(String(50), nullable=True, comment="申请人修改的IP地址")
    office_location = Column(String(200), nullable=True, comment="申请人修改的存放办公地点")
    floor = Column(String(50), nullable=True, comment="申请人修改的存放楼层")
    seat_number = Column(String(50), nullable=True, comment="申请人修改的座位号")
    new_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="申请人修改的保管人ID")
    remark = Column(Text, nullable=True, comment="申请人修改的备注说明")
    
    # 关系
    asset = relationship("Asset")
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approver_id])
    new_user = relationship("User", foreign_keys=[new_user_id])


class AssetHistory(Base):
    """资产流转记录模型"""
    __tablename__ = "asset_history"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, comment="资产ID")
    action_type = Column(String(50), nullable=False, comment="操作类型：create/edit/transfer/return/approve/edit_approve")
    action_description = Column(Text, nullable=True, comment="操作描述")
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="操作人ID")
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="审批人ID（如有）")
    old_value = Column(Text, nullable=True, comment="旧值（JSON格式）")
    new_value = Column(Text, nullable=True, comment="新值（JSON格式）")
    related_request_id = Column(Integer, nullable=True, comment="关联的申请ID（交接、退回或编辑）")
    related_request_type = Column(String(20), nullable=True, comment="关联申请类型：transfer/return/edit")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="操作时间")
    
    # 关系
    asset = relationship("Asset")
    operator = relationship("User", foreign_keys=[operator_id])
    approver = relationship("User", foreign_keys=[approver_id])


class AssetEditRequest(Base):
    """资产编辑申请模型"""
    __tablename__ = "asset_edit_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, comment="资产ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="申请人ID")
    status = Column(String(20), default=ApprovalStatus.PENDING.value, nullable=False, comment="审批状态")
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="审批人ID")
    approval_comment = Column(Text, nullable=True, comment="审批意见")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True, comment="审批时间")
    
    # 申请人修改的字段（JSON格式存储）
    edit_data = Column(Text, nullable=False, comment="编辑数据（JSON格式）")
    
    # 关系
    asset = relationship("Asset")
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approver_id])


class SafetyCheckType(Base):
    """安全检查类型模型"""
    __tablename__ = "safety_check_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, comment="检查类型名称")
    description = Column(Text, nullable=True, comment="检查类型描述")
    check_items = Column(Text, nullable=True, comment="检查项列表（JSON格式）")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人ID")
    
    # 关系
    created_by = relationship("User", foreign_keys=[created_by_id])
    tasks = relationship("SafetyCheckTask", back_populates="check_type")
    
    def get_check_items(self):
        """获取检查项列表（解析JSON）"""
        if self.check_items:
            try:
                return json.loads(self.check_items)
            except:
                return []
        return []
    
    def set_check_items(self, items):
        """设置检查项列表（转换为JSON）"""
        self.check_items = json.dumps(items, ensure_ascii=False) if items else None


class SafetyCheckTask(Base):
    """安全检查任务模型"""
    __tablename__ = "safety_check_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_number = Column(String(50), unique=True, nullable=False, index=True, comment="任务编号")
    check_type_id = Column(Integer, ForeignKey("safety_check_types.id"), nullable=False, comment="检查类型ID")
    title = Column(String(200), nullable=False, comment="任务标题")
    description = Column(Text, nullable=True, comment="任务描述")
    deadline = Column(DateTime(timezone=True), nullable=True, comment="截止时间")
    status = Column(String(20), default="pending", nullable=False, comment="任务状态：pending/completed/overdue/cancelled")
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建人ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")
    
    # 关系
    check_type = relationship("SafetyCheckType", back_populates="tasks")
    created_by = relationship("User", foreign_keys=[created_by_id])
    task_assets = relationship("TaskAsset", back_populates="task", cascade="all, delete-orphan")


class TaskAsset(Base):
    """任务资产关联模型"""
    __tablename__ = "task_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("safety_check_tasks.id"), nullable=False, comment="任务ID")
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, comment="资产ID")
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="分配用户ID（资产使用人）")
    status = Column(String(20), default="pending", nullable=False, comment="检查状态：pending/checked/overdue/returned")
    check_result = Column(String(20), nullable=True, comment="检查结果：yes/no")
    check_comment = Column(Text, nullable=True, comment="检查备注")
    check_items_result = Column(Text, nullable=True, comment="检查项结果（JSON格式）")
    checked_at = Column(DateTime(timezone=True), nullable=True, comment="检查时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    task = relationship("SafetyCheckTask", back_populates="task_assets")
    asset = relationship("Asset")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    history_records = relationship("SafetyCheckHistory", back_populates="task_asset")
    
    def get_check_items_result(self):
        """获取检查项结果（解析JSON）"""
        if self.check_items_result:
            try:
                return json.loads(self.check_items_result)
            except:
                return []
        return []
    
    def set_check_items_result(self, items):
        """设置检查项结果（转换为JSON）"""
        self.check_items_result = json.dumps(items, ensure_ascii=False) if items else None

    def set_check_items_result(self, items):
        """设置检查项结果（转换为JSON）"""
        self.check_items_result = json.dumps(items, ensure_ascii=False) if items else None

    def set_check_items_result(self, items):
        """设置检查项结果（转换为JSON）"""
        self.check_items_result = json.dumps(items, ensure_ascii=False) if items else None


class SafetyCheckHistory(Base):
    """安全检查历史记录模型"""
    __tablename__ = "safety_check_history"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("safety_check_tasks.id"), nullable=False, comment="任务ID")
    task_asset_id = Column(Integer, ForeignKey("task_assets.id"), nullable=False, comment="任务资产关联ID")
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, comment="资产ID")
    check_type_id = Column(Integer, ForeignKey("safety_check_types.id"), nullable=False, comment="检查类型ID")
    checked_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="检查人ID")
    check_result = Column(String(20), nullable=False, comment="检查结果：yes/no")
    check_comment = Column(Text, nullable=True, comment="检查备注")
    check_items_result = Column(Text, nullable=True, comment="检查项结果（JSON格式）")
    checked_at = Column(DateTime(timezone=True), nullable=False, comment="检查时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    task = relationship("SafetyCheckTask")
    task_asset = relationship("TaskAsset", back_populates="history_records")
    asset = relationship("Asset")
    check_type = relationship("SafetyCheckType")
    checked_by = relationship("User", foreign_keys=[checked_by_id])
    
    def get_check_items_result(self):
        """获取检查项结果（解析JSON）"""
        if self.check_items_result:
            try:
                return json.loads(self.check_items_result)
            except:
                return []
        return []
    
    def set_check_items_result(self, items):
        """设置检查项结果（转换为JSON）"""
        self.check_items_result = json.dumps(items, ensure_ascii=False) if items else None
