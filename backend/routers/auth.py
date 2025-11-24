"""
认证相关路由
包括登录、EHR号验证等
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from schemas import EHRCheck, EHRCheckResponse, LoginRequest, LoginResponse
from auth import (
    authenticate_user, 
    create_access_token, 
    get_user_by_ehr,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from datetime import timedelta

router = APIRouter()


@router.post("/check-ehr", response_model=EHRCheckResponse)
async def check_ehr(
    ehr_data: EHRCheck,
    db: Session = Depends(get_db)
):
    """
    检查EHR号是否存在，如果存在则返回用户名
    用于登录界面输入EHR号后回显用户名
    """
    user = get_user_by_ehr(db, ehr_data.ehr_number)
    if user:
        return EHRCheckResponse(exists=True, real_name=user.real_name)
    else:
        return EHRCheckResponse(exists=False, real_name=None)


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录
    使用EHR号和密码进行登录，返回JWT token
    """
    user = authenticate_user(db, login_data.ehr_number, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="EHR号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.ehr_number, "role": user.role},
        expires_delta=access_token_expires
    )
    
    from schemas import UserResponse
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )




