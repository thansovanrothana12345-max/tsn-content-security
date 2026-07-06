import os

class Config:
    PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ENV: str = os.getenv("APP_ENV", "production")
    PORT: int = int(os.getenv("APP_PORT", 0)) # 0 dynamically allocates a free port on startup
    DATABASE_URL: str = os.getenv("DATABASE_URL", os.path.join(PROJECT_ROOT, "storage", "database.db"))
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "storage")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "7a3b4c9e8d1f2a3b4c9e8d1f2a3b4c9e")
    SESSION_EXPIRE_HOURS: int = 24
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local") # 'local', 's3', 'r2'
    DEVELOPMENT_BYPASS_AUTH: bool = os.getenv("DEVELOPMENT_BYPASS_AUTH", "False").lower() in ("true", "1", "yes")
    
    # S3 / R2 Configurations (Optional fallback placeholders)
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_BUCKET_NAME: str = os.getenv("AWS_BUCKET_NAME", "")
    R2_ENDPOINT_URL: str = os.getenv("R2_ENDPOINT_URL", "")
