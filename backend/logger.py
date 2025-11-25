"""
日志配置模块
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 创建logs目录
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志格式
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 创建logger
logger = logging.getLogger('asset_management')
logger.setLevel(logging.INFO)

# 避免重复添加handler
if not logger.handlers:
    # 文件handler - 按日期和大小轮转
    log_file = os.path.join(log_dir, f'asset_management_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # 控制台只显示警告和错误
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
