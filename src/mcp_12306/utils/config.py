"""配置管理"""

import logging
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """应用配置"""
    server_host: str = Field(default="0.0.0.0", description="服务器主机地址")
    server_port: int = Field(default=8000, description="服务器端口")
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置实例"""
    global _settings
    if _settings is None:
        env_file_path = Path(".env")
        if not env_file_path.exists():
            logger.warning(f"环境配置文件 {env_file_path.absolute()} 不存在，使用默认配置")
        else:
            logger.info(f"加载环境配置文件: {env_file_path.absolute()}")
        
        try:
            _settings = Settings()
            logger.info(f"配置加载成功 - 主机: {_settings.server_host}, 端口: {_settings.server_port}, 调试模式: {_settings.debug}, 日志级别: {_settings.log_level}")
        except Exception as e:
            logger.error(f"配置加载失败: {e}，使用默认配置")
            _settings = Settings.model_validate({})
    
    return _settings