"""
资产大类管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import AssetCategory
from schemas import AssetCategoryCreate, AssetCategoryResponse
from auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[AssetCategoryResponse])
async def get_categories(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取所有资产大类"""
    categories = db.query(AssetCategory).all()
    return [AssetCategoryResponse.model_validate(cat) for cat in categories]


@router.post("/", response_model=AssetCategoryResponse)
async def create_category(
    category_data: AssetCategoryCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建资产大类"""
    # 检查是否已存在
    existing = db.query(AssetCategory).filter(AssetCategory.name == category_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="该大类已存在")
    
    db_category = AssetCategory(name=category_data.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return AssetCategoryResponse.model_validate(db_category)
