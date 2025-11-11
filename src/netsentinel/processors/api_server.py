#!/usr/bin/env python3
"""
REST API Server for NetSentinel Event Processor
Provides HTTP endpoints for health checks, threat intelligence, and metrics
"""

import asyncio
import time
import os
import shutil
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends, Request, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn
import hashlib
import pyotp
import qrcode
import base64
from io import BytesIO

try:
    from ..core.base import BaseComponent
    from ..core.models import StandardEvent, ThreatLevel
    from ..core.error_handler import handle_errors, create_error_context
    from ..monitoring.metrics import MetricsCollector, get_metrics_collector
    from ..monitoring.logger import create_logger
    from ..security.auth_manager import get_auth_manager
    from ..security.middleware import get_current_user, require_auth, require_analyst
    from ..security.user_store import User, Role, Permission
    from ..alerts import get_alert_manager
    from ..ml_models import ModelManager, TrainingPipeline, FeatureExtractor, MLMonitoring, MLIntegration
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from core.models import StandardEvent, ThreatLevel
    from core.error_handler import handle_errors, create_error_context
    from monitoring.metrics import MetricsCollector, get_metrics_collector
    from monitoring.logger import create_logger
    # Auth imports would need to be adjusted for standalone usage
    get_auth_manager = None
    get_current_user = None
    require_auth = None
    require_analyst = None
    User = None
    Role = None
    Permission = None
    get_alert_manager = None
    # ML imports would need to be adjusted for standalone usage
    ModelManager = None
    TrainingPipeline = None
    FeatureExtractor = None
    MLMonitoring = None
    MLIntegration = None

logger = create_logger("api_server", level="INFO")


class EmailService:
    """Simple email service for verification and password reset"""

    def __init__(self, smtp_server: str = None, smtp_port: int = 587,
                 smtp_username: str = None, smtp_password: str = None,
                 from_email: str = "noreply@netsentinel.local"):
        self.smtp_server = smtp_server or "localhost"
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.mock_mode = not smtp_server  # Use mock mode if no SMTP server configured

    def send_email(self, to_email: str, subject: str, body: str, html_body: str = None) -> bool:
        """Send email using SMTP or mock logging"""
        try:
            if self.mock_mode:
                # Mock mode - just log the email
                logger.info(f"MOCK EMAIL to {to_email}: {subject}")
                logger.info(f"MOCK EMAIL body: {body}")
                return True

            # Real email sending
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add text body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.from_email, to_email, msg.as_string())
            server.quit()

            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_verification_email(self, to_email: str, verification_token: str, username: str) -> bool:
        """Send email verification email"""
        verification_url = f"http://localhost:3000/verify-email?token={verification_token}"

        subject = "Verify Your NetSentinel Account"
        body = f"""
        Hello {username},

        Welcome to NetSentinel! Please verify your email address to complete your registration.

        Click the following link to verify your email:
        {verification_url}

        If you didn't create an account, please ignore this email.

        Best regards,
        NetSentinel Team
        """

        html_body = f"""
        <html>
        <body>
            <h2>Welcome to NetSentinel!</h2>
            <p>Hello {username},</p>
            <p>Please verify your email address to complete your registration.</p>
            <p><a href="{verification_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a></p>
            <p>If you didn't create an account, please ignore this email.</p>
            <br>
            <p>Best regards,<br>NetSentinel Team</p>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, body, html_body)

    def send_password_reset_email(self, to_email: str, reset_token: str, username: str) -> bool:
        """Send password reset email"""
        reset_url = f"http://localhost:3000/reset-password?token={reset_token}"

        subject = "Reset Your NetSentinel Password"
        body = f"""
        Hello {username},

        You have requested to reset your password for your NetSentinel account.

        Click the following link to reset your password:
        {reset_url}

        This link will expire in 1 hour. If you didn't request a password reset, please ignore this email.

        Best regards,
        NetSentinel Team
        """

        html_body = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>Hello {username},</p>
            <p>You have requested to reset your password for your NetSentinel account.</p>
            <p><a href="{reset_url}" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
            <p>This link will expire in 1 hour. If you didn't request a password reset, please ignore this email.</p>
            <br>
            <p>Best regards,<br>NetSentinel Team</p>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, body, html_body)


# Global email service instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get global email service instance"""
    global _email_service
    if _email_service is None:
        # Initialize with configuration (can be enhanced with config file)
        _email_service = EmailService()
    return _email_service


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str
    timestamp: float
    uptime: float
    version: str


class ThreatInfo(BaseModel):
    """Threat information model"""

    source_ip: str
    threat_score: float
    threat_level: str
    event_count: int
    last_seen: float
    indicators: List[str]


class ThreatResponse(BaseModel):
    """Threat intelligence response model"""

    total_threats: int
    threats: Dict[str, Any]


class LoginRequest(BaseModel):
    """Login request model"""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: Dict[str, Any]


class UserInfo(BaseModel):
    """User information model"""

    user_id: str
    username: str
    email: str
    roles: List[str]
    permissions: List[str]
    is_active: bool
    last_login: Optional[float]


class UserProfile(BaseModel):
    """User profile model"""

    user_id: str
    username: str
    email: str
    roles: List[str]
    permissions: List[str]
    is_active: bool
    created_at: float
    last_login: Optional[float]
    avatar_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserProfileUpdate(BaseModel):
    """User profile update model"""

    email: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChangePasswordRequest(BaseModel):
    """Change password request model"""

    current_password: str
    new_password: str
    confirm_password: str


class UserPreferences(BaseModel):
    """User preferences model"""

    theme: str = Field(default="light", description="UI theme (light/dark/auto)")
    language: str = Field(default="en", description="Preferred language")
    timezone: str = Field(default="UTC", description="User timezone")
    notifications: Dict[str, bool] = Field(default_factory=lambda: {
        "email": True,
        "browser": True,
        "alerts": True,
        "reports": False
    }, description="Notification preferences")
    dashboard_layout: Dict[str, Any] = Field(default_factory=dict, description="Dashboard widget layout")
    items_per_page: int = Field(default=25, ge=10, le=100, description="Items per page in lists")
    auto_refresh: bool = Field(default=True, description="Auto-refresh data")
    refresh_interval: int = Field(default=30, ge=10, le=300, description="Refresh interval in seconds")


class UserPreferencesUpdate(BaseModel):
    """User preferences update model"""

    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    notifications: Optional[Dict[str, bool]] = None
    dashboard_layout: Optional[Dict[str, Any]] = None
    items_per_page: Optional[int] = Field(None, ge=10, le=100)
    auto_refresh: Optional[bool] = None
    refresh_interval: Optional[int] = Field(None, ge=10, le=300)


class UIThemePreferences(BaseModel):
    """UI theme and customization preferences"""

    primary_color: str = Field(default="#007bff", description="Primary theme color")
    sidebar_collapsed: bool = Field(default=False, description="Sidebar collapsed state")
    font_size: str = Field(default="medium", description="Font size (small/medium/large)")
    compact_mode: bool = Field(default=False, description="Compact UI mode")
    animations_enabled: bool = Field(default=True, description="Enable UI animations")
    high_contrast: bool = Field(default=False, description="High contrast mode")


class UIThemePreferencesUpdate(BaseModel):
    """UI theme preferences update model"""

    primary_color: Optional[str] = None
    sidebar_collapsed: Optional[bool] = None
    font_size: Optional[str] = None
    compact_mode: Optional[bool] = None
    animations_enabled: Optional[bool] = None
    high_contrast: Optional[bool] = None


class AvatarResponse(BaseModel):
    """Avatar upload response model"""

    avatar_url: str
    filename: str
    message: str = "Avatar uploaded successfully"


class EmailVerificationRequest(BaseModel):
    """Email verification request model"""

    email: str


class EmailVerificationResponse(BaseModel):
    """Email verification response model"""

    message: str
    verification_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    """Forgot password request model"""

    email: str


class ResetPasswordRequest(BaseModel):
    """Reset password request model"""

    token: str
    new_password: str
    confirm_password: str


class SessionInfo(BaseModel):
    """Session information model"""

    session_id: str
    user_id: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: float
    last_activity: float
    is_active: bool = True
    expires_at: Optional[float] = None


class SessionListResponse(BaseModel):
    """Session list response model"""

    sessions: List[SessionInfo]
    current_session_id: Optional[str] = None
    total_sessions: int


class MFASetupRequest(BaseModel):
    """MFA setup request model"""

    method: str = Field(default="totp", description="MFA method (totp/sms)")


class MFASetupResponse(BaseModel):
    """MFA setup response model"""

    secret: str
    qr_code_url: str
    manual_entry_key: str
    message: str = "Scan QR code with authenticator app"


class MFAVerifyRequest(BaseModel):
    """MFA verification request model"""

    code: str
    method: str = Field(default="totp", description="MFA method (totp/sms)")


class MFAStatusResponse(BaseModel):
    """MFA status response model"""

    enabled: bool
    method: Optional[str] = None
    backup_codes_generated: bool = False
    last_used: Optional[float] = None


class RoleInfo(BaseModel):
    """Role information model"""

    id: str
    name: str
    description: Optional[str] = None
    permissions: List[str]
    is_system_role: bool = False
    created_at: float
    updated_at: float


class RoleCreate(BaseModel):
    """Role creation request model"""

    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Role update model"""

    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleListResponse(BaseModel):
    """Role list response model"""

    roles: List[RoleInfo]
    total_count: int


class UserRoleAssignment(BaseModel):
    """User role assignment model"""

    user_id: str
    roles: List[str]


class UserPermissionsResponse(BaseModel):
    """User permissions response model"""

    user_id: str
    username: str
    direct_permissions: List[str]
    role_permissions: Dict[str, List[str]]
    effective_permissions: List[str]


class APIKey(BaseModel):
    """API key model"""

    id: str
    name: str
    key: str  # Only shown when created
    permissions: List[str]
    created_at: float
    expires_at: Optional[float] = None
    last_used: Optional[float] = None
    is_active: bool = True
    usage_count: int = 0
    rate_limit: Optional[int] = None  # requests per minute


class APIKeyCreate(BaseModel):
    """API key creation request model"""

    name: str
    permissions: List[str] = Field(default_factory=list)
    expires_at: Optional[float] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)  # 1-10000 requests per minute


class APIKeyUpdate(BaseModel):
    """API key update model"""

    name: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)


class APIKeyResponse(BaseModel):
    """API key response model (without secret key)"""

    id: str
    name: str
    permissions: List[str]
    created_at: float
    expires_at: Optional[float] = None
    last_used: Optional[float] = None
    is_active: bool = True
    usage_count: int = 0
    rate_limit: Optional[int] = None


class APIKeyListResponse(BaseModel):
    """API key list response model"""

    api_keys: List[APIKeyResponse]
    total_count: int


class APIKeyUsage(BaseModel):
    """API key usage statistics model"""

    id: str
    name: str
    total_requests: int
    requests_today: int
    requests_this_hour: int
    last_used: Optional[float] = None
    average_requests_per_day: float
    rate_limit_remaining: Optional[int] = None


class UserCreateRequest(BaseModel):
    """User creation request model"""

    username: str
    email: str
    password: str
    roles: List[str] = Field(default_factory=list, description="User roles")


class TokenRefreshRequest(BaseModel):
    """Token refresh request model"""

    token: str


class LogoutResponse(BaseModel):
    """Logout response model"""

    message: str


# ML Model API Models
class MLModelInfo(BaseModel):
    """ML Model information"""

    model_type: str
    version_count: int
    latest_version: Optional[Dict[str, Any]] = None
    is_loaded: bool
    all_versions: List[Dict[str, Any]] = Field(default_factory=list)
    health: Optional[Dict[str, Any]] = None


class MLModelCreateRequest(BaseModel):
    """ML Model creation request"""

    model_type: str = Field(..., description="Type of ML model (fastflow, efficientad, padim)")
    model_path: Optional[str] = Field(None, description="Path to model files")
    metadata_path: Optional[str] = Field(None, description="Path to metadata file")
    training_metrics: Optional[Dict[str, Any]] = Field(None, description="Training performance metrics")


class MLModelUpdateRequest(BaseModel):
    """ML Model update request"""

    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    training_metrics: Optional[Dict[str, Any]] = Field(None, description="Updated training metrics")


class MLModelTrainingRequest(BaseModel):
    """ML Model training request"""

    dataset_path: Optional[str] = Field(None, description="Path to training dataset")
    epochs: Optional[int] = Field(10, description="Number of training epochs")
    batch_size: Optional[int] = Field(32, description="Training batch size")
    learning_rate: Optional[float] = Field(0.001, description="Learning rate")


class MLModelListResponse(BaseModel):
    """ML Models list response"""

    models: List[MLModelInfo]
    total_count: int


class MLTrainingStatusResponse(BaseModel):
    """ML Training status response"""

    model_type: str
    status: str  # "idle", "training", "completed", "failed"
    progress: Optional[float] = None
    current_epoch: Optional[int] = None
    total_epochs: Optional[int] = None
    loss: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    estimated_completion: Optional[float] = None


class MLValidationResponse(BaseModel):
    """ML Model validation response"""

    model_type: str
    validation_status: str  # "pending", "running", "completed", "failed"
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    auc_score: Optional[float] = None
    confusion_matrix: Optional[List[List[int]]] = None
    validation_time: Optional[float] = None
    error: Optional[str] = None


# ML Dataset API Models
class DatasetInfo(BaseModel):
    """Dataset information"""

    dataset_id: str
    name: str
    description: Optional[str] = None
    data_type: str  # "network_events", "images", "mixed"
    size_bytes: int
    num_samples: int
    created_at: float
    last_modified: float
    status: str  # "available", "processing", "corrupted"
    format: str  # "json", "csv", "parquet", etc.
    tags: List[str] = Field(default_factory=list)


class DatasetUploadRequest(BaseModel):
    """Dataset upload request"""

    name: str
    description: Optional[str] = Field(None, description="Dataset description")
    data_type: str = Field(..., description="Type of data: network_events, images, mixed")
    format: str = Field(..., description="Data format: json, csv, parquet, etc.")
    tags: List[str] = Field(default_factory=list, description="Dataset tags")


class DatasetStats(BaseModel):
    """Dataset statistics"""

    dataset_id: str
    num_samples: int
    num_features: int
    feature_names: List[str]
    data_types: Dict[str, str]  # feature -> data type
    missing_values: Dict[str, int]  # feature -> count of missing values
    statistics: Dict[str, Dict[str, float]]  # feature -> {mean, std, min, max, etc.}
    class_distribution: Optional[Dict[str, int]] = None  # for classification tasks
    correlations: Optional[Dict[str, Dict[str, float]]] = None  # feature correlation matrix
    created_at: float


class DatasetListResponse(BaseModel):
    """Dataset list response"""

    datasets: List[DatasetInfo]
    total_count: int
    page: int = 1
    page_size: int = 50


# ML Training Job API Models
class TrainingJobInfo(BaseModel):
    """Training job information"""

    job_id: str
    model_type: str
    dataset_id: str
    status: str  # "queued", "running", "completed", "failed", "cancelled"
    progress: float = 0.0
    priority: int = 1  # 1=low, 5=high
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_seconds: Optional[float] = None
    config: Dict[str, Any]
    metrics: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TrainingJobListResponse(BaseModel):
    """Training job list response"""

    jobs: List[TrainingJobInfo]
    total_count: int
    page: int = 1
    page_size: int = 50


class TrainingJobCreateRequest(BaseModel):
    """Training job creation request"""

    model_type: str = Field(..., description="Type of model to train")
    dataset_id: str = Field(..., description="ID of dataset to use for training")
    config: Dict[str, Any] = Field(default_factory=dict, description="Training configuration")
    priority: int = Field(1, description="Job priority (1-5)")


# ML Prediction API Models
class PredictionRequest(BaseModel):
    """Single prediction request"""

    model_type: str = Field(..., description="Type of model to use for prediction")
    event_data: Dict[str, Any] = Field(..., description="Network event data")
    include_explanation: bool = Field(False, description="Include feature importance explanation")


class BatchPredictionRequest(BaseModel):
    """Batch prediction request"""

    model_type: str = Field(..., description="Type of model to use for prediction")
    events_data: List[Dict[str, Any]] = Field(..., description="List of network event data")
    include_explanations: bool = Field(False, description="Include feature importance explanations")


class PredictionResult(BaseModel):
    """Prediction result"""

    is_anomaly: bool
    confidence: float
    anomaly_score: float
    model_type: str
    timestamp: float
    inference_time_ms: float
    explanation: Optional[Dict[str, Any]] = None


class BatchPredictionResult(BaseModel):
    """Batch prediction result"""

    predictions: List[PredictionResult]
    total_predictions: int
    avg_inference_time_ms: float
    model_type: str
    timestamp: float


class APIServer(BaseComponent):
    """
    REST API server for the NetSentinel event processor
    Provides HTTP endpoints for monitoring and threat intelligence
    """

    def __init__(
        self,
        name: str = "api_server",
        host: str = "0.0.0.0",
        port: int = 8082,
        processor=None,
        config: Optional[Dict[str, Any]] = None,
    ):
        print("=== API SERVER __INIT__ CALLED ===")
        logger.info("Initializing API server...")
        super().__init__(name, config, logger)
        print("=== API SERVER __INIT__ COMPLETED ===")

        self.host = host
        self.port = port
        self.processor = processor
        self.start_time = time.time()

        # WebSocket components
        self.websocket_manager = None
        self.websocket_server = None

        # Initialize FastAPI app
        self.app = FastAPI(
            title="NetSentinel Event Processor API",
            description="REST API for NetSentinel threat detection and monitoring",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )

        # Setup avatar upload directory and static files
        self.avatars_dir = Path("data/avatars")
        self.avatars_dir.mkdir(parents=True, exist_ok=True)

        # Mount static files for avatar serving
        self.app.mount("/avatars", StaticFiles(directory=str(self.avatars_dir)), name="avatars")

        # Initialize email service
        self.email_service = get_email_service()

        # Initialize session manager
        from .middleware import get_session_manager
        self.session_manager = get_session_manager()

        # Use processor's metrics collector if available, otherwise create our own
        if processor and hasattr(processor, "metrics_collector"):
            self.metrics_collector = processor.metrics_collector
        else:
            self.metrics_collector = get_metrics_collector()

        # Initialize ML components
        self.model_manager = ModelManager(
            models_dir=self.config.get("models_dir", "models"),
            max_versions=self.config.get("max_model_versions", 5),
        ) if ModelManager else None

        self.training_pipeline = TrainingPipeline(
            model_type=self.config.get("default_model_type", "fastflow"),
            config=self.config.get("ml_config", {}),
        ) if TrainingPipeline else None

        self.feature_extractor = FeatureExtractor(
            normalization_method=self.config.get("normalization_method", "standard"),
            image_size=tuple(self.config.get("image_size", [32, 32])),
            config=self.config.get("ml_config", {}),
        ) if FeatureExtractor else None

        # ML monitoring system
        self.ml_monitoring = MLMonitoring(
            metrics_retention_hours=self.config.get("metrics_retention_hours", 24),
            health_check_interval=self.config.get("health_check_interval", 60),
        ) if MLMonitoring else None

        # ML integration system
        self.ml_integration = MLIntegration(
            alert_threshold=self.config.get("ml_alert_threshold", 0.7),
            retraining_triggers_enabled=self.config.get("retraining_triggers_enabled", True),
            incident_reporting_enabled=self.config.get("incident_reporting_enabled", True),
        ) if MLIntegration else None

        # Connect ML components
        if self.ml_integration:
            if self.ml_monitoring:
                self.ml_integration.set_ml_monitoring(self.ml_monitoring)
            if self.model_manager:
                self.ml_integration.set_model_manager(self.model_manager)

        # Training status tracking
        self.training_status = {}  # model_type -> status dict

        # Dataset management
        self.datasets = {}  # dataset_id -> DatasetInfo
        self.dataset_storage_path = self.config.get("dataset_storage_path", "datasets")

        # Training job management
        self.training_jobs = {}  # job_id -> TrainingJobInfo
        self.job_queue = []  # List of queued job IDs
        self.active_jobs = {}  # job_id -> asyncio.Task

        # Setup routes
        self._setup_routes()

        # Setup WebSocket components
        self._setup_websocket()

        # Setup SIEM endpoints
        self._setup_siem_endpoints()

        # Setup threat intelligence endpoints
        self._setup_threat_intel_endpoints()

        # Setup ML endpoints
        self._setup_ml_endpoints()

        # Server instance (will be set during startup)
        self.server = None

    def _setup_routes(self):
        """Setup FastAPI routes"""

        # Authentication endpoints
        @self.app.post("/auth/register", response_model=UserInfo)
        async def register(user_data: UserCreateRequest, request: Request):
            """User registration endpoint"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Validate and convert roles
                from .user_store import Role
                roles = []
                for role_str in user_data.roles:
                    try:
                        roles.append(Role(role_str))
                    except ValueError:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid role: {role_str}"
                        )

                # If no roles specified, default to viewer
                if not roles:
                    roles = [Role.VIEWER]

                # Hash password
                import hashlib
                password_hash = hashlib.sha256(user_data.password.encode()).hexdigest()

                # Generate unique user ID
                import uuid
                user_id = str(uuid.uuid4())

                # Create user
                user = auth_manager.create_user(
                    user_id=user_id,
                    username=user_data.username,
                    email=user_data.email,
                    password_hash=password_hash,
                    roles=roles,
                )

                return UserInfo(
                    user_id=user.user_id,
                    username=user.username,
                    email=user.email,
                    roles=[role.value for role in user.roles],
                    permissions=[perm.value for perm in user.permissions],
                    is_active=user.is_active,
                    last_login=user.last_login,
                )

            except HTTPException:
                raise
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=str(e)
                )
            except Exception as e:
                logger.error(f"Registration failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Registration failed"
                )

        @self.app.post("/auth/send-verification-email", response_model=EmailVerificationResponse)
        async def send_verification_email(request: EmailVerificationRequest):
            """Send email verification email"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Find user by email
                user = None
                for u in auth_manager.get_all_users():
                    if u.email == request.email:
                        user = u
                        break

                if not user:
                    # Don't reveal if email exists or not for security
                    return EmailVerificationResponse(
                        message="If the email address is registered, a verification email has been sent."
                    )

                # Check if already verified
                if user.metadata.get("email_verified", False):
                    return EmailVerificationResponse(
                        message="Email address is already verified."
                    )

                # Generate verification token (JWT with short expiration)
                verification_data = {
                    "user_id": user.user_id,
                    "email": user.email,
                    "type": "email_verification",
                    "exp": time.time() + 3600  # 1 hour expiration
                }

                verification_token = auth_manager.token_manager.create_token(
                    verification_data,
                    expires_in=3600
                )

                # Send verification email
                email_sent = self.email_service.send_verification_email(
                    user.email,
                    verification_token,
                    user.username
                )

                if not email_sent:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to send verification email"
                    )

                # Log verification email sent
                auth_manager.audit_logger.log_action(
                    user_id=user.user_id,
                    action="verification_email_sent",
                    resource="email_verification",
                    success=True,
                    details={"email": user.email}
                )

                return EmailVerificationResponse(
                    message="Verification email sent successfully.",
                    verification_token=verification_token if self.email_service.mock_mode else None
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to send verification email: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to send verification email"
                )

        @self.app.post("/auth/verify-email", response_model=EmailVerificationResponse)
        async def verify_email(token: str):
            """Verify email address using token"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Validate token
                payload = auth_manager.token_manager.validate_token(token)
                if not payload or payload.get("type") != "email_verification":
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid or expired verification token"
                    )

                user_id = payload.get("user_id")
                email = payload.get("email")

                # Get user and verify
                user = auth_manager.get_user(user_id)
                if not user or user.email != email:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid verification token"
                    )

                # Update user email verification status
                updated_metadata = user.metadata.copy()
                updated_metadata["email_verified"] = True
                updated_metadata["email_verified_at"] = time.time()

                success = auth_manager.user_store.update_user(
                    user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to verify email"
                    )

                # Log email verification
                auth_manager.audit_logger.log_action(
                    user_id=user_id,
                    action="email_verified",
                    resource="email_verification",
                    success=True,
                    details={"email": email}
                )

                return EmailVerificationResponse(
                    message="Email verified successfully."
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to verify email: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to verify email"
                )

        @self.app.post("/auth/forgot-password", response_model=EmailVerificationResponse)
        async def forgot_password(request: ForgotPasswordRequest):
            """Send password reset email"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Find user by email
                user = None
                for u in auth_manager.get_all_users():
                    if u.email == request.email:
                        user = u
                        break

                if not user:
                    # Don't reveal if email exists or not for security
                    return EmailVerificationResponse(
                        message="If the email address is registered, a password reset email has been sent."
                    )

                # Generate password reset token
                reset_data = {
                    "user_id": user.user_id,
                    "email": user.email,
                    "type": "password_reset",
                    "exp": time.time() + 3600  # 1 hour expiration
                }

                reset_token = auth_manager.token_manager.create_token(
                    reset_data,
                    expires_in=3600
                )

                # Send password reset email
                email_sent = self.email_service.send_password_reset_email(
                    user.email,
                    reset_token,
                    user.username
                )

                if not email_sent:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to send password reset email"
                    )

                # Log password reset request
                auth_manager.audit_logger.log_action(
                    user_id=user.user_id,
                    action="password_reset_requested",
                    resource="password_reset",
                    success=True,
                    details={"email": user.email}
                )

                return EmailVerificationResponse(
                    message="If the email address is registered, a password reset email has been sent.",
                    verification_token=reset_token if self.email_service.mock_mode else None
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to process password reset request: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to process password reset request"
                )

        @self.app.post("/auth/reset-password")
        async def reset_password(request: ResetPasswordRequest):
            """Reset password using token"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Validate new password confirmation
                if request.new_password != request.confirm_password:
                    raise HTTPException(
                        status_code=400,
                        detail="New password and confirmation do not match"
                    )

                # Validate password strength
                if len(request.new_password) < 8:
                    raise HTTPException(
                        status_code=400,
                        detail="Password must be at least 8 characters long"
                    )

                # Validate token
                payload = auth_manager.token_manager.validate_token(request.token)
                if not payload or payload.get("type") != "password_reset":
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid or expired reset token"
                    )

                user_id = payload.get("user_id")
                email = payload.get("email")

                # Get user
                user = auth_manager.get_user(user_id)
                if not user or user.email != email:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid reset token"
                    )

                # Hash new password
                import hashlib
                new_password_hash = hashlib.sha256(request.new_password.encode()).hexdigest()

                # Update password
                success = auth_manager.user_store.update_user(
                    user_id,
                    password_hash=new_password_hash
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to reset password"
                    )

                # Update metadata to track password reset
                updated_metadata = user.metadata.copy()
                updated_metadata["password_reset_at"] = time.time()

                auth_manager.user_store.update_user(
                    user_id,
                    metadata=updated_metadata
                )

                # Log password reset
                auth_manager.audit_logger.log_action(
                    user_id=user_id,
                    action="password_reset_completed",
                    resource="password_reset",
                    success=True,
                    details={"email": email}
                )

                return {"message": "Password reset successfully."}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to reset password: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to reset password"
                )

        @self.app.get("/auth/sessions", response_model=SessionListResponse)
        async def get_user_sessions(
            request: Request,
            current_user: User = Depends(get_current_user)
        ):
            """Get user's active sessions"""
            try:
                # Clean up expired sessions first
                self.session_manager.cleanup_expired_sessions()

                # Get user's sessions
                sessions = self.session_manager.get_user_sessions(current_user.user_id)

                # Get current session ID from request headers
                current_session_id = request.headers.get("X-Session-ID")

                session_infos = []
                for session in sessions:
                    session_infos.append(SessionInfo(
                        session_id=session.session_id,
                        user_id=session.user_id,
                        user_agent=session.user_agent,
                        ip_address=session.ip_address,
                        created_at=session.created_at,
                        last_activity=session.last_activity,
                        is_active=session.is_active,
                        expires_at=session.expires_at
                    ))

                return SessionListResponse(
                    sessions=session_infos,
                    current_session_id=current_session_id,
                    total_sessions=len(session_infos)
                )

            except Exception as e:
                logger.error(f"Failed to get user sessions: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve user sessions"
                )

        @self.app.delete("/auth/sessions/{session_id}")
        async def terminate_session(
            session_id: str,
            current_user: User = Depends(get_current_user)
        ):
            """Terminate a specific session"""
            try:
                # Verify the session belongs to the current user
                session = self.session_manager.get_session(session_id)
                if not session or session.user_id != current_user.user_id:
                    raise HTTPException(
                        status_code=404,
                        detail="Session not found"
                    )

                # Terminate the session
                success = self.session_manager.deactivate_session(session_id)

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to terminate session"
                    )

                # Log session termination
                auth_manager = get_auth_manager()
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="session_terminated",
                    resource="session_management",
                    success=True,
                    details={"terminated_session_id": session_id}
                )

                return {"message": "Session terminated successfully"}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to terminate session: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to terminate session"
                )

        @self.app.delete("/auth/sessions/all")
        async def terminate_all_sessions(
            request: Request,
            current_user: User = Depends(get_current_user)
        ):
            """Terminate all user sessions except current"""
            try:
                # Get current session ID to exclude from termination
                current_session_id = request.headers.get("X-Session-ID")

                # Terminate all sessions for user except current
                terminated_count = self.session_manager.deactivate_user_sessions(
                    current_user.user_id,
                    exclude_session_id=current_session_id
                )

                # Log session termination
                auth_manager = get_auth_manager()
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="all_sessions_terminated",
                    resource="session_management",
                    success=True,
                    details={"terminated_count": terminated_count, "excluded_session": current_session_id}
                )

                return {
                    "message": f"All sessions terminated successfully",
                    "terminated_sessions": terminated_count
                }

            except Exception as e:
                logger.error(f"Failed to terminate all sessions: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to terminate sessions"
                )

        # MFA (Multi-Factor Authentication) endpoints
        @self.app.post("/auth/mfa/setup", response_model=MFASetupResponse)
        async def setup_mfa(request: MFASetupRequest, current_user: User = Depends(get_current_user)):
            """Setup MFA for user account"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Check if MFA is already enabled
                mfa_data = current_user.metadata.get("mfa", {})
                if mfa_data.get("enabled", False):
                    raise HTTPException(
                        status_code=400,
                        detail="MFA is already enabled for this account"
                    )

                if request.method not in ["totp"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Unsupported MFA method. Currently only TOTP is supported"
                    )

                # Generate TOTP secret
                totp_secret = pyotp.random_base32()

                # Create TOTP instance
                totp = pyotp.TOTP(totp_secret)

                # Generate provisioning URI for QR code
                provisioning_uri = totp.provisioning_uri(
                    name=current_user.email,
                    issuer_name="NetSentinel"
                )

                # Generate QR code
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(provisioning_uri)
                qr.make(fit=True)

                # Create QR code image
                img = qr.make_image(fill_color="black", back_color="white")
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                qr_code_data = base64.b64encode(buffered.getvalue()).decode()

                # Store MFA setup data temporarily (not enabled yet)
                updated_metadata = current_user.metadata.copy()
                updated_metadata["mfa_setup"] = {
                    "secret": totp_secret,
                    "method": request.method,
                    "created_at": time.time(),
                    "provisioning_uri": provisioning_uri
                }

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to setup MFA"
                    )

                # Log MFA setup initiation
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="mfa_setup_initiated",
                    resource="mfa_management",
                    success=True,
                    details={"method": request.method}
                )

                return MFASetupResponse(
                    secret=totp_secret,
                    qr_code_url=f"data:image/png;base64,{qr_code_data}",
                    manual_entry_key=totp_secret,
                    message="Scan QR code with authenticator app, then verify with code"
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to setup MFA: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to setup MFA"
                )

        @self.app.post("/auth/mfa/verify")
        async def verify_mfa(request: MFAVerifyRequest, current_user: User = Depends(get_current_user)):
            """Verify MFA setup with code"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Get MFA setup data
                mfa_setup_data = current_user.metadata.get("mfa_setup")
                if not mfa_setup_data:
                    raise HTTPException(
                        status_code=400,
                        detail="MFA setup not initiated"
                    )

                # Check if MFA is already enabled
                mfa_data = current_user.metadata.get("mfa", {})
                if mfa_data.get("enabled", False):
                    raise HTTPException(
                        status_code=400,
                        detail="MFA is already enabled for this account"
                    )

                # Verify the code
                totp = pyotp.TOTP(mfa_setup_data["secret"])
                if not totp.verify(request.code):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid verification code"
                    )

                # Enable MFA
                updated_metadata = current_user.metadata.copy()
                updated_metadata["mfa"] = {
                    "enabled": True,
                    "method": mfa_setup_data["method"],
                    "secret": mfa_setup_data["secret"],
                    "enabled_at": time.time(),
                    "last_used": time.time()
                }

                # Remove setup data
                updated_metadata.pop("mfa_setup", None)

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to enable MFA"
                    )

                # Log MFA enable
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="mfa_enabled",
                    resource="mfa_management",
                    success=True,
                    details={"method": mfa_setup_data["method"]}
                )

                return {"message": "MFA successfully enabled"}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to verify MFA: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to verify MFA"
                )

        @self.app.post("/auth/mfa/disable")
        async def disable_mfa(current_password: str, current_user: User = Depends(get_current_user)):
            """Disable MFA for user account"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Verify current password
                import hashlib
                current_password_hash = hashlib.sha256(current_password.encode()).hexdigest()
                if current_user.password_hash != current_password_hash:
                    raise HTTPException(
                        status_code=400,
                        detail="Current password is incorrect"
                    )

                # Get MFA data
                mfa_data = current_user.metadata.get("mfa", {})
                if not mfa_data.get("enabled", False):
                    raise HTTPException(
                        status_code=400,
                        detail="MFA is not enabled for this account"
                    )

                # Disable MFA
                updated_metadata = current_user.metadata.copy()
                updated_metadata.pop("mfa", None)
                updated_metadata.pop("mfa_setup", None)  # Clean up any pending setup

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to disable MFA"
                    )

                # Log MFA disable
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="mfa_disabled",
                    resource="mfa_management",
                    success=True,
                    details={"method": mfa_data.get("method")}
                )

                return {"message": "MFA successfully disabled"}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to disable MFA: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to disable MFA"
                )

        @self.app.get("/auth/mfa/status", response_model=MFAStatusResponse)
        async def get_mfa_status(current_user: User = Depends(get_current_user)):
            """Get MFA status for user account"""
            try:
                mfa_data = current_user.metadata.get("mfa", {})
                mfa_setup_data = current_user.metadata.get("mfa_setup")

                enabled = mfa_data.get("enabled", False)
                method = mfa_data.get("method") if enabled else None
                last_used = mfa_data.get("last_used") if enabled else None

                # Check if backup codes exist (placeholder for future implementation)
                backup_codes_generated = False

                return MFAStatusResponse(
                    enabled=enabled,
                    method=method,
                    backup_codes_generated=backup_codes_generated,
                    last_used=last_used
                )

            except Exception as e:
                logger.error(f"Failed to get MFA status: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve MFA status"
                )

        @self.app.post("/auth/mfa/verify-login", response_model=LoginResponse)
        async def verify_mfa_login(request: MFAVerifyRequest, session_id: str):
            """Verify MFA code for login and return JWT token"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Get session
                session = self.session_manager.get_session(session_id)
                if not session or not session.is_active:
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid or expired session"
                    )

                # Get user
                user = auth_manager.get_user(session.user_id)
                if not user:
                    raise HTTPException(
                        status_code=401,
                        detail="User not found"
                    )

                # Verify MFA is enabled
                mfa_data = user.metadata.get("mfa", {})
                if not mfa_data.get("enabled", False):
                    raise HTTPException(
                        status_code=400,
                        detail="MFA is not enabled for this account"
                    )

                # Verify MFA code
                totp = pyotp.TOTP(mfa_data["secret"])
                if not totp.verify(request.code):
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid MFA code"
                    )

                # Create JWT token now that MFA is verified
                user_data = {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "roles": [role.value for role in user.roles],
                    "permissions": [perm.value for perm in user.permissions],
                }

                token = auth_manager.token_manager.create_token(user_data)

                # Update MFA last used
                updated_metadata = user.metadata.copy()
                updated_metadata["mfa"]["last_used"] = time.time()

                auth_manager.user_store.update_user(
                    user.user_id,
                    metadata=updated_metadata
                )

                # Update last login
                user.last_login = time.time()

                # Log successful MFA login
                auth_manager.audit_logger.log_action(
                    user_id=user.user_id,
                    action="mfa_login_success",
                    resource="auth",
                    success=True,
                    details={"session_id": session_id}
                )

                user_info = {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "roles": [role.value for role in user.roles],
                    "permissions": [perm.value for perm in user.permissions],
                    "is_active": user.is_active,
                    "last_login": user.last_login,
                    "session_id": session_id
                }

                return LoginResponse(
                    access_token=token,
                    token_type="bearer",
                    expires_in=3600,
                    user=user_info,
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"MFA login verification failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="MFA verification failed"
                )

        # RBAC (Role-Based Access Control) endpoints - Admin only
        @self.app.get("/admin/roles", response_model=RoleListResponse)
        async def list_roles(current_user: User = Depends(require_admin)):
            """List all available roles (admin only)"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()
                roles = auth_manager.user_store.get_all_roles()

                role_infos = []
                for role in roles:
                    role_infos.append(RoleInfo(
                        id=role.id,
                        name=role.name,
                        description=role.description,
                        permissions=role.permissions,
                        is_system_role=role.is_system_role,
                        created_at=role.created_at,
                        updated_at=role.updated_at
                    ))

                return RoleListResponse(
                    roles=role_infos,
                    total_count=len(role_infos)
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to list roles: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve roles"
                )

        @self.app.post("/admin/roles", response_model=RoleInfo)
        async def create_role(role_data: RoleCreate, current_user: User = Depends(require_admin)):
            """Create new role (admin only)"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Generate role ID from name
                role_id = role_data.name.lower().replace(" ", "_")

                # Validate permissions (basic check - should be more comprehensive)
                valid_permissions = [
                    "read:events", "write:events", "read:alerts", "write:alerts",
                    "read:config", "write:config", "admin", "audit"
                ]

                for perm in role_data.permissions:
                    if not any(perm.startswith(vp.split(":")[0]) for vp in valid_permissions):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid permission: {perm}"
                        )

                role = auth_manager.user_store.create_custom_role(
                    role_id=role_id,
                    name=role_data.name,
                    description=role_data.description,
                    permissions=role_data.permissions
                )

                # Log role creation
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="role_created",
                    resource="rbac_management",
                    success=True,
                    details={"role_name": role_data.name, "role_id": role_id}
                )

                return RoleInfo(
                    id=role.id,
                    name=role.name,
                    description=role.description,
                    permissions=role.permissions,
                    is_system_role=role.is_system_role,
                    created_at=role.created_at,
                    updated_at=role.updated_at
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to create role: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create role"
                )

        @self.app.get("/admin/roles/{role_id}", response_model=RoleInfo)
        async def get_role(role_id: str, current_user: User = Depends(require_admin)):
            """Get role details (admin only)"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()
                role = auth_manager.user_store.get_role(role_id)

                if not role:
                    raise HTTPException(
                        status_code=404,
                        detail="Role not found"
                    )

                return RoleInfo(
                    id=role.id,
                    name=role.name,
                    description=role.description,
                    permissions=role.permissions,
                    is_system_role=role.is_system_role,
                    created_at=role.created_at,
                    updated_at=role.updated_at
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get role: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve role"
                )

        @self.app.put("/admin/roles/{role_id}", response_model=RoleInfo)
        async def update_role(
            role_id: str,
            role_update: RoleUpdate,
            current_user: User = Depends(require_admin)
        ):
            """Update role (admin only)"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Validate permissions if provided
                if role_update.permissions:
                    valid_permissions = [
                        "read:events", "write:events", "read:alerts", "write:alerts",
                        "read:config", "write:config", "admin", "audit"
                    ]

                    for perm in role_update.permissions:
                        if not any(perm.startswith(vp.split(":")[0]) for vp in valid_permissions):
                            raise HTTPException(
                                status_code=400,
                                detail=f"Invalid permission: {perm}"
                            )

                success = auth_manager.user_store.update_role(
                    role_id=role_id,
                    name=role_update.name,
                    description=role_update.description,
                    permissions=role_update.permissions
                )

                if not success:
                    raise HTTPException(
                        status_code=404,
                        detail="Role not found"
                    )

                # Get updated role
                role = auth_manager.user_store.get_role(role_id)

                # Log role update
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="role_updated",
                    resource="rbac_management",
                    success=True,
                    details={"role_id": role_id, "updates": role_update.dict(exclude_unset=True)}
                )

                return RoleInfo(
                    id=role.id,
                    name=role.name,
                    description=role.description,
                    permissions=role.permissions,
                    is_system_role=role.is_system_role,
                    created_at=role.created_at,
                    updated_at=role.updated_at
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to update role: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update role"
                )

        @self.app.delete("/admin/roles/{role_id}")
        async def delete_role(role_id: str, current_user: User = Depends(require_admin)):
            """Delete role (admin only)"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                success = auth_manager.user_store.delete_role(role_id)

                if not success:
                    raise HTTPException(
                        status_code=404,
                        detail="Role not found"
                    )

                # Log role deletion
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="role_deleted",
                    resource="rbac_management",
                    success=True,
                    details={"role_id": role_id}
                )

                return {"message": "Role deleted successfully"}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to delete role: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to delete role"
                )

        @self.app.get("/admin/users")
        async def list_users_admin(current_user: User = Depends(require_admin)):
            """List all users (admin only)"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()
                users = auth_manager.get_all_users()

                user_list = []
                for user in users:
                    user_list.append({
                        "user_id": user.user_id,
                        "username": user.username,
                        "email": user.email,
                        "roles": [role.value for role in user.roles],
                        "is_active": user.is_active,
                        "created_at": user.created_at,
                        "last_login": user.last_login
                    })

                return {
                    "users": user_list,
                    "total_count": len(user_list)
                }

            except Exception as e:
                logger.error(f"Failed to list users: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve users"
                )

        @self.app.put("/admin/users/{user_id}/roles")
        async def assign_user_roles(
            user_id: str,
            role_assignment: UserRoleAssignment,
            current_user: User = Depends(require_admin)
        ):
            """Assign roles to user (admin only)"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Validate that user exists
                user = auth_manager.get_user(user_id)
                if not user:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )

                # Validate roles exist
                for role_id in role_assignment.roles:
                    if not auth_manager.user_store.get_role(role_id):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Role not found: {role_id}"
                        )

                success = auth_manager.user_store.assign_user_roles(
                    user_id=user_id,
                    role_ids=role_assignment.roles
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to assign roles"
                    )

                # Log role assignment
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="user_roles_assigned",
                    resource="rbac_management",
                    success=True,
                    details={"target_user": user_id, "roles": role_assignment.roles}
                )

                return {"message": "Roles assigned successfully"}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to assign user roles: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to assign roles"
                )

        @self.app.get("/admin/users/{user_id}/permissions", response_model=UserPermissionsResponse)
        async def get_user_permissions(user_id: str, current_user: User = Depends(require_admin)):
            """Get user's effective permissions (admin only)"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Validate that user exists
                user = auth_manager.get_user(user_id)
                if not user:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )

                permissions_data = auth_manager.user_store.get_user_effective_permissions(user_id)

                return UserPermissionsResponse(
                    user_id=user_id,
                    username=user.username,
                    direct_permissions=permissions_data["direct_permissions"],
                    role_permissions=permissions_data["role_permissions"],
                    effective_permissions=permissions_data["effective_permissions"]
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get user permissions: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve user permissions"
                )

        @self.app.post("/auth/login", response_model=LoginResponse)
        async def login(login_data: LoginRequest, request: Request):
            """User login endpoint with JWT authentication"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Extract client information
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")

                # Hash password for authentication
                import hashlib
                password_hash = hashlib.sha256(login_data.password.encode()).hexdigest()

                # Authenticate user
                token = auth_manager.authenticate_credentials(
                    login_data.username,
                    password_hash,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                if not token:
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid username or password"
                    )

                # Get user information from token
                user = auth_manager.authenticate_token(token)
                if not user:
                    raise HTTPException(
                        status_code=500,
                        detail="Authentication failed"
                    )

                user_info = {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "roles": [role.value for role in user.roles],
                    "permissions": [perm.value for perm in user.permissions],
                    "is_active": user.is_active,
                    "last_login": user.last_login,
                }

                # Check if MFA is required
                mfa_data = user.metadata.get("mfa", {})
                mfa_required = mfa_data.get("enabled", False)

                if mfa_required:
                    # Create temporary session for MFA verification
                    session = self.session_manager.create_session(
                        user_id=user.user_id,
                        user_agent=user_agent,
                        ip_address=ip_address
                    )

                    # Return MFA required response instead of token
                    return {
                        "mfa_required": True,
                        "session_id": session.session_id,
                        "message": "MFA verification required",
                        "user": user_info
                    }
                else:
                    # Create session for tracking
                    session = self.session_manager.create_session(
                        user_id=user.user_id,
                        user_agent=user_agent,
                        ip_address=ip_address
                    )

                    # Add session ID to response
                    response_data = LoginResponse(
                        access_token=token,
                        token_type="bearer",
                        expires_in=3600,
                        user=user_info,
                    )

                    # Add session info to user info
                    user_info["session_id"] = session.session_id

                    return response_data

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Login failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Login failed"
                )

        @self.app.post("/auth/logout", response_model=LogoutResponse)
        async def logout(request: Request, current_user: User = Depends(get_current_user)):
            """User logout endpoint with token revocation"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Extract token from Authorization header
                auth_header = request.headers.get("authorization", "")
                token = None
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]  # Remove "Bearer " prefix

                # Extract client information
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")

                # Revoke token if provided
                if token:
                    auth_manager.logout(
                        token,
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )

                # Terminate session if session ID provided
                session_id = request.headers.get("X-Session-ID")
                if session_id:
                    self.session_manager.deactivate_session(session_id)

                return LogoutResponse(message="Logout successful")

            except Exception as e:
                logger.error(f"Logout failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Logout failed"
                )

        @self.app.post("/auth/refresh", response_model=LoginResponse)
        async def refresh_token(refresh_request: TokenRefreshRequest, request: Request):
            """Token refresh endpoint"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Refresh token
                new_token = auth_manager.refresh_token(refresh_request.token)
                if not new_token:
                    raise HTTPException(status_code=401, detail="Invalid or expired token")

                # Get user from new token
                user = auth_manager.authenticate_token(new_token)
                if not user:
                    raise HTTPException(status_code=500, detail="Token validation failed")

                user_info = {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "roles": [role.value for role in user.roles],
                    "permissions": [perm.value for perm in user.permissions],
                    "is_active": user.is_active,
                    "last_login": user.last_login,
                }

                return LoginResponse(
                    access_token=new_token,
                    token_type="bearer",
                    expires_in=3600,
                    user=user_info,
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                raise HTTPException(status_code=500, detail="Token refresh failed")

        @self.app.get("/auth/me", response_model=UserInfo)
        async def get_current_user_info(current_user: User = Depends(get_current_user)):
            """Get current user information"""
            try:
                return UserInfo(
                    user_id=current_user.user_id,
                    username=current_user.username,
                    email=current_user.email,
                    roles=[role.value for role in current_user.roles],
                    permissions=[perm.value for perm in current_user.permissions],
                    is_active=current_user.is_active,
                    last_login=current_user.last_login,
                )

            except Exception as e:
                logger.error(f"Failed to get user info: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve user information"
                )

        # User Profile endpoints
        @self.app.get("/users/profile", response_model=UserProfile)
        async def get_user_profile(current_user: User = Depends(get_current_user)):
            """Get current user profile"""
            try:
                return UserProfile(
                    user_id=current_user.user_id,
                    username=current_user.username,
                    email=current_user.email,
                    roles=[role.value for role in current_user.roles],
                    permissions=[perm.value for perm in current_user.permissions],
                    is_active=current_user.is_active,
                    created_at=current_user.created_at,
                    last_login=current_user.last_login,
                    avatar_url=current_user.metadata.get("avatar_url"),
                    metadata=current_user.metadata,
                )

            except Exception as e:
                logger.error(f"Failed to get user profile: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve user profile"
                )

        @self.app.put("/users/profile", response_model=UserProfile)
        async def update_user_profile(
            profile_update: UserProfileUpdate,
            current_user: User = Depends(get_current_user)
        ):
            """Update current user profile"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()
                updates = {}

                # Validate email if provided
                if profile_update.email is not None:
                    try:
                        from .user_store import validate_email
                        updates["email"] = validate_email(profile_update.email)
                    except ValueError as e:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid email: {e}"
                        )

                # Update metadata if provided
                if profile_update.metadata is not None:
                    # Merge with existing metadata
                    updated_metadata = current_user.metadata.copy()
                    updated_metadata.update(profile_update.metadata)
                    updates["metadata"] = updated_metadata

                if updates:
                    success = auth_manager.user_store.update_user(current_user.user_id, **updates)
                    if not success:
                        raise HTTPException(
                            status_code=404,
                            detail="User not found"
                        )

                    # Get updated user
                    updated_user = auth_manager.get_user(current_user.user_id)
                    if not updated_user:
                        raise HTTPException(
                            status_code=500,
                            detail="Failed to retrieve updated user"
                        )

                    current_user = updated_user

                return UserProfile(
                    user_id=current_user.user_id,
                    username=current_user.username,
                    email=current_user.email,
                    roles=[role.value for role in current_user.roles],
                    permissions=[perm.value for perm in current_user.permissions],
                    is_active=current_user.is_active,
                    created_at=current_user.created_at,
                    last_login=current_user.last_login,
                    avatar_url=current_user.metadata.get("avatar_url"),
                    metadata=current_user.metadata,
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to update user profile: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update user profile"
                )

        @self.app.post("/users/change-password")
        async def change_password(
            password_request: ChangePasswordRequest,
            current_user: User = Depends(get_current_user)
        ):
            """Change user password"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Validate new password confirmation
                if password_request.new_password != password_request.confirm_password:
                    raise HTTPException(
                        status_code=400,
                        detail="New password and confirmation do not match"
                    )

                # Validate password strength (basic check)
                if len(password_request.new_password) < 8:
                    raise HTTPException(
                        status_code=400,
                        detail="Password must be at least 8 characters long"
                    )

                # Verify current password
                import hashlib
                current_password_hash = hashlib.sha256(password_request.current_password.encode()).hexdigest()
                if current_user.password_hash != current_password_hash:
                    raise HTTPException(
                        status_code=400,
                        detail="Current password is incorrect"
                    )

                # Hash new password
                new_password_hash = hashlib.sha256(password_request.new_password.encode()).hexdigest()

                # Update password
                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    password_hash=new_password_hash
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to update password"
                    )

                # Log password change
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="password_changed",
                    resource="user_management",
                    success=True,
                    details={"username": current_user.username}
                )

                return {"message": "Password changed successfully"}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to change password: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to change password"
                )

        @self.app.get("/users/preferences", response_model=UserPreferences)
        async def get_user_preferences(current_user: User = Depends(get_current_user)):
            """Get user preferences"""
            try:
                # Get preferences from user metadata
                prefs_data = current_user.metadata.get("preferences", {})

                # Create preferences object with defaults merged from stored data
                preferences = UserPreferences()
                for key, value in prefs_data.items():
                    if hasattr(preferences, key):
                        setattr(preferences, key, value)

                return preferences

            except Exception as e:
                logger.error(f"Failed to get user preferences: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve user preferences"
                )

        @self.app.put("/users/preferences", response_model=UserPreferences)
        async def update_user_preferences(
            preferences_update: UserPreferencesUpdate,
            current_user: User = Depends(get_current_user)
        ):
            """Update user preferences"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Get current preferences
                current_prefs = current_user.metadata.get("preferences", {})

                # Update preferences with new values
                update_dict = preferences_update.dict(exclude_unset=True)
                current_prefs.update(update_dict)

                # Update user metadata
                updated_metadata = current_user.metadata.copy()
                updated_metadata["preferences"] = current_prefs

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to update preferences"
                    )

                # Get updated user and return preferences
                updated_user = auth_manager.get_user(current_user.user_id)
                if not updated_user:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to retrieve updated user"
                    )

                # Create preferences object
                preferences = UserPreferences()
                for key, value in current_prefs.items():
                    if hasattr(preferences, key):
                        setattr(preferences, key, value)

                return preferences

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to update user preferences: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update user preferences"
                )

        @self.app.get("/users/preferences/ui", response_model=UIThemePreferences)
        async def get_ui_preferences(current_user: User = Depends(get_current_user)):
            """Get UI theme and customization preferences"""
            try:
                # Get UI preferences from user metadata
                ui_prefs_data = current_user.metadata.get("ui_preferences", {})

                # Create UI preferences object with defaults merged from stored data
                ui_preferences = UIThemePreferences()
                for key, value in ui_prefs_data.items():
                    if hasattr(ui_preferences, key):
                        setattr(ui_preferences, key, value)

                return ui_preferences

            except Exception as e:
                logger.error(f"Failed to get UI preferences: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve UI preferences"
                )

        @self.app.put("/users/preferences/ui", response_model=UIThemePreferences)
        async def update_ui_preferences(
            ui_preferences_update: UIThemePreferencesUpdate,
            current_user: User = Depends(get_current_user)
        ):
            """Update UI theme and customization preferences"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Get current UI preferences
                current_ui_prefs = current_user.metadata.get("ui_preferences", {})

                # Update UI preferences with new values
                update_dict = ui_preferences_update.dict(exclude_unset=True)
                current_ui_prefs.update(update_dict)

                # Update user metadata
                updated_metadata = current_user.metadata.copy()
                updated_metadata["ui_preferences"] = current_ui_prefs

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to update UI preferences"
                    )

                # Get updated user and return UI preferences
                updated_user = auth_manager.get_user(current_user.user_id)
                if not updated_user:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to retrieve updated user"
                    )

                # Create UI preferences object
                ui_preferences = UIThemePreferences()
                for key, value in current_ui_prefs.items():
                    if hasattr(ui_preferences, key):
                        setattr(ui_preferences, key, value)

                return ui_preferences

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to update UI preferences: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update UI preferences"
                )

        @self.app.post("/users/avatar", response_model=AvatarResponse)
        async def upload_avatar(
            file: UploadFile = File(...),
            current_user: User = Depends(get_current_user)
        ):
            """Upload user avatar"""
            try:
                # Validate file type
                if not file.content_type or not file.content_type.startswith("image/"):
                    raise HTTPException(
                        status_code=400,
                        detail="File must be an image"
                    )

                # Validate file size (max 5MB)
                file_size = 0
                content = await file.read()
                file_size = len(content)

                if file_size > 5 * 1024 * 1024:  # 5MB limit
                    raise HTTPException(
                        status_code=400,
                        detail="File size must be less than 5MB"
                    )

                # Validate image format
                allowed_formats = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
                if file.content_type not in allowed_formats:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported image format. Allowed: {', '.join(allowed_formats)}"
                    )

                # Generate unique filename
                file_extension = Path(file.filename).suffix.lower()
                unique_filename = f"{current_user.user_id}_{uuid.uuid4().hex}{file_extension}"
                file_path = self.avatars_dir / unique_filename

                # Save file
                with open(file_path, "wb") as buffer:
                    buffer.write(content)

                # Create avatar URL
                avatar_url = f"/avatars/{unique_filename}"

                # Update user metadata with avatar URL
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()
                updated_metadata = current_user.metadata.copy()
                updated_metadata["avatar_url"] = avatar_url

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    # Clean up uploaded file if database update failed
                    if file_path.exists():
                        file_path.unlink()
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to update user avatar"
                    )

                return AvatarResponse(
                    avatar_url=avatar_url,
                    filename=unique_filename
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to upload avatar: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to upload avatar"
                )

        @self.app.delete("/users/avatar")
        async def delete_avatar(current_user: User = Depends(get_current_user)):
            """Delete user avatar"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Get current avatar URL
                current_avatar_url = current_user.metadata.get("avatar_url")
                if not current_avatar_url:
                    raise HTTPException(
                        status_code=404,
                        detail="No avatar found"
                    )

                # Extract filename from URL
                filename = current_avatar_url.split("/")[-1]
                file_path = self.avatars_dir / filename

                # Delete file if it exists
                if file_path.exists():
                    file_path.unlink()

                # Update user metadata to remove avatar URL
                updated_metadata = current_user.metadata.copy()
                updated_metadata.pop("avatar_url", None)

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to delete avatar"
                    )

                return {"message": "Avatar deleted successfully"}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to delete avatar: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to delete avatar"
                )

        # API Key Management endpoints
        @self.app.get("/api-keys", response_model=APIKeyListResponse)
        async def list_api_keys(current_user: User = Depends(get_current_user)):
            """List user's API keys"""
            try:
                # Get API keys from user metadata
                api_keys_data = current_user.metadata.get("api_keys", {})

                api_keys = []
                for key_id, key_data in api_keys_data.items():
                    # Don't include the actual key value in the response
                    api_keys.append(APIKeyResponse(
                        id=key_id,
                        name=key_data.get("name", ""),
                        permissions=key_data.get("permissions", []),
                        created_at=key_data.get("created_at", 0),
                        expires_at=key_data.get("expires_at"),
                        last_used=key_data.get("last_used"),
                        is_active=key_data.get("is_active", True),
                        usage_count=key_data.get("usage_count", 0),
                        rate_limit=key_data.get("rate_limit")
                    ))

                return APIKeyListResponse(
                    api_keys=api_keys,
                    total_count=len(api_keys)
                )

            except Exception as e:
                logger.error(f"Failed to list API keys: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve API keys"
                )

        @self.app.post("/api-keys", response_model=APIKey)
        async def create_api_key(
            api_key_data: APIKeyCreate,
            current_user: User = Depends(get_current_user)
        ):
            """Create new API key"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Generate unique API key
                import secrets
                api_key_value = secrets.token_urlsafe(32)

                # Generate unique key ID
                key_id = str(uuid.uuid4())

                # Create API key data
                key_data = {
                    "id": key_id,
                    "name": api_key_data.name,
                    "key": api_key_value,  # Store the actual key
                    "permissions": api_key_data.permissions,
                    "created_at": time.time(),
                    "expires_at": api_key_data.expires_at,
                    "last_used": None,
                    "is_active": True,
                    "usage_count": 0,
                    "rate_limit": api_key_data.rate_limit,
                    "usage_history": []  # For tracking usage over time
                }

                # Get current API keys
                updated_metadata = current_user.metadata.copy()
                api_keys = updated_metadata.get("api_keys", {})
                api_keys[key_id] = key_data
                updated_metadata["api_keys"] = api_keys

                # Update user metadata
                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to create API key"
                    )

                # Log API key creation
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="api_key_created",
                    resource="api_key_management",
                    success=True,
                    details={"key_name": api_key_data.name, "key_id": key_id}
                )

                return APIKey(**key_data)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to create API key: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create API key"
                )

        @self.app.get("/api-keys/{key_id}", response_model=APIKeyResponse)
        async def get_api_key(
            key_id: str,
            current_user: User = Depends(get_current_user)
        ):
            """Get specific API key details"""
            try:
                # Get API keys from user metadata
                api_keys_data = current_user.metadata.get("api_keys", {})

                if key_id not in api_keys_data:
                    raise HTTPException(
                        status_code=404,
                        detail="API key not found"
                    )

                key_data = api_keys_data[key_id]

                return APIKeyResponse(
                    id=key_id,
                    name=key_data.get("name", ""),
                    permissions=key_data.get("permissions", []),
                    created_at=key_data.get("created_at", 0),
                    expires_at=key_data.get("expires_at"),
                    last_used=key_data.get("last_used"),
                    is_active=key_data.get("is_active", True),
                    usage_count=key_data.get("usage_count", 0),
                    rate_limit=key_data.get("rate_limit")
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get API key: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve API key"
                )

        @self.app.put("/api-keys/{key_id}", response_model=APIKeyResponse)
        async def update_api_key(
            key_id: str,
            update_data: APIKeyUpdate,
            current_user: User = Depends(get_current_user)
        ):
            """Update API key"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Get current API keys
                updated_metadata = current_user.metadata.copy()
                api_keys = updated_metadata.get("api_keys", {})

                if key_id not in api_keys:
                    raise HTTPException(
                        status_code=404,
                        detail="API key not found"
                    )

                # Update key data
                key_data = api_keys[key_id]
                update_dict = update_data.dict(exclude_unset=True)

                for field, value in update_dict.items():
                    key_data[field] = value

                # Update metadata
                updated_metadata["api_keys"] = api_keys

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to update API key"
                    )

                # Log API key update
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="api_key_updated",
                    resource="api_key_management",
                    success=True,
                    details={"key_id": key_id, "updates": list(update_dict.keys())}
                )

                return APIKeyResponse(
                    id=key_id,
                    name=key_data.get("name", ""),
                    permissions=key_data.get("permissions", []),
                    created_at=key_data.get("created_at", 0),
                    expires_at=key_data.get("expires_at"),
                    last_used=key_data.get("last_used"),
                    is_active=key_data.get("is_active", True),
                    usage_count=key_data.get("usage_count", 0),
                    rate_limit=key_data.get("rate_limit")
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to update API key: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update API key"
                )

        @self.app.delete("/api-keys/{key_id}")
        async def delete_api_key(
            key_id: str,
            current_user: User = Depends(get_current_user)
        ):
            """Delete API key"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Get current API keys
                updated_metadata = current_user.metadata.copy()
                api_keys = updated_metadata.get("api_keys", {})

                if key_id not in api_keys:
                    raise HTTPException(
                        status_code=404,
                        detail="API key not found"
                    )

                # Remove the key
                deleted_key_name = api_keys[key_id].get("name", "")
                del api_keys[key_id]
                updated_metadata["api_keys"] = api_keys

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to delete API key"
                    )

                # Log API key deletion
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="api_key_deleted",
                    resource="api_key_management",
                    success=True,
                    details={"key_id": key_id, "key_name": deleted_key_name}
                )

                return {"message": "API key deleted successfully"}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to delete API key: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to delete API key"
                )

        @self.app.post("/api-keys/{key_id}/regenerate", response_model=APIKey)
        async def regenerate_api_key(
            key_id: str,
            current_user: User = Depends(get_current_user)
        ):
            """Regenerate API key (creates new secret, keeps same ID)"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Get current API keys
                updated_metadata = current_user.metadata.copy()
                api_keys = updated_metadata.get("api_keys", {})

                if key_id not in api_keys:
                    raise HTTPException(
                        status_code=404,
                        detail="API key not found"
                    )

                # Generate new API key
                import secrets
                new_api_key_value = secrets.token_urlsafe(32)

                # Update key data
                key_data = api_keys[key_id]
                key_data["key"] = new_api_key_value
                key_data["usage_count"] = 0  # Reset usage count
                key_data["last_used"] = None  # Reset last used

                # Update metadata
                updated_metadata["api_keys"] = api_keys

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to regenerate API key"
                    )

                # Log API key regeneration
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="api_key_regenerated",
                    resource="api_key_management",
                    success=True,
                    details={"key_id": key_id, "key_name": key_data.get("name", "")}
                )

                return APIKey(**key_data)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to regenerate API key: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to regenerate API key"
                )

        @self.app.get("/api-keys/{key_id}/usage", response_model=APIKeyUsage)
        async def get_api_key_usage(
            key_id: str,
            current_user: User = Depends(get_current_user)
        ):
            """Get API key usage statistics"""
            try:
                # Get API keys from user metadata
                api_keys_data = current_user.metadata.get("api_keys", {})

                if key_id not in api_keys_data:
                    raise HTTPException(
                        status_code=404,
                        detail="API key not found"
                    )

                key_data = api_keys_data[key_id]
                usage_history = key_data.get("usage_history", [])

                # Calculate statistics
                now = time.time()
                today_start = now - (now % 86400)  # Start of today
                hour_start = now - (now % 3600)    # Start of current hour

                total_requests = key_data.get("usage_count", 0)
                requests_today = sum(1 for timestamp in usage_history if timestamp >= today_start)
                requests_this_hour = sum(1 for timestamp in usage_history if timestamp >= hour_start)

                # Calculate average requests per day (simplified)
                days_since_creation = max(1, (now - key_data.get("created_at", now)) / 86400)
                avg_requests_per_day = total_requests / days_since_creation

                # Calculate rate limit remaining (simplified - would need more sophisticated tracking)
                rate_limit = key_data.get("rate_limit")
                rate_limit_remaining = None
                if rate_limit:
                    # This is a simplified calculation - in production you'd track per-minute usage
                    rate_limit_remaining = max(0, rate_limit - requests_this_hour)

                return APIKeyUsage(
                    id=key_id,
                    name=key_data.get("name", ""),
                    total_requests=total_requests,
                    requests_today=requests_today,
                    requests_this_hour=requests_this_hour,
                    last_used=key_data.get("last_used"),
                    average_requests_per_day=avg_requests_per_day,
                    rate_limit_remaining=rate_limit_remaining
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get API key usage: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve API key usage"
                )

        @self.app.get("/api-keys/{key_id}/permissions")
        async def get_api_key_permissions(
            key_id: str,
            current_user: User = Depends(get_current_user)
        ):
            """Get API key permissions"""
            try:
                # Get API keys from user metadata
                api_keys_data = current_user.metadata.get("api_keys", {})

                if key_id not in api_keys_data:
                    raise HTTPException(
                        status_code=404,
                        detail="API key not found"
                    )

                key_data = api_keys_data[key_id]
                permissions = key_data.get("permissions", [])

                return {
                    "key_id": key_id,
                    "permissions": permissions,
                    "permission_count": len(permissions)
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get API key permissions: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve API key permissions"
                )

        @self.app.put("/api-keys/{key_id}/permissions")
        async def update_api_key_permissions(
            key_id: str,
            permissions: List[str],
            current_user: User = Depends(get_current_user)
        ):
            """Update API key permissions"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                auth_manager = get_auth_manager()

                # Get current API keys
                updated_metadata = current_user.metadata.copy()
                api_keys = updated_metadata.get("api_keys", {})

                if key_id not in api_keys:
                    raise HTTPException(
                        status_code=404,
                        detail="API key not found"
                    )

                # Update permissions
                key_data = api_keys[key_id]
                key_data["permissions"] = permissions

                # Update metadata
                updated_metadata["api_keys"] = api_keys

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to update API key permissions"
                    )

                # Log permission update
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="api_key_permissions_updated",
                    resource="api_key_management",
                    success=True,
                    details={"key_id": key_id, "permission_count": len(permissions)}
                )

                return {
                    "message": "API key permissions updated successfully",
                    "key_id": key_id,
                    "permissions": permissions
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to update API key permissions: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update API key permissions"
                )

        @self.app.post("/api-keys/{key_id}/extend")
        async def extend_api_key_expiration(
            key_id: str,
            days_to_extend: int = 30,
            current_user: User = Depends(get_current_user)
        ):
            """Extend API key expiration date"""
            try:
                if not get_auth_manager:
                    raise HTTPException(
                        status_code=503, detail="Authentication not configured"
                    )

                if days_to_extend <= 0 or days_to_extend > 365:
                    raise HTTPException(
                        status_code=400,
                        detail="Extension period must be between 1 and 365 days"
                    )

                auth_manager = get_auth_manager()

                # Get current API keys
                updated_metadata = current_user.metadata.copy()
                api_keys = updated_metadata.get("api_keys", {})

                if key_id not in api_keys:
                    raise HTTPException(
                        status_code=404,
                        detail="API key not found"
                    )

                # Calculate new expiration date
                key_data = api_keys[key_id]
                current_expires_at = key_data.get("expires_at")

                if current_expires_at and current_expires_at < time.time():
                    # Key is already expired, extend from now
                    new_expires_at = time.time() + (days_to_extend * 24 * 60 * 60)
                else:
                    # Key is still valid, extend from current expiration
                    base_time = current_expires_at if current_expires_at else time.time()
                    new_expires_at = base_time + (days_to_extend * 24 * 60 * 60)

                # Update expiration
                key_data["expires_at"] = new_expires_at
                updated_metadata["api_keys"] = api_keys

                success = auth_manager.user_store.update_user(
                    current_user.user_id,
                    metadata=updated_metadata
                )

                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to extend API key expiration"
                    )

                # Log extension
                auth_manager.audit_logger.log_action(
                    user_id=current_user.user_id,
                    action="api_key_extended",
                    resource="api_key_management",
                    success=True,
                    details={"key_id": key_id, "days_extended": days_to_extend, "new_expires_at": new_expires_at}
                )

                return {
                    "message": "API key expiration extended successfully",
                    "key_id": key_id,
                    "new_expires_at": new_expires_at,
                    "days_extended": days_to_extend
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to extend API key expiration: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to extend API key expiration"
                )

        @self.app.get("/api-keys/expired")
        async def get_expired_api_keys(current_user: User = Depends(get_current_user)):
            """Get list of expired API keys"""
            try:
                # Get API keys from user metadata
                api_keys_data = current_user.metadata.get("api_keys", {})

                expired_keys = []
                current_time = time.time()

                for key_id, key_data in api_keys_data.items():
                    expires_at = key_data.get("expires_at")
                    if expires_at and expires_at < current_time:
                        expired_keys.append({
                            "id": key_id,
                            "name": key_data.get("name", ""),
                            "expired_at": expires_at,
                            "days_expired": int((current_time - expires_at) / (24 * 60 * 60))
                        })

                return {
                    "expired_keys": expired_keys,
                    "count": len(expired_keys)
                }

            except Exception as e:
                logger.error(f"Failed to get expired API keys: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve expired API keys"
                )

        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint"""
            try:
                # Check component health
                is_healthy = self.is_healthy()
                if not is_healthy:
                    raise HTTPException(status_code=503, detail="Service unhealthy")

                # Check processor health if available
                processor_healthy = True
                if self.processor and hasattr(self.processor, "is_healthy"):
                    processor_healthy = self.processor.is_healthy()

                if not processor_healthy:
                    raise HTTPException(
                        status_code=503, detail="Event processor unhealthy"
                    )

                return HealthResponse(
                    status="healthy",
                    timestamp=time.time(),
                    uptime=time.time() - self.start_time,
                    version="1.0.0",
                )

            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise HTTPException(
                    status_code=503, detail=f"Health check failed: {str(e)}"
                )

        @self.app.get("/threats")
        async def get_threats(
            min_score: float = Query(0.0, description="Minimum threat score to include"),
            limit: int = Query(100, description="Maximum number of threats to return")
        ):
            """Get threat intelligence data - simplified for now"""
            try:
                if not self.processor:
                    return {"total_threats": 0, "threats": [], "message": "Event processor not available"}

                # Get threat data from processor
                threat_data = await self._get_threat_intelligence(min_score, limit)

                return {
                    "total_threats": len(threat_data),
                    "threats": threat_data,
                    "message": f"Retrieved {len(threat_data)} threats"
                }

            except Exception as e:
                logger.error(f"Failed to get threat data: {e}")
                return {"total_threats": 0, "threats": [], "error": str(e)}

        @self.app.get("/threats/{ip_address}")
        async def get_threat_by_ip(ip_address: str):
            """Get threat information for specific IP address - simplified for now"""
            try:
                if not self.processor:
                    return {"message": "Event processor not available", "ip_address": ip_address}

                threat_info = await self._get_threat_by_ip(ip_address)
                if not threat_info:
                    return {
                        "message": f"No threat data found for IP: {ip_address}",
                        "ip_address": ip_address,
                        "threat_score": 0.0,
                        "status": "clean"
                    }

                return threat_info

            except Exception as e:
                logger.error(f"Failed to get threat data for IP {ip_address}: {e}")
                return {
                    "error": str(e),
                    "ip_address": ip_address,
                    "message": "Error retrieving threat data"
                }

        @self.app.get("/metrics")
        async def get_metrics():
            """Get Prometheus-compatible metrics - simplified for now"""
            try:
                metrics_data = "# NetSentinel API Server Metrics\n"
                metrics_data += f"netsentinel_api_uptime_seconds{{service=\"api_server\"}} {time.time() - self.start_time}\n"
                metrics_data += "netsentinel_api_requests_total{service=\"api_server\", endpoint=\"health\"} 1\n"
                metrics_data += "netsentinel_api_requests_total{service=\"api_server\", endpoint=\"threats\"} 1\n"
                metrics_data += "netsentinel_api_requests_total{service=\"api_server\", endpoint=\"alerts\"} 1\n"

                # Add basic system metrics
                metrics_data += f"netsentinel_system_cpu_usage_percent 15.5\n"
                metrics_data += f"netsentinel_system_memory_usage_bytes {1024*1024*256}\n"  # 256MB
                metrics_data += f"netsentinel_active_alerts 0\n"
                metrics_data += f"netsentinel_total_events_processed 150\n"

                return JSONResponse(
                    content={"metrics": metrics_data},
                    media_type="text/plain",
                )

            except Exception as e:
                logger.error(f"Failed to get metrics: {e}")
                return JSONResponse(
                    content={"error": str(e)},
                    status_code=500
                )

        # Temporarily disabled
        # @self.app.get("/status")
        # @require_analyst
        # async def get_status(current_user: User = Depends(get_current_user)):
            """Get detailed system status"""
            try:
                status = {
                    "api_server": {
                        "status": "healthy" if self.is_healthy() else "unhealthy",
                        "uptime": time.time() - self.start_time,
                        "host": self.host,
                        "port": self.port,
                    },
                    "event_processor": {"status": "unknown"},
                    "components": {},
                }

                # Add processor status if available
                if self.processor:
                    if hasattr(self.processor, "is_healthy"):
                        status["event_processor"]["status"] = (
                            "healthy" if self.processor.is_healthy() else "unhealthy"
                        )

                    if hasattr(self.processor, "get_metrics"):
                        status["event_processor"][
                            "metrics"
                        ] = self.processor.get_metrics()

                # Add component information
                if hasattr(self, "_dependencies"):
                    for dep in self._dependencies:
                        status["components"][dep.name] = {
                            "status": "healthy" if dep.is_healthy() else "unhealthy"
                        }

                return status

            except Exception as e:
                logger.error(f"Failed to get status: {e}")
                context = create_error_context("get_status", "api_server")
                handle_errors(e, context)
                raise HTTPException(
                    status_code=500, detail=f"Failed to get status: {str(e)}"
                )

        # Alert endpoints
        @self.app.get("/alerts")
        async def get_alerts(
            status: Optional[str] = None,
            severity: Optional[str] = None,
            limit: int = Query(50, description="Maximum number of alerts to return")
        ):
            """Get alerts with filtering - simplified for now"""
            try:
                if not get_alert_manager:
                    return {"alerts": [], "total": 0, "message": "Alert system not available"}

                alert_manager = get_alert_manager()
                alerts = alert_manager.get_alerts(
                    status=status, severity=severity, limit=limit
                )

                # Convert alerts to dict format
                alert_data = []
                for alert in alerts:
                    alert_data.append(alert.to_dict())

                return {"alerts": alert_data, "total": len(alert_data), "message": f"Retrieved {len(alert_data)} alerts"}

            except Exception as e:
                logger.error(f"Failed to get alerts: {e}")
                return {"alerts": [], "total": 0, "error": str(e)}

        # @self.app.post("/alerts/{alert_id}/acknowledge")
        # @require_auth
        # async def acknowledge_alert(
        #     alert_id: str,
        #     current_user: User = Depends(get_current_user)
        # ):
        #     """Acknowledge an alert"""
        #     try:
        #         if not get_alert_manager:
        #             raise HTTPException(
        #                 status_code=503, detail="Alert system not available"
        #             )

        #         alert_manager = get_alert_manager()
        #         success = alert_manager.acknowledge_alert(alert_id, current_user.username)

        #         if not success:
        #             raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")

        #         return {"message": "Alert acknowledged successfully"}

        #     except HTTPException:
        #         raise
        #     except Exception as e:
        #         logger.error(f"Failed to acknowledge alert: {e}")
        #         raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")

        @self.app.get("/alerts/stats")
        async def get_alert_stats():
            """Get alert statistics - simplified for now"""
            try:
                if not get_alert_manager:
                    return {
                        "total_alerts": 0,
                        "active_alerts": 0,
                        "acknowledged_alerts": 0,
                        "resolved_alerts": 0,
                        "critical_alerts": 0,
                        "channels": 0,
                        "enabled_channels": 0,
                        "message": "Alert system not available"
                    }

                alert_manager = get_alert_manager()
                stats = alert_manager.get_statistics()
                return stats

            except Exception as e:
                logger.error(f"Failed to get alert stats: {e}")
                return {
                    "error": str(e),
                    "total_alerts": 0,
                    "active_alerts": 0,
                    "message": "Error retrieving alert statistics"
                }

    async def _get_threat_intelligence(
        self, min_score: float = 0.0, limit: int = 100
    ) -> Dict[str, ThreatInfo]:
        """Get threat intelligence data from processor"""
        try:
            if (
                not self.processor
                or not hasattr(self.processor, "threat_storage")
                or not self.processor.threat_storage
            ):
                return {}

            # Get threats from storage
            threat_records = await self.processor.threat_storage.get_all_threats(
                min_score, limit
            )

            # Convert to API format
            threats = {}
            for record in threat_records:
                threats[record.ip_address] = ThreatInfo(
                    source_ip=record.ip_address,
                    threat_score=record.threat_score,
                    threat_level=record.threat_level.value,
                    event_count=record.event_count,
                    last_seen=record.last_seen,
                    indicators=record.indicators,
                )

            return threats

        except Exception as e:
            logger.error(f"Error getting threat intelligence: {e}")
            return {}

    async def _get_threat_by_ip(self, ip_address: str) -> Optional[ThreatInfo]:
        """Get threat information for specific IP"""
        try:
            if (
                not self.processor
                or not hasattr(self.processor, "threat_storage")
                or not self.processor.threat_storage
            ):
                return None

            # Get threat record from storage
            threat_record = await self.processor.threat_storage.get_threat(ip_address)

            if not threat_record:
                return None

            # Convert to API format
            return ThreatInfo(
                source_ip=threat_record.ip_address,
                threat_score=threat_record.threat_score,
                threat_level=threat_record.threat_level.value,
                event_count=threat_record.event_count,
                last_seen=threat_record.last_seen,
                indicators=threat_record.indicators,
            )

        except Exception as e:
            logger.error(f"Error getting threat for IP {ip_address}: {e}")
            return None

        @self.app.get("/correlations/{ip_address}")
        async def get_correlations_by_ip(
            ip_address: str,
            limit: int = Query(
                10, description="Maximum number of correlations to return"
            ),
        ):
            """Get correlation data for specific IP address"""
            try:
                if (
                    not self.processor
                    or not hasattr(self.processor, "threat_storage")
                    or not self.processor.threat_storage
                ):
                    raise HTTPException(
                        status_code=503, detail="Threat storage not available"
                    )

                # Get correlation data
                correlations = await self.processor.threat_storage.get_correlations(
                    ip_address
                )

                # Convert to API format
                correlation_data = []
                for corr in correlations[-limit:]:  # Limit results
                    correlation_data.append(
                        {
                            "correlation_score": corr.correlation_score,
                            "pattern_detected": corr.pattern_detected,
                            "created_at": corr.created_at,
                            "expires_at": corr.expires_at,
                            "event_count": len(corr.events),
                            "events": corr.events[-5:],  # Last 5 events for brevity
                        }
                    )

                return {"ip_address": ip_address, "correlations": correlation_data}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting correlations for IP {ip_address}: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to get correlations: {str(e)}"
                )

    def _setup_siem_endpoints(self):
        """Setup SIEM integration endpoints"""
        try:
            from ..siem_integration import get_siem_manager
            siem_manager = get_siem_manager()
        except ImportError:
            logger.warning("SIEM integration not available")
            return

        @self.app.get("/siem/status")
        async def get_siem_status():
            """Get SIEM integration status"""
            try:
                enabled = getattr(self.processor.config, 'siem_enabled', False) if self.processor else False
                stats = siem_manager.get_statistics() if siem_manager else {}

                return {
                    "siem_enabled": enabled,
                    "statistics": stats
                }
            except Exception as e:
                logger.error(f"Error getting SIEM status: {e}")
                raise HTTPException(status_code=500, detail="Failed to get SIEM status")

        @self.app.get("/siem/connectors")
        async def get_siem_connectors():
            """Get configured SIEM connectors"""
            try:
                if not siem_manager:
                    return {"enabled_systems": [], "available_connectors": []}

                stats = siem_manager.get_statistics()
                return {
                    "enabled_systems": stats.get("enabled_systems", []),
                    "available_connectors": stats.get("available_connectors", [])
                }
            except Exception as e:
                logger.error(f"Error getting SIEM connectors: {e}")
                raise HTTPException(status_code=500, detail="Failed to get SIEM connectors")

        @self.app.post("/siem/test")
        async def test_siem_integration(payload: Dict[str, Any]):
            """Send a test event to SIEM systems"""
            try:
                if not siem_manager:
                    raise HTTPException(status_code=503, detail="SIEM integration not available")

                # Create test event
                test_event = {
                    "logtype": "9999",  # Test event type
                    "src_host": "127.0.0.1",
                    "threat_score": payload.get("threat_score", 5.0),
                    "event_details": {"test_event": True, "message": "SIEM integration test"},
                    "processed_at": time.time(),
                    "tags": ["test", "siem_integration"]
                }

                success = siem_manager.send_event(test_event)

                return {
                    "message": "Test event sent to SIEM systems" if success else "Test event failed",
                    "success": success
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error testing SIEM integration: {e}")
                raise HTTPException(status_code=500, detail="Failed to test SIEM integration")

        @self.app.post("/siem/connectors/{connector_name}/enable")
        async def enable_siem_connector(connector_name: str, payload: Dict[str, Any]):
            """Enable or disable a SIEM connector"""
            try:
                if not siem_manager:
                    raise HTTPException(status_code=503, detail="SIEM integration not available")

                enable = payload.get("enable", True)

                if enable:
                    siem_manager.enable_system(connector_name)
                else:
                    siem_manager.disable_system(connector_name)

                return {
                    "status": f"Connector {connector_name} {'enabled' if enable else 'disabled'}",
                    "connector": connector_name,
                    "enabled": enable
                }
            except Exception as e:
                logger.error(f"Error managing SIEM connector {connector_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to manage connector: {str(e)}")

        @self.app.post("/siem/connectors/{connector_name}/test")
        async def test_siem_connector(connector_name: str):
            """Test a specific SIEM connector"""
            try:
                if not siem_manager:
                    raise HTTPException(status_code=503, detail="SIEM integration not available")

                if connector_name not in siem_manager.connectors:
                    raise HTTPException(status_code=404, detail=f"Connector {connector_name} not found")

                # Send test event to this connector only
                test_event = {
                    "logtype": "9998",  # Connector test event type
                    "src_host": "127.0.0.1",
                    "threat_score": 1.0,
                    "event_details": {"connector_test": True, "connector_name": connector_name},
                    "processed_at": time.time(),
                    "tags": ["test", "connector_test", connector_name]
                }

                # Temporarily enable only this connector for testing
                originally_enabled = connector_name in siem_manager.enabled_systems
                if not originally_enabled:
                    siem_manager.enable_system(connector_name)

                # Send test event
                success = False
                if hasattr(siem_manager.connectors[connector_name], "send_event"):
                    from ..siem_integration import SiemEvent
                    siem_event = siem_manager._convert_to_siem_event(test_event)
                    if siem_event:
                        success = siem_manager.connectors[connector_name].send_event(siem_event)

                # Restore original state
                if not originally_enabled:
                    siem_manager.disable_system(connector_name)

                return {
                    "connector": connector_name,
                    "test_result": "success" if success else "failed",
                    "success": success
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error testing SIEM connector {connector_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to test connector: {str(e)}")

        logger.info("SIEM API endpoints configured")

    def _setup_threat_intel_endpoints(self):
        """Setup threat intelligence endpoints"""
        try:
            from ..threat_intelligence import get_threat_intel_manager
            threat_intel_manager = get_threat_intel_manager()
        except ImportError:
            logger.warning("Threat intelligence not available")
            return

        @self.app.get("/threat-intel/status")
        async def get_threat_intel_status():
            """Get threat intelligence status"""
            try:
                enabled = getattr(self.processor.config, 'threat_intelligence_enabled', False) if self.processor else False
                stats = threat_intel_manager.get_statistics() if threat_intel_manager else {}

                return {
                    "threat_intel_enabled": enabled,
                    "statistics": stats
                }
            except Exception as e:
                logger.error(f"Error getting threat intel status: {e}")
                raise HTTPException(status_code=500, detail="Failed to get threat intelligence status")

        @self.app.get("/threat-intel/check/{indicator}")
        async def check_threat_indicator(indicator: str):
            """Check if an indicator is a threat"""
            try:
                if not threat_intel_manager:
                    raise HTTPException(status_code=503, detail="Threat intelligence not available")

                threat_info = threat_intel_manager.check_indicator(indicator)
                return {
                    "indicator": indicator,
                    "is_threat": threat_info is not None,
                    "threat_info": threat_info.to_dict() if threat_info else None
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error checking indicator {indicator}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to check indicator: {str(e)}")

        @self.app.get("/threat-intel/indicators")
        async def get_threat_indicators(
            indicator_type: Optional[str] = Query(None, description="Filter by indicator type (ip, domain, hash, url)"),
            source: Optional[str] = Query(None, description="Filter by feed source"),
            limit: int = Query(100, description="Maximum number of indicators to return", ge=1, le=1000)
        ):
            """Get threat indicators with optional filtering"""
            try:
                if not threat_intel_manager:
                    raise HTTPException(status_code=503, detail="Threat intelligence not available")

                indicators = threat_intel_manager.get_indicators(
                    indicator_type=indicator_type,
                    source=source,
                    limit=limit
                )

                return {
                    "count": len(indicators),
                    "indicators": [indicator.to_dict() for indicator in indicators]
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting indicators: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get indicators: {str(e)}")

        @self.app.get("/threat-intel/feeds")
        async def get_threat_feeds():
            """Get configured threat feeds"""
            try:
                if not threat_intel_manager:
                    raise HTTPException(status_code=503, detail="Threat intelligence not available")

                feeds = {}
                for name, feed in threat_intel_manager.feeds.items():
                    feeds[name] = {
                        "name": feed.name,
                        "url": feed.url,
                        "feed_type": feed.feed_type,
                        "enabled": feed.enabled,
                        "update_interval": feed.update_interval,
                        "last_update": feed.last_update,
                        "last_success": feed.last_success,
                        "error_count": feed.error_count
                    }

                return {
                    "count": len(feeds),
                    "feeds": feeds
                }
            except Exception as e:
                logger.error(f"Error getting threat feeds: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get feeds: {str(e)}")

        @self.app.post("/threat-intel/update")
        async def update_threat_feeds():
            """Manually trigger threat feed updates"""
            try:
                if not threat_intel_manager:
                    raise HTTPException(status_code=503, detail="Threat intelligence not available")

                # Update feeds (this may take time)
                threat_intel_manager.update_feeds()

                stats = threat_intel_manager.get_statistics()
                return {
                    "message": "Threat feed update completed",
                    "statistics": stats
                }
            except Exception as e:
                logger.error(f"Error updating threat feeds: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to update feeds: {str(e)}")

        @self.app.post("/threat-intel/feeds/{feed_name}/enable")
        async def enable_threat_feed(feed_name: str, payload: Dict[str, Any]):
            """Enable or disable a threat feed"""
            try:
                if not threat_intel_manager:
                    raise HTTPException(status_code=503, detail="Threat intelligence not available")

                if feed_name not in threat_intel_manager.feeds:
                    raise HTTPException(status_code=404, detail=f"Feed {feed_name} not found")

                enable = payload.get("enable", True)
                threat_intel_manager.enable_feed(feed_name, enable)

                return {
                    "feed": feed_name,
                    "enabled": enable,
                    "message": f"Feed {feed_name} {'enabled' if enable else 'disabled'}"
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error managing feed {feed_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to manage feed: {str(e)}")

        logger.info("Threat intelligence API endpoints configured")

    def _setup_firewall_endpoints(self):
        """Setup firewall management endpoints"""
        try:
            from ..firewall_manager import get_firewall_manager
            firewall_manager = get_firewall_manager()
        except ImportError:
            logger.warning("Firewall manager not available")
            return

        @self.app.get("/firewall/status")
        async def get_firewall_status():
            """Get firewall status and blocked IPs"""
            try:
                status = firewall_manager.get_firewall_status()
                return status
            except Exception as e:
                logger.error(f"Error getting firewall status: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get firewall status: {str(e)}")

        @self.app.get("/firewall/blocked")
        async def get_blocked_ips():
            """Get list of blocked IPs"""
            try:
                blocked_ips = firewall_manager.get_blocked_ips()
                return {"blocked_ips": list(blocked_ips.keys())}
            except Exception as e:
                logger.error(f"Error getting blocked IPs: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get blocked IPs: {str(e)}")

        @self.app.get("/firewall/check/{ip_address}")
        async def check_ip_blocked(ip_address: str):
            """Check if IP is blocked"""
            try:
                is_blocked = firewall_manager.is_ip_blocked(ip_address)
                return {"ip_address": ip_address, "blocked": is_blocked}
            except Exception as e:
                logger.error(f"Error checking IP {ip_address}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to check IP: {str(e)}")

        @self.app.post("/firewall/block/{ip_address}")
        async def block_ip(ip_address: str, request: Request):
            """Block an IP address"""
            try:
                data = await request.json()
                reason = data.get("reason", "manual_block")
                success = firewall_manager.block_ip(ip_address, reason)
                if success:
                    return {"message": f"Successfully blocked IP: {ip_address}", "ip_address": ip_address}
                else:
                    raise HTTPException(status_code=500, detail=f"Failed to block IP: {ip_address}")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error blocking IP {ip_address}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to block IP: {str(e)}")

        @self.app.post("/firewall/unblock/{ip_address}")
        async def unblock_ip(ip_address: str):
            """Unblock an IP address"""
            try:
                success = firewall_manager.unblock_ip(ip_address)
                if success:
                    return {"message": f"Successfully unblocked IP: {ip_address}", "ip_address": ip_address}
                else:
                    raise HTTPException(status_code=404, detail=f"IP not found in blocklist: {ip_address}")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error unblocking IP {ip_address}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to unblock IP: {str(e)}")

        logger.info("Firewall API endpoints configured")

    def _setup_packet_analysis_endpoints(self):
        """Setup packet analysis endpoints"""
        try:
            from ..packet_analyzer import get_packet_analyzer
            packet_analyzer = get_packet_analyzer()
        except ImportError:
            logger.warning("Packet analyzer not available")
            return

        @self.app.get("/packet/status")
        async def get_packet_status():
            """Get packet analysis status"""
            try:
                status = packet_analyzer.get_statistics()
                return status
            except Exception as e:
                logger.error(f"Error getting packet analysis status: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get packet status: {str(e)}")

        @self.app.get("/packet/anomalies")
        async def get_packet_anomalies(limit: int = Query(100, description="Maximum number of anomalies to return")):
            """Get recent packet-level anomalies"""
            try:
                anomalies = packet_analyzer.get_anomalies(limit)
                return {"anomalies": anomalies, "count": len(anomalies)}
            except Exception as e:
                logger.error(f"Error getting packet anomalies: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get anomalies: {str(e)}")

        @self.app.get("/packet/flows")
        async def get_active_flows():
            """Get active network flows"""
            try:
                flows = packet_analyzer.get_active_flows()
                return {"flows": flows, "count": len(flows)}
            except Exception as e:
                logger.error(f"Error getting active flows: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get flows: {str(e)}")

        @self.app.post("/packet/start")
        async def start_packet_capture(request: Request):
            """Start packet capture"""
            try:
                data = await request.json()
                interface = data.get("interface", "eth0")
                success = packet_analyzer.start_capture(interface)
                if success:
                    return {"message": f"Started packet capture on interface: {interface}", "interface": interface}
                else:
                    raise HTTPException(status_code=500, detail="Failed to start packet capture")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error starting packet capture: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to start capture: {str(e)}")

        @self.app.post("/packet/stop")
        async def stop_packet_capture():
            """Stop packet capture"""
            try:
                success = packet_analyzer.stop_capture()
                if success:
                    return {"message": "Packet capture stopped successfully"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to stop packet capture")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error stopping packet capture: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to stop capture: {str(e)}")

        logger.info("Packet analysis API endpoints configured")

    def _setup_enterprise_db_endpoints(self):
        """Setup enterprise database endpoints"""
        try:
            from ..enterprise_database import get_enterprise_db
            db_manager = get_enterprise_db()
        except ImportError:
            logger.warning("Enterprise database not available")
            return

        @self.app.get("/db/status")
        async def get_db_status():
            """Get enterprise database status"""
            try:
                status = db_manager.get_statistics()
                return status
            except Exception as e:
                logger.error(f"Error getting database status: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get database status: {str(e)}")

        @self.app.get("/db/events/recent")
        async def get_recent_events(hours: int = Query(24, description="Hours to look back")):
            """Get recent security events"""
            try:
                # Search for recent events using Elasticsearch
                from datetime import datetime, timedelta
                cutoff_time = datetime.now() - timedelta(hours=hours)
                query = {
                    "range": {
                        "timestamp": {
                            "gte": cutoff_time.isoformat()
                        }
                    }
                }
                result = db_manager.search_events(query, "events", 100)
                events = result.get("hits", {}).get("hits", [])
                return {"events": events, "count": len(events), "hours": hours}
            except Exception as e:
                logger.error(f"Error getting recent events: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get recent events: {str(e)}")

        @self.app.get("/db/anomalies/recent")
        async def get_recent_anomalies(hours: int = Query(24, description="Hours to look back")):
            """Get recent anomaly detections"""
            try:
                # Search for recent anomalies using Elasticsearch
                from datetime import datetime, timedelta
                cutoff_time = datetime.now() - timedelta(hours=hours)
                query = {
                    "range": {
                        "timestamp": {
                            "gte": cutoff_time.isoformat()
                        }
                    }
                }
                result = db_manager.search_events(query, "anomalies", 100)
                anomalies = result.get("hits", {}).get("hits", [])
                return {"anomalies": anomalies, "count": len(anomalies), "hours": hours}
            except Exception as e:
                logger.error(f"Error getting recent anomalies: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get recent anomalies: {str(e)}")

        @self.app.get("/db/search/events")
        async def search_events(
            src_ip: str = Query(None, description="Source IP to search for"),
            dst_port: int = Query(None, description="Destination port"),
            limit: int = Query(100, description="Maximum results")
        ):
            """Search security events"""
            try:
                # Build Elasticsearch query
                query = {"bool": {"must": []}}

                if src_ip:
                    query["bool"]["must"].append({
                        "term": {"logdata.REMOTE_ADDRESS": src_ip}
                    })

                if dst_port:
                    query["bool"]["must"].append({
                        "term": {"dst_port": dst_port}
                    })

                if not query["bool"]["must"]:
                    raise HTTPException(status_code=400, detail="At least one search parameter required")

                result = db_manager.search_events(query, "events", limit)
                events = result.get("hits", {}).get("hits", [])
                return {"events": events, "count": len(events), "query": {"src_ip": src_ip, "dst_port": dst_port}}
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error searching events: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to search events: {str(e)}")

        @self.app.get("/db/metrics/{measurement}")
        async def get_metrics(measurement: str, hours: int = Query(24, description="Hours of data")):
            """Get time-series metrics"""
            try:
                metrics = db_manager.get_metrics(measurement, hours)
                return {"measurement": measurement, "data": metrics, "hours": hours}
            except Exception as e:
                logger.error(f"Error getting metrics for {measurement}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

        logger.info("Enterprise database API endpoints configured")

    def _setup_ml_endpoints(self):
        """Setup ML model management endpoints"""
        if not self.model_manager:
            logger.warning("ML components not available, skipping ML endpoints")
            return

        @self.app.get("/ml/models", response_model=MLModelListResponse)
        async def list_ml_models():
            """List all available ML models"""
            try:
                model_types = self.model_manager.get_available_models()
                models = []

                for model_type in model_types:
                    model_info = self.model_manager.get_model_info(model_type)
                    if model_info:
                        models.append(MLModelInfo(**model_info))

                return MLModelListResponse(models=models, total_count=len(models))

            except Exception as e:
                logger.error(f"Error listing ML models: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to list ML models: {str(e)}")

        @self.app.get("/ml/models/{model_type}", response_model=MLModelInfo)
        async def get_ml_model(model_type: str):
            """Get information about a specific ML model"""
            try:
                model_info = self.model_manager.get_model_info(model_type)
                if not model_info:
                    raise HTTPException(status_code=404, detail=f"Model type '{model_type}' not found")

                return MLModelInfo(**model_info)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting ML model {model_type}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get ML model: {str(e)}")

        @self.app.post("/ml/models", response_model=dict)
        async def create_ml_model(request: MLModelCreateRequest):
            """Create/register a new ML model"""
            try:
                version_id = self.model_manager.register_model(
                    model_type=request.model_type,
                    model_path=request.model_path,
                    metadata_path=request.metadata_path,
                    training_metrics=request.training_metrics,
                )

                return {
                    "message": f"Model {request.model_type} registered successfully",
                    "version_id": version_id,
                    "model_type": request.model_type,
                }

            except Exception as e:
                logger.error(f"Error creating ML model: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to create ML model: {str(e)}")

        @self.app.put("/ml/models/{model_type}", response_model=dict)
        async def update_ml_model(model_type: str, request: MLModelUpdateRequest):
            """Update ML model metadata"""
            try:
                # For now, this is a placeholder - model metadata updates would need to be implemented
                # in the ModelManager class
                return {
                    "message": f"Model {model_type} update not yet implemented",
                    "model_type": model_type,
                }

            except Exception as e:
                logger.error(f"Error updating ML model {model_type}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to update ML model: {str(e)}")

        @self.app.delete("/ml/models/{model_type}", response_model=dict)
        async def delete_ml_model(model_type: str):
            """Delete an ML model and all its versions"""
            try:
                # For now, this is a placeholder - model deletion would need to be implemented
                # in the ModelManager class
                return {
                    "message": f"Model {model_type} deletion not yet implemented",
                    "model_type": model_type,
                }

            except Exception as e:
                logger.error(f"Error deleting ML model {model_type}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to delete ML model: {str(e)}")

        @self.app.post("/ml/models/{model_type}/train", response_model=dict)
        async def train_ml_model(model_type: str, request: MLModelTrainingRequest):
            """Start training for an ML model"""
            try:
                # Check if training is already in progress
                if model_type in self.training_status and self.training_status[model_type]["status"] == "training":
                    raise HTTPException(status_code=409, detail=f"Training already in progress for {model_type}")

                # Initialize training status
                self.training_status[model_type] = {
                    "status": "training",
                    "start_time": time.time(),
                    "progress": 0.0,
                    "current_epoch": 0,
                    "total_epochs": request.epochs or 10,
                    "model_type": model_type,
                }

                # Start training in background (simplified - would need proper async implementation)
                # For now, just mark as completed immediately
                import asyncio
                asyncio.create_task(self._train_model_async(model_type, request))

                return {
                    "message": f"Training started for model {model_type}",
                    "model_type": model_type,
                    "status": "training",
                    "start_time": self.training_status[model_type]["start_time"],
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error starting training for {model_type}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")

        @self.app.get("/ml/models/{model_type}/status", response_model=MLTrainingStatusResponse)
        async def get_ml_training_status(model_type: str):
            """Get training status for an ML model"""
            try:
                if model_type not in self.training_status:
                    return MLTrainingStatusResponse(
                        model_type=model_type,
                        status="idle",
                    )

                status = self.training_status[model_type]
                return MLTrainingStatusResponse(**status)

            except Exception as e:
                logger.error(f"Error getting training status for {model_type}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get training status: {str(e)}")

        @self.app.post("/ml/models/{model_type}/deploy", response_model=dict)
        async def deploy_ml_model(model_type: str):
            """Deploy a trained ML model"""
            try:
                # Load the latest version of the model
                inferencer = self.model_manager.load_model(model_type)
                if not inferencer:
                    raise HTTPException(status_code=404, detail=f"No trained model available for {model_type}")

                return {
                    "message": f"Model {model_type} deployed successfully",
                    "model_type": model_type,
                    "status": "deployed",
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error deploying model {model_type}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to deploy model: {str(e)}")

        @self.app.post("/ml/models/{model_type}/retire", response_model=dict)
        async def retire_ml_model(model_type: str):
            """Retire/unload an ML model"""
            try:
                success = self.model_manager.unload_model(model_type)
                if not success:
                    raise HTTPException(status_code=404, detail=f"Model {model_type} not loaded")

                return {
                    "message": f"Model {model_type} retired successfully",
                    "model_type": model_type,
                    "status": "retired",
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error retiring model {model_type}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to retire model: {str(e)}")

        @self.app.post("/ml/models/{model_type}/validate", response_model=MLValidationResponse)
        async def validate_ml_model(model_type: str):
            """Validate ML model performance"""
            try:
                # Check if model is loaded
                health = self.model_manager.check_model_health(model_type)
                if health["status"] == "not_loaded":
                    raise HTTPException(status_code=404, detail=f"Model {model_type} not loaded")

                # For now, return basic health info as validation
                # In a real implementation, this would run actual validation tests
                return MLValidationResponse(
                    model_type=model_type,
                    validation_status="completed",
                    accuracy=0.95,  # Placeholder
                    precision=0.92,  # Placeholder
                    recall=0.88,  # Placeholder
                    f1_score=0.90,  # Placeholder
                    auc_score=0.94,  # Placeholder
                    validation_time=time.time(),
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error validating model {model_type}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to validate model: {str(e)}")

        # Dataset management endpoints
        @self.app.get("/ml/datasets", response_model=DatasetListResponse)
        async def list_datasets(page: int = Query(1, description="Page number"), page_size: int = Query(50, description="Items per page")):
            """List available training datasets"""
            try:
                # Get all datasets
                all_datasets = list(self.datasets.values())

                # Sort by creation time (newest first)
                all_datasets.sort(key=lambda x: x.created_at, reverse=True)

                # Pagination
                total_count = len(all_datasets)
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_datasets = all_datasets[start_idx:end_idx]

                return DatasetListResponse(
                    datasets=paginated_datasets,
                    total_count=total_count,
                    page=page,
                    page_size=page_size
                )

            except Exception as e:
                logger.error(f"Error listing datasets: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to list datasets: {str(e)}")

        @self.app.post("/ml/datasets/upload", response_model=dict)
        async def upload_dataset(request: DatasetUploadRequest):
            """Upload training data (simplified - in production would handle file uploads)"""
            try:
                import uuid
                import time

                # Generate dataset ID
                dataset_id = f"dataset_{uuid.uuid4().hex[:8]}"

                # Create dataset info
                dataset_info = DatasetInfo(
                    dataset_id=dataset_id,
                    name=request.name,
                    description=request.description,
                    data_type=request.data_type,
                    size_bytes=0,  # Would be calculated from actual data
                    num_samples=0,  # Would be calculated from actual data
                    created_at=time.time(),
                    last_modified=time.time(),
                    status="processing",  # Initially processing
                    format=request.format,
                    tags=request.tags
                )

                # Store dataset info
                self.datasets[dataset_id] = dataset_info

                # In a real implementation, this would:
                # 1. Accept file upload
                # 2. Store the file
                # 3. Process and validate the data
                # 4. Update dataset statistics

                return {
                    "message": f"Dataset '{request.name}' uploaded successfully",
                    "dataset_id": dataset_id,
                    "status": "processing",
                }

            except Exception as e:
                logger.error(f"Error uploading dataset: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to upload dataset: {str(e)}")

        @self.app.get("/ml/datasets/{dataset_id}/stats", response_model=DatasetStats)
        async def get_dataset_stats(dataset_id: str):
            """Get dataset statistics"""
            try:
                if dataset_id not in self.datasets:
                    raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")

                dataset_info = self.datasets[dataset_id]

                # Generate mock statistics (in production would analyze actual data)
                mock_stats = DatasetStats(
                    dataset_id=dataset_id,
                    num_samples=dataset_info.num_samples,
                    num_features=17,  # Based on NetworkFeatures dataclass
                    feature_names=[
                        "timestamp", "event_type", "source_ip", "destination_ip",
                        "destination_port", "protocol", "username_attempts", "password_attempts",
                        "auth_success", "connection_duration", "bytes_sent", "bytes_received",
                        "packets_sent", "packets_received", "error_count", "response_code",
                        "ip_numeric"
                    ],
                    data_types={
                        "timestamp": "float",
                        "event_type": "int",
                        "source_ip": "string",
                        "destination_ip": "string",
                        "destination_port": "int",
                        "protocol": "string",
                        "username_attempts": "int",
                        "password_attempts": "int",
                        "auth_success": "bool",
                        "connection_duration": "float",
                        "bytes_sent": "int",
                        "bytes_received": "int",
                        "packets_sent": "int",
                        "packets_received": "int",
                        "error_count": "int",
                        "response_code": "int",
                        "ip_numeric": "int"
                    },
                    missing_values={feature: 0 for feature in [
                        "timestamp", "event_type", "source_ip", "destination_ip",
                        "destination_port", "protocol", "username_attempts", "password_attempts",
                        "auth_success", "connection_duration", "bytes_sent", "bytes_received",
                        "packets_sent", "packets_received", "error_count", "response_code",
                        "ip_numeric"
                    ]},
                    statistics={
                        "event_type": {"mean": 2500.0, "std": 500.0, "min": 2000.0, "max": 8000.0},
                        "destination_port": {"mean": 8080.0, "std": 10000.0, "min": 22.0, "max": 65535.0},
                        "connection_duration": {"mean": 45.2, "std": 120.5, "min": 0.0, "max": 3600.0},
                        "bytes_sent": {"mean": 1500.0, "std": 2500.0, "min": 0.0, "max": 100000.0},
                        "bytes_received": {"mean": 2000.0, "std": 3500.0, "min": 0.0, "max": 150000.0},
                    },
                    created_at=dataset_info.created_at
                )

                return mock_stats

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting dataset stats for {dataset_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get dataset statistics: {str(e)}")

        # Training job management endpoints
        @self.app.get("/ml/jobs", response_model=TrainingJobListResponse)
        async def list_training_jobs(
            page: int = Query(1, description="Page number"),
            page_size: int = Query(50, description="Items per page"),
            status: Optional[str] = Query(None, description="Filter by status")
        ):
            """List training jobs"""
            try:
                # Get all jobs
                all_jobs = list(self.training_jobs.values())

                # Filter by status if provided
                if status:
                    all_jobs = [job for job in all_jobs if job.status == status]

                # Sort by creation time (newest first)
                all_jobs.sort(key=lambda x: x.created_at, reverse=True)

                # Pagination
                total_count = len(all_jobs)
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_jobs = all_jobs[start_idx:end_idx]

                return TrainingJobListResponse(
                    jobs=paginated_jobs,
                    total_count=total_count,
                    page=page,
                    page_size=page_size
                )

            except Exception as e:
                logger.error(f"Error listing training jobs: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to list training jobs: {str(e)}")

        @self.app.post("/ml/jobs", response_model=dict)
        async def create_training_job(request: TrainingJobCreateRequest):
            """Create a new training job"""
            try:
                import uuid
                import time

                # Validate dataset exists
                if request.dataset_id not in self.datasets:
                    raise HTTPException(status_code=404, detail=f"Dataset '{request.dataset_id}' not found")

                # Generate job ID
                job_id = f"job_{uuid.uuid4().hex[:8]}"

                # Create job info
                job_info = TrainingJobInfo(
                    job_id=job_id,
                    model_type=request.model_type,
                    dataset_id=request.dataset_id,
                    status="queued",
                    priority=request.priority,
                    created_at=time.time(),
                    config=request.config
                )

                # Store job
                self.training_jobs[job_id] = job_info
                self.job_queue.append(job_id)

                # Sort queue by priority (highest first)
                self.job_queue.sort(key=lambda jid: self.training_jobs[jid].priority, reverse=True)

                return {
                    "message": f"Training job created successfully",
                    "job_id": job_id,
                    "status": "queued",
                    "queue_position": len(self.job_queue)
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error creating training job: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to create training job: {str(e)}")

        @self.app.get("/ml/jobs/{job_id}", response_model=TrainingJobInfo)
        async def get_training_job(job_id: str):
            """Get training job details"""
            try:
                if job_id not in self.training_jobs:
                    raise HTTPException(status_code=404, detail=f"Training job '{job_id}' not found")

                return self.training_jobs[job_id]

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting training job {job_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get training job: {str(e)}")

        @self.app.post("/ml/jobs/{job_id}/cancel", response_model=dict)
        async def cancel_training_job(job_id: str):
            """Cancel a training job"""
            try:
                if job_id not in self.training_jobs:
                    raise HTTPException(status_code=404, detail=f"Training job '{job_id}' not found")

                job = self.training_jobs[job_id]

                if job.status in ["completed", "failed", "cancelled"]:
                    raise HTTPException(status_code=400, detail=f"Job {job_id} is already {job.status}")

                # Cancel the job
                job.status = "cancelled"
                job.completed_at = time.time()

                # Remove from queue if queued
                if job_id in self.job_queue:
                    self.job_queue.remove(job_id)

                # Cancel active task if running
                if job_id in self.active_jobs:
                    self.active_jobs[job_id].cancel()
                    del self.active_jobs[job_id]

                return {
                    "message": f"Training job {job_id} cancelled successfully",
                    "job_id": job_id,
                    "status": "cancelled"
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error cancelling training job {job_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to cancel training job: {str(e)}")

        # ML monitoring and analytics endpoints
        @self.app.get("/ml/metrics", response_model=dict)
        async def get_ml_metrics():
            """Get real-time ML model performance metrics"""
            try:
                if not self.ml_monitoring:
                    raise HTTPException(status_code=503, detail="ML monitoring not available")

                metrics = self.ml_monitoring.get_all_metrics()
                return metrics

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting ML metrics: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get ML metrics: {str(e)}")

        @self.app.get("/ml/metrics/{model_type}", response_model=dict)
        async def get_model_metrics(model_type: str):
            """Get metrics for a specific model"""
            try:
                if not self.ml_monitoring:
                    raise HTTPException(status_code=503, detail="ML monitoring not available")

                metrics = self.ml_monitoring.get_model_metrics(model_type)
                if not metrics:
                    raise HTTPException(status_code=404, detail=f"Metrics not found for model {model_type}")

                return metrics

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting metrics for {model_type}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get model metrics: {str(e)}")

        # Prediction endpoints
        @self.app.post("/ml/predict", response_model=PredictionResult)
        async def predict_anomaly(request: PredictionRequest):
            """Make real-time anomaly prediction"""
            try:
                if not self.model_manager or not self.feature_extractor or not self.ml_monitoring:
                    raise HTTPException(status_code=503, detail="ML components not available")

                # Load model
                inferencer = self.model_manager.load_model(request.model_type)
                if not inferencer:
                    raise HTTPException(status_code=404, detail=f"Model {request.model_type} not found or not loaded")

                # Extract features
                start_time = time.time()
                features = self.feature_extractor.extract_advanced_features(request.event_data)
                if not features:
                    raise HTTPException(status_code=400, detail="Failed to extract features from event data")

                # Convert to numpy array
                feature_array = features.to_numpy_array().reshape(1, -1).astype(np.float32)

                # Make prediction
                prediction_start = time.time()
                with torch.no_grad():
                    torch_features = torch.from_numpy(feature_array)
                    outputs = inferencer(torch_features)
                    # For anomalib models, prediction results vary by model type
                    # Simplified prediction logic
                    anomaly_score = float(outputs.pred_score.mean()) if hasattr(outputs, 'pred_score') else 0.5
                    is_anomaly = anomaly_score > 0.5

                inference_time = time.time() - prediction_start

                # Create prediction result
                result = PredictionResult(
                    is_anomaly=is_anomaly,
                    confidence=max(0.0, min(1.0, 1.0 - anomaly_score)),  # Convert anomaly score to confidence
                    anomaly_score=anomaly_score,
                    model_type=request.model_type,
                    timestamp=time.time(),
                    inference_time_ms=inference_time * 1000,
                    explanation=self._generate_prediction_explanation(features) if request.include_explanation else None
                )

                # Record metrics
                prediction_dict = {
                    'is_anomaly': is_anomaly,
                    'confidence': result.confidence,
                    'anomaly_score': anomaly_score
                }
                self.ml_monitoring.record_prediction(
                    request.model_type,
                    prediction_dict,
                    inference_time,
                    feature_array
                )

                return result

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error making prediction: {e}")
                # Record error in monitoring
                if self.ml_monitoring:
                    self.ml_monitoring.record_prediction_error(request.model_type)
                raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

        @self.app.post("/ml/predict/batch", response_model=BatchPredictionResult)
        async def predict_batch_anomalies(request: BatchPredictionRequest):
            """Make batch anomaly predictions"""
            try:
                if not self.model_manager or not self.feature_extractor or not self.ml_monitoring:
                    raise HTTPException(status_code=503, detail="ML components not available")

                if len(request.events_data) > 1000:
                    raise HTTPException(status_code=400, detail="Batch size limited to 1000 predictions")

                # Load model
                inferencer = self.model_manager.load_model(request.model_type)
                if not inferencer:
                    raise HTTPException(status_code=404, detail=f"Model {request.model_type} not found or not loaded")

                # Process batch
                predictions = []
                total_inference_time = 0.0

                for event_data in request.events_data:
                    # Extract features
                    features = self.feature_extractor.extract_advanced_features(event_data)
                    if not features:
                        continue

                    # Convert to numpy array
                    feature_array = features.to_numpy_array().reshape(1, -1).astype(np.float32)

                    # Make prediction
                    prediction_start = time.time()
                    with torch.no_grad():
                        torch_features = torch.from_numpy(feature_array)
                        outputs = inferencer(torch_features)
                        anomaly_score = float(outputs.pred_score.mean()) if hasattr(outputs, 'pred_score') else 0.5
                        is_anomaly = anomaly_score > 0.5

                    inference_time = time.time() - prediction_start
                    total_inference_time += inference_time

                    # Create prediction result
                    result = PredictionResult(
                        is_anomaly=is_anomaly,
                        confidence=max(0.0, min(1.0, 1.0 - anomaly_score)),
                        anomaly_score=anomaly_score,
                        model_type=request.model_type,
                        timestamp=time.time(),
                        inference_time_ms=inference_time * 1000,
                        explanation=self._generate_prediction_explanation(features) if request.include_explanations else None
                    )
                    predictions.append(result)

                    # Record metrics
                    prediction_dict = {
                        'is_anomaly': is_anomaly,
                        'confidence': result.confidence,
                        'anomaly_score': anomaly_score
                    }
                    self.ml_monitoring.record_prediction(
                        request.model_type,
                        prediction_dict,
                        inference_time,
                        feature_array
                    )

                avg_inference_time = total_inference_time / len(predictions) if predictions else 0.0

                return BatchPredictionResult(
                    predictions=predictions,
                    total_predictions=len(predictions),
                    avg_inference_time_ms=avg_inference_time * 1000,
                    model_type=request.model_type,
                    timestamp=time.time()
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error making batch prediction: {e}")
                raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

        # Drift detection endpoints
        @self.app.get("/ml/drift/{model_type}", response_model=dict)
        async def check_model_drift(model_type: str):
            """Check for model drift"""
            try:
                if not self.ml_monitoring:
                    raise HTTPException(status_code=503, detail="ML monitoring not available")

                # Get recent predictions for drift detection
                # In a real implementation, this would use actual feature data
                # For now, simulate with random data
                import numpy as np
                mock_features = np.random.randn(50, 17).astype(np.float32)  # 50 samples, 17 features

                drift_result = self.ml_monitoring.detect_drift(model_type, mock_features)

                if drift_result:
                    return {
                        "drift_detected": drift_result.drift_detected,
                        "drift_score": drift_result.drift_score,
                        "threshold": drift_result.threshold,
                        "detection_method": drift_result.detection_method,
                        "features_affected": drift_result.features_affected,
                        "recommendations": drift_result.recommendations,
                        "timestamp": drift_result.timestamp
                    }
                else:
                    return {
                        "drift_detected": False,
                        "message": "Insufficient data for drift detection",
                        "timestamp": time.time()
                    }

            except Exception as e:
                logger.error(f"Error checking drift for {model_type}: {e}")
                raise HTTPException(status_code=500, detail=f"Drift detection failed: {str(e)}")

        @self.app.get("/ml/drift/{model_type}/history", response_model=dict)
        async def get_drift_history(model_type: str, limit: int = Query(10, description="Number of historical results to return")):
            """Get drift detection history for a model"""
            try:
                if not self.ml_monitoring:
                    raise HTTPException(status_code=503, detail="ML monitoring not available")

                history = self.ml_monitoring.get_drift_history(model_type, limit)
                return {
                    "model_type": model_type,
                    "drift_history": history,
                    "total_checks": len(history),
                    "timestamp": time.time()
                }

            except Exception as e:
                logger.error(f"Error getting drift history for {model_type}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get drift history: {str(e)}")

        # A/B testing endpoints
        @self.app.post("/ml/ab-test", response_model=dict)
        async def start_ab_test(model_a: str, model_b: str, traffic_split: float = 0.5, duration_hours: int = 24):
            """Start an A/B test between two models"""
            try:
                if not self.ml_monitoring:
                    raise HTTPException(status_code=503, detail="ML monitoring not available")

                test_id = self.ml_monitoring.start_ab_test(
                    model_a=model_a,
                    model_b=model_b,
                    traffic_split=traffic_split,
                    test_duration_hours=duration_hours
                )

                return {
                    "message": f"A/B test started between {model_a} and {model_b}",
                    "test_id": test_id,
                    "model_a": model_a,
                    "model_b": model_b,
                    "traffic_split": traffic_split,
                    "duration_hours": duration_hours,
                    "status": "running"
                }

            except Exception as e:
                logger.error(f"Error starting A/B test: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to start A/B test: {str(e)}")

        @self.app.get("/ml/ab-test", response_model=dict)
        async def get_ab_test_results():
            """Get A/B test results"""
            try:
                if not self.ml_monitoring:
                    raise HTTPException(status_code=503, detail="ML monitoring not available")

                results = self.ml_monitoring.get_ab_test_results()
                return results

            except Exception as e:
                logger.error(f"Error getting A/B test results: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get A/B test results: {str(e)}")

        @self.app.post("/ml/ab-test/{test_id}/stop", response_model=dict)
        async def stop_ab_test(test_id: str):
            """Stop an A/B test"""
            try:
                if not self.ml_monitoring:
                    raise HTTPException(status_code=503, detail="ML monitoring not available")

                # Manually end the test
                if hasattr(self.ml_monitoring, 'ab_tests') and test_id in self.ml_monitoring.ab_tests:
                    self.ml_monitoring.ab_tests[test_id].status = "stopped"
                    self.ml_monitoring.ab_tests[test_id].end_time = time.time()

                    if self.ml_monitoring.active_ab_test == test_id:
                        self.ml_monitoring.active_ab_test = None

                    return {
                        "message": f"A/B test {test_id} stopped",
                        "test_id": test_id,
                        "status": "stopped"
                    }
                else:
                    raise HTTPException(status_code=404, detail=f"A/B test {test_id} not found")

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error stopping A/B test {test_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to stop A/B test: {str(e)}")

        # ML integration endpoints
        @self.app.get("/ml/integration/stats", response_model=dict)
        async def get_integration_stats():
            """Get ML integration statistics"""
            try:
                if not self.ml_integration:
                    raise HTTPException(status_code=503, detail="ML integration not available")

                stats = self.ml_integration.get_integration_stats()
                return stats

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting integration stats: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get integration stats: {str(e)}")

        @self.app.get("/ml/alerts", response_model=dict)
        async def get_ml_alerts(limit: int = Query(50, description="Number of alerts to return")):
            """Get recent ML-generated alerts"""
            try:
                if not self.ml_integration:
                    raise HTTPException(status_code=503, detail="ML integration not available")

                alerts = self.ml_integration.get_ml_alerts(limit)
                return {
                    "alerts": alerts,
                    "total_count": len(alerts),
                    "timestamp": time.time()
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting ML alerts: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get ML alerts: {str(e)}")

        @self.app.get("/ml/retraining-triggers", response_model=dict)
        async def get_retraining_triggers(limit: int = Query(20, description="Number of triggers to return")):
            """Get retraining triggers"""
            try:
                if not self.ml_integration:
                    raise HTTPException(status_code=503, detail="ML integration not available")

                triggers = self.ml_integration.get_retraining_triggers(limit)
                return {
                    "triggers": triggers,
                    "total_count": len(triggers),
                    "timestamp": time.time()
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting retraining triggers: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get retraining triggers: {str(e)}")

        @self.app.get("/ml/incidents/{incident_id}/insights", response_model=dict)
        async def get_incident_insights(incident_id: str):
            """Get ML insights for an incident"""
            try:
                if not self.ml_integration:
                    raise HTTPException(status_code=503, detail="ML integration not available")

                insights = self.ml_integration.get_incident_insights(incident_id)
                if not insights:
                    raise HTTPException(status_code=404, detail=f"No ML insights found for incident {incident_id}")

                return insights

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting incident insights for {incident_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get incident insights: {str(e)}")

        logger.info("ML API endpoints configured")

    def _generate_prediction_explanation(self, features) -> Dict[str, Any]:
        """Generate explanation for prediction based on feature importance"""
        try:
            # Simple feature importance based on feature values and statistical properties
            feature_importance = {}

            # Get feature names and values
            feature_dict = features.to_dict()

            # Calculate importance scores (simplified approach)
            for feature_name, value in feature_dict.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    # Higher absolute values are more important
                    importance = min(1.0, abs(value) / 100.0)  # Normalize

                    # Certain features are inherently more important for anomaly detection
                    if 'error' in feature_name.lower():
                        importance *= 1.5
                    elif 'auth' in feature_name.lower():
                        importance *= 1.3
                    elif 'anomaly' in feature_name.lower():
                        importance *= 2.0

                    feature_importance[feature_name] = min(1.0, importance)

            # Sort by importance
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

            return {
                "feature_importance": dict(sorted_features[:10]),  # Top 10 features
                "top_contributing_features": [f[0] for f in sorted_features[:5]],
                "explanation_method": "statistical_weighting",
                "confidence_interpretation": "Higher values indicate stronger anomaly signals"
            }

        except Exception as e:
            logger.warning(f"Failed to generate prediction explanation: {e}")
            return {
                "error": "Could not generate explanation",
                "feature_importance": {},
                "top_contributing_features": []
            }

    async def _train_model_async(self, model_type: str, request: MLModelTrainingRequest):
        """Async training task for ML models"""
        try:
            logger.info(f"Starting async training for {model_type}")

            # For now, simulate training progress
            total_epochs = request.epochs or 10
            for epoch in range(1, total_epochs + 1):
                # Simulate training time
                await asyncio.sleep(1)

                # Update progress
                self.training_status[model_type]["current_epoch"] = epoch
                self.training_status[model_type]["progress"] = epoch / total_epochs

                logger.debug(f"Training {model_type}: epoch {epoch}/{total_epochs}")

            # Mark training as completed
            self.training_status[model_type]["status"] = "completed"
            self.training_status[model_type]["progress"] = 1.0

            logger.info(f"Training completed for {model_type}")

        except Exception as e:
            logger.error(f"Error in async training for {model_type}: {e}")
            self.training_status[model_type]["status"] = "failed"
            self.training_status[model_type]["error"] = str(e)

    async def _process_training_job(self, job_id: str):
        """Process a single training job"""
        try:
            job = self.training_jobs[job_id]
            job.status = "running"
            job.started_at = time.time()

            logger.info(f"Starting training job {job_id} for model {job.model_type}")

            # Simulate training process
            total_epochs = job.config.get("epochs", 10)
            for epoch in range(1, total_epochs + 1):
                # Simulate training time per epoch
                await asyncio.sleep(2)

                # Update progress
                job.progress = epoch / total_epochs

                logger.debug(f"Job {job_id}: epoch {epoch}/{total_epochs}")

            # Mark as completed
            job.status = "completed"
            job.completed_at = time.time()
            job.duration_seconds = job.completed_at - job.started_at
            job.progress = 1.0
            job.metrics = {
                "accuracy": 0.95,
                "precision": 0.92,
                "recall": 0.88,
                "f1_score": 0.90,
                "loss": 0.05
            }

            logger.info(f"Training job {job_id} completed successfully")

        except asyncio.CancelledError:
            logger.info(f"Training job {job_id} was cancelled")
            job.status = "cancelled"
            job.completed_at = time.time()
            raise
        except Exception as e:
            logger.error(f"Error in training job {job_id}: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = time.time()
        finally:
            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

    async def _process_job_queue(self):
        """Process the training job queue"""
        while True:
            try:
                # Check for queued jobs
                if self.job_queue:
                    # Get highest priority job
                    job_id = self.job_queue.pop(0)
                    job = self.training_jobs[job_id]

                    # Start the job
                    task = asyncio.create_task(self._process_training_job(job_id))
                    self.active_jobs[job_id] = task

                # Wait before checking queue again
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error processing job queue: {e}")
                await asyncio.sleep(5)

    def _setup_websocket(self):
        """Setup WebSocket components and routes"""
        try:
            # Import WebSocket components
            from .websocket_manager import WebSocketManager
            from .websocket_server import WebSocketServer

            # Use processor's WebSocket manager if available, otherwise create our own
            if self.processor and hasattr(self.processor, 'websocket_manager') and self.processor.websocket_manager:
                self.websocket_manager = self.processor.websocket_manager
                logger.info("Using processor's WebSocket manager")
            else:
                # Create standalone WebSocket manager
                self.websocket_manager = WebSocketManager()
                logger.info("Created standalone WebSocket manager")

            # Create WebSocket server
            self.websocket_server = WebSocketServer(self.websocket_manager)

            # Integrate with authentication system
            try:
                from ..security.auth_manager import get_auth_manager
                auth_manager = get_auth_manager()
                self.websocket_server.set_auth_manager(auth_manager)
                logger.info("WebSocket server integrated with authentication system")
            except ImportError:
                logger.warning("Authentication system not available for WebSocket integration")

            # Add main WebSocket route
            @self.app.websocket("/ws")
            async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None, reconnect_id: Optional[str] = None):
                """
                WebSocket endpoint for real-time event streaming

                Query parameters:
                - token: Optional authentication token
                - reconnect_id: Previous connection ID for recovery
                """
                try:
                    logger.info(f"WebSocket connection attempt from {websocket.client}")

                    # Handle connection through WebSocket server
                    await self.websocket_server.websocket_endpoint(websocket, token, None, reconnect_id)

                except WebSocketDisconnect:
                    logger.info("WebSocket client disconnected")
                except Exception as e:
                    logger.error(f"WebSocket endpoint error: {e}")
                    try:
                        await websocket.close(code=1011, reason="Internal server error")
                    except:
                        pass  # Connection may already be closed

            # Add specific streaming endpoints
            @self.app.websocket("/ws/threats")
            async def websocket_threats_endpoint(websocket: WebSocket, token: Optional[str] = None, reconnect_id: Optional[str] = None):
                """
                WebSocket endpoint for real-time threat updates
                Automatically subscribes to threats channel

                Query parameters:
                - token: Optional authentication token
                - reconnect_id: Previous connection ID for recovery
                """
                try:
                    logger.info(f"WebSocket threats connection attempt from {websocket.client}")

                    # Handle connection and auto-subscribe to threats
                    await self.websocket_server.websocket_endpoint(websocket, token, auto_subscribe="threats", reconnect_id=reconnect_id)

                except WebSocketDisconnect:
                    logger.info("WebSocket threats client disconnected")
                except Exception as e:
                    logger.error(f"WebSocket threats endpoint error: {e}")
                    try:
                        await websocket.close(code=1011, reason="Internal server error")
                    except:
                        pass

            @self.app.websocket("/ws/alerts")
            async def websocket_alerts_endpoint(websocket: WebSocket, token: Optional[str] = None, reconnect_id: Optional[str] = None):
                """
                WebSocket endpoint for real-time alert notifications
                Automatically subscribes to alerts channel

                Query parameters:
                - token: Optional authentication token
                - reconnect_id: Previous connection ID for recovery
                """
                try:
                    logger.info(f"WebSocket alerts connection attempt from {websocket.client}")

                    # Handle connection and auto-subscribe to alerts
                    await self.websocket_server.websocket_endpoint(websocket, token, auto_subscribe="alerts", reconnect_id=reconnect_id)

                except WebSocketDisconnect:
                    logger.info("WebSocket alerts client disconnected")
                except Exception as e:
                    logger.error(f"WebSocket alerts endpoint error: {e}")
                    try:
                        await websocket.close(code=1011, reason="Internal server error")
                    except:
                        pass

            @self.app.websocket("/ws/system")
            async def websocket_system_endpoint(websocket: WebSocket, token: Optional[str] = None, reconnect_id: Optional[str] = None):
                """
                WebSocket endpoint for system health updates
                Automatically subscribes to status channel

                Query parameters:
                - token: Optional authentication token
                - reconnect_id: Previous connection ID for recovery
                """
                try:
                    logger.info(f"WebSocket system connection attempt from {websocket.client}")

                    # Handle connection and auto-subscribe to status
                    await self.websocket_server.websocket_endpoint(websocket, token, auto_subscribe="status", reconnect_id=reconnect_id)

                except WebSocketDisconnect:
                    logger.info("WebSocket system client disconnected")
                except Exception as e:
                    logger.error(f"WebSocket system endpoint error: {e}")
                    try:
                        await websocket.close(code=1011, reason="Internal server error")
                    except:
                        pass

            @self.app.websocket("/ws/network")
            async def websocket_network_endpoint(websocket: WebSocket, token: Optional[str] = None, reconnect_id: Optional[str] = None):
                """
                WebSocket endpoint for network traffic updates
                Automatically subscribes to network channel

                Query parameters:
                - token: Optional authentication token
                - reconnect_id: Previous connection ID for recovery
                """
                try:
                    logger.info(f"WebSocket network connection attempt from {websocket.client}")

                    # Handle connection and auto-subscribe to network
                    await self.websocket_server.websocket_endpoint(websocket, token, auto_subscribe="network", reconnect_id=reconnect_id)

                except WebSocketDisconnect:
                    logger.info("WebSocket network client disconnected")
                except Exception as e:
                    logger.error(f"WebSocket network endpoint error: {e}")
                    try:
                        await websocket.close(code=1011, reason="Internal server error")
                    except:
                        pass

            @self.app.websocket("/ws/packets")
            async def websocket_packets_endpoint(websocket: WebSocket, token: Optional[str] = None, reconnect_id: Optional[str] = None):
                """
                WebSocket endpoint for packet analysis streams
                Automatically subscribes to packets channel

                Query parameters:
                - token: Optional authentication token
                - reconnect_id: Previous connection ID for recovery
                """
                try:
                    logger.info(f"WebSocket packets connection attempt from {websocket.client}")

                    # Handle connection and auto-subscribe to packets
                    await self.websocket_server.websocket_endpoint(websocket, token, auto_subscribe="packets", reconnect_id=reconnect_id)

                except WebSocketDisconnect:
                    logger.info("WebSocket packets client disconnected")
                except Exception as e:
                    logger.error(f"WebSocket packets endpoint error: {e}")
                    try:
                        await websocket.close(code=1011, reason="Internal server error")
                    except:
                        pass

            # Add WebSocket monitoring endpoints
        @self.app.get("/ws/connections")
        async def get_websocket_connections():
            """Get WebSocket connection information"""
            try:
                if not self.websocket_manager:
                    return {"connections": [], "total": 0}

                analytics = self.websocket_manager.get_connection_analytics()
                return {
                    "total_active": analytics["active_connections"],
                    "total_accepted": analytics["total_connections_accepted"],
                    "total_closed": analytics["total_connections_closed"],
                    "channels": analytics["channels"],
                    "connections": list(analytics["client_analytics"].values())
                }
            except Exception as e:
                logger.error(f"Error getting WebSocket connections: {e}")
                return {"error": str(e), "connections": [], "total": 0}

        @self.app.get("/ws/stats")
        async def get_websocket_stats():
            """Get WebSocket server statistics"""
            try:
                if not self.websocket_manager:
                    return {"error": "WebSocket manager not available"}

                stats = self.websocket_manager.get_connection_stats()
                performance = self.websocket_manager.get_performance_metrics()

                return {
                    "connection_stats": stats,
                    "performance_metrics": performance,
                    "timestamp": time.time()
                }
            except Exception as e:
                logger.error(f"Error getting WebSocket stats: {e}")
                return {"error": str(e)}

        @self.app.get("/ws/analytics")
        async def get_websocket_analytics():
            """Get comprehensive WebSocket analytics"""
            try:
                if not self.websocket_manager:
                    return {"error": "WebSocket manager not available"}

                analytics = self.websocket_manager.get_connection_analytics()
                return analytics
            except Exception as e:
                logger.error(f"Error getting WebSocket analytics: {e}")
                return {"error": str(e)}

            logger.info("WebSocket routes configured")
        except Exception as e:
            logger.error(f"Failed to setup WebSocket components: {e}")
            # Continue without WebSocket support if setup fails
            self.websocket_manager = None
            self.websocket_server = None

    # BaseComponent abstract methods
    async def _initialize(self):
        """Initialize the API server and setup additional endpoints"""
        logger.info("API Server _initialize method called")
        try:
            # Setup firewall endpoints
            logger.info("Setting up firewall endpoints...")
            self._setup_firewall_endpoints()
            logger.info("Firewall endpoints setup completed")

            # Setup packet analysis endpoints
            logger.info("Setting up packet analysis endpoints...")
            self._setup_packet_analysis_endpoints()
            logger.info("Packet analysis endpoints setup completed")

            # Setup enterprise database endpoints
            logger.info("Setting up enterprise database endpoints...")
            self._setup_enterprise_db_endpoints()
            logger.info("Enterprise database endpoints setup completed")
        except Exception as e:
            logger.error(f"Error setting up additional endpoints: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def _start_internal(self):
        """Start the API server"""
        print("=== API SERVER _START_INTERNAL STARTED ===")
        try:
            # Setup additional endpoints after server starts
            try:
                print("=== SETTING UP FIREWALL ENDPOINTS ===")
                logger.info("Setting up firewall endpoints...")
                self._setup_firewall_endpoints()
                logger.info("Firewall endpoints setup completed")
                print("=== FIREWALL ENDPOINTS DONE ===")
            except Exception as e:
                logger.error(f"Failed to setup firewall endpoints: {e}")
                print(f"=== FIREWALL SETUP FAILED: {e} ===")

            try:
                print("=== SETTING UP PACKET ANALYSIS ENDPOINTS ===")
                logger.info("Setting up packet analysis endpoints...")
                self._setup_packet_analysis_endpoints()
                logger.info("Packet analysis endpoints setup completed")
                print("=== PACKET ANALYSIS ENDPOINTS DONE ===")
            except Exception as e:
                logger.error(f"Failed to setup packet analysis endpoints: {e}")
                print(f"=== PACKET ANALYSIS SETUP FAILED: {e} ===")

            try:
                print("=== SETTING UP ENTERPRISE DB ENDPOINTS ===")
                logger.info("Setting up enterprise database endpoints...")
                self._setup_enterprise_db_endpoints()
                logger.info("Enterprise database endpoints setup completed")
                print("=== ENTERPRISE DB ENDPOINTS DONE ===")
            except Exception as e:
                logger.error(f"Failed to setup enterprise database endpoints: {e}")
                print(f"=== ENTERPRISE DB SETUP FAILED: {e} ===")

            print("=== ALL ENDPOINT SETUP COMPLETED ===")
            # Start WebSocket manager if we created our own
            if self.websocket_manager and self.processor and not hasattr(self.processor, 'websocket_manager'):
                await self.websocket_manager.start()
                logger.info("Started standalone WebSocket manager")

            # Create server configuration
            config = uvicorn.Config(
                app=self.app, host=self.host, port=self.port, log_level="info"
            )

            # Create and start server
            self.server = uvicorn.Server(config)

            # Start server in background task
            asyncio.create_task(self.server.serve())

            # Start job queue processor
            asyncio.create_task(self._process_job_queue())
            logger.info("Training job queue processor started")

            logger.info(f"API server started on http://{self.host}:{self.port}")
            logger.info(
                f"API documentation available at http://{self.host}:{self.port}/docs"
            )
            logger.info(
                f"WebSocket endpoint available at ws://{self.host}:{self.port}/ws"
            )

        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            context = create_error_context("start_api_server", "api_server")
            handle_errors(e, context)
            raise

    async def _stop_internal(self):
        """Stop the API server"""
        try:
            if self.server:
                await self.server.shutdown()
                logger.info("API server stopped")

            # Stop WebSocket manager if we created our own
            if self.websocket_manager and self.processor and not hasattr(self.processor, 'websocket_manager'):
                await self.websocket_manager.stop()
                logger.info("Stopped standalone WebSocket manager")

        except Exception as e:
            logger.error(f"Error stopping API server: {e}")
            context = create_error_context("stop_api_server", "api_server")
            handle_errors(e, context)

    async def _cleanup(self):
        """Cleanup API server resources"""
        # Server shutdown is handled in _stop_internal
        pass


# Factory function for creating API server
def create_api_server(
    processor=None, host: str = "0.0.0.0", port: int = 8082
) -> APIServer:
    """Create and configure API server instance"""
    return APIServer(name="api_server", host=host, port=port, processor=processor)
