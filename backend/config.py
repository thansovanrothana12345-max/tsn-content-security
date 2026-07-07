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

    # Similarity Thresholds & Settings
    SIMILARITY_VIDEO_THRESHOLD: float = 0.80
    SIMILARITY_IMAGE_THRESHOLD: float = 0.85
    SIMILARITY_AUDIO_THRESHOLD: float = 0.80

    # File Upload Limits
    MAX_ASSET_UPLOAD_SIZE: int = 50 * 1024 * 1024       # 50MB
    MAX_ATTACHMENT_UPLOAD_SIZE: int = 20 * 1024 * 1024  # 20MB

    # Background Job Queue Configs
    QUEUE_POLLING_INTERVAL: float = 2.0
    QUEUE_MAX_RETRIES: int = 3
    SUPPORTED_PLATFORMS: list = ["YouTube", "TikTok", "Instagram", "Facebook Post", "Facebook Ad Library", "Website"]

    # AI and Background Tasks Configurations
    AI_INFERENCE_TIMEOUT: float = float(os.getenv("AI_INFERENCE_TIMEOUT", "120.0"))
    AI_MODEL_RETRY_COUNT: int = int(os.getenv("AI_MODEL_RETRY_COUNT", "3"))
    AI_MODEL_RETRY_BACKOFF: float = float(os.getenv("AI_MODEL_RETRY_BACKOFF", "2.0"))
    DETECTION_CACHE_ENABLED: bool = os.getenv("DETECTION_CACHE_ENABLED", "True").lower() in ("true", "1", "yes")
    DETECTION_CACHE_TTL: int = int(os.getenv("DETECTION_CACHE_TTL", str(30 * 24 * 3600))) # 30 days
    USE_CONCURRENT_WORKER: bool = os.getenv("USE_CONCURRENT_WORKER", "True").lower() in ("true", "1", "yes")
    MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", "4"))

    # Sprint 6 Additions
    METRICS_ENABLED: bool = os.getenv("METRICS_ENABLED", "True").lower() in ("true", "1", "yes")
    TELEMETRY_ENABLED: bool = os.getenv("TELEMETRY_ENABLED", "True").lower() in ("true", "1", "yes")
    AI_MODEL_IDLE_TIMEOUT: float = float(os.getenv("AI_MODEL_IDLE_TIMEOUT", "600.0")) # 10 minutes default
    CALIBRATION_SIGMOID_A: float = float(os.getenv("CALIBRATION_SIGMOID_A", "-12.0")) # Platt scaling slope
    CALIBRATION_SIGMOID_B: float = float(os.getenv("CALIBRATION_SIGMOID_B", "9.6"))   # Platt scaling intercept
    CONFIDENCE_WEIGHTS_CALIBRATED: dict = {
        "video": 0.35,
        "audio": 0.25,
        "ocr": 0.15,
        "logo": 0.15,
        "metadata": 0.10
    }

    @classmethod
    def validate_config(cls):
        """Runs security and schema checks on configuration variables."""
        errors = []
        
        # 1. Type validation
        if not isinstance(cls.SECRET_KEY, str):
            errors.append("SECRET_KEY must be a string.")
        if not isinstance(cls.DATABASE_URL, str):
            errors.append("DATABASE_URL must be a string.")
            
        # 2. Security validation
        if cls.SECRET_KEY == "7a3b4c9e8d1f2a3b4c9e8d1f2a3b4c9e" or len(cls.SECRET_KEY) < 16:
            print("[SECURITY WARNING] SECRET_KEY is set to default or is too short (< 16 chars). Please override in production!")
            
        if cls.DEVELOPMENT_BYPASS_AUTH:
            print("[SECURITY WARNING] DEVELOPMENT_BYPASS_AUTH is enabled. Do not use in production!")
            
        # 3. Model settings validation
        total_weights = sum(cls.CONFIDENCE_WEIGHTS_CALIBRATED.values())
        if abs(total_weights - 1.0) > 0.001:
            errors.append(f"CONFIDENCE_WEIGHTS_CALIBRATED must sum to 1.0, current sum is {total_weights}")
            
        if errors:
            raise ValueError(f"Configuration Validation Failed: {'; '.join(errors)}")
            
        print("[CONFIG] System configurations validated successfully.")


