"""
FastAPI主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth, users, assets, transfers, returns, approvals, categories, stats, asset_history, edit_requests
import uvicorn
# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(
    title="固定资产管理系统",
    description="用于固定资产管理的系统，支持资产增删改查、交接、审批等功能",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React开发服务器端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户管理"])
app.include_router(categories.router, prefix="/api/categories", tags=["资产大类"])
app.include_router(assets.router, prefix="/api/assets", tags=["资产管理"])
app.include_router(transfers.router, prefix="/api/transfers", tags=["资产交接"])
app.include_router(returns.router, prefix="/api/returns", tags=["资产退回"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["审批管理"])
app.include_router(stats.router, prefix="/api/stats", tags=["统计信息"])
app.include_router(asset_history.router, prefix="/api/asset-history", tags=["资产流转记录"])
app.include_router(edit_requests.router, prefix="/api/edit-requests", tags=["资产编辑申请"])


@app.get("/")
async def root():
    """根路径"""
    return {"message": "固定资产管理系统API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 

