"""
Integration Tests for Notification Service
Tests with real PostgreSQL database (CI-compatible)
"""

import sys
from pathlib import Path
# Add parent folder (project root) to sys.path so local modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
proj_root_str = str(PROJECT_ROOT)
if proj_root_str not in sys.path:
    sys.path.insert(0, proj_root_str)

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
import uuid
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

from main import app
from database import Base, get_db
from models import Notification, NotificationChannel, NotificationStatus
import crud

# Test database URL - Use env var for CI, fallback for local
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://testuser:testpass@localhost:15434/testdb"
)

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create test database and tables"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Teardown - drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(test_db):
    """Get database session for tests"""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Create test client with database override"""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_notification(db_session):
    """Create a test notification in database"""
    notification_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    notification = await crud.create_notification(
        db=db_session,
        notification_id=notification_id,
        user_id=user_id,
        notification_type="test",
        channel=NotificationChannel.EMAIL,
        body="Test notification body"
    )
    return notification


@pytest_asyncio.fixture
async def test_user_id():
    """Generate a test user ID"""
    return str(uuid.uuid4())


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

class TestHealthCheck:
    """Test health check endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check returns healthy status"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "notification-service"
        assert "kafka_connected" in data


# ============================================================================
# EMAIL NOTIFICATION TESTS
# ============================================================================

class TestEmailNotifications:
    """Test email notification endpoints"""
    
    @pytest.mark.asyncio
    @patch('main.BackgroundTasks.add_task')
    async def test_send_email_notification(self, mock_add_task, client):
        """Test sending an email notification"""
        email_data = {
            "to": "test@example.com",
            "subject": "Test Email",
            "body": "This is a test email notification"
        }
        
        response = await client.post("/notifications/email", json=email_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "notification_id" in data
        assert mock_add_task.called
    
    @pytest.mark.asyncio
    async def test_send_email_invalid_email(self, client):
        """Test sending email with invalid email address"""
        email_data = {
            "to": "not-an-email",
            "subject": "Test",
            "body": "Test body"
        }
        
        response = await client.post("/notifications/email", json=email_data)
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_send_email_missing_fields(self, client):
        """Test sending email with missing required fields"""
        email_data = {
            "to": "test@example.com"
            # Missing subject and body
        }
        
        response = await client.post("/notifications/email", json=email_data)
        
        assert response.status_code == 422


# ============================================================================
# SMS NOTIFICATION TESTS
# ============================================================================

class TestSMSNotifications:
    """Test SMS notification endpoints"""
    
    @pytest.mark.asyncio
    @patch('main.BackgroundTasks.add_task')
    async def test_send_sms_notification(self, mock_add_task, client):
        """Test sending an SMS notification"""
        sms_data = {
            "to": "+1234567890",
            "message": "Test SMS message"
        }
        
        response = await client.post("/notifications/sms", json=sms_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "notification_id" in data
        assert mock_add_task.called
    
    @pytest.mark.asyncio
    async def test_send_sms_missing_message(self, client):
        """Test sending SMS with missing message"""
        sms_data = {
            "to": "+1234567890"
            # Missing message
        }
        
        response = await client.post("/notifications/sms", json=sms_data)
        
        assert response.status_code == 422


# ============================================================================
# PUSH NOTIFICATION TESTS
# ============================================================================

class TestPushNotifications:
    """Test push notification endpoints"""
    
    @pytest.mark.asyncio
    @patch('main.BackgroundTasks.add_task')
    async def test_send_push_notification(self, mock_add_task, client):
        """Test sending a push notification"""
        push_data = {
            "user_id": str(uuid.uuid4()),
            "title": "Test Push",
            "body": "Test push notification",
            "data": {"key": "value"}
        }
        
        response = await client.post("/notifications/push", json=push_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "notification_id" in data
        assert mock_add_task.called


# ============================================================================
# USER NOTIFICATIONS TESTS
# ============================================================================

class TestUserNotifications:
    """Test user notification retrieval endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_my_notifications(self, client, test_notification, db_session):
        """Test getting current user's notifications"""
        response = await client.get(
            "/notifications/my",
            headers={"x-user-id": str(test_notification.user_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "total" in data
        assert data["total"] >= 1
    
    @pytest.mark.asyncio
    async def test_get_my_notifications_unauthorized(self, client):
        """Test getting notifications without authentication"""
        response = await client.get("/notifications/my")
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_my_notifications_with_filters(self, client, test_user_id):
        """Test getting notifications with channel filter"""
        response = await client.get(
            "/notifications/my?channel=email",
            headers={"x-user-id": test_user_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
    
    @pytest.mark.asyncio
    async def test_get_my_notifications_pagination(self, client, test_user_id):
        """Test notification pagination"""
        response = await client.get(
            "/notifications/my?limit=5&offset=0",
            headers={"x-user-id": test_user_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) <= 5
    
    @pytest.mark.asyncio
    async def test_get_unread_count(self, client, test_notification):
        """Test getting unread notification count"""
        response = await client.get(
            "/notifications/unread",
            headers={"x-user-id": str(test_notification.user_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)
        assert "notifications" in data
    
    @pytest.mark.asyncio
    async def test_get_unread_count_unauthorized(self, client):
        """Test getting unread count without authentication"""
        response = await client.get("/notifications/unread")
        
        assert response.status_code == 401


# ============================================================================
# NOTIFICATION ACTIONS TESTS
# ============================================================================

class TestNotificationActions:
    """Test notification action endpoints (mark as read, etc.)"""
    
    @pytest.mark.asyncio
    async def test_mark_notification_as_read(self, client, test_notification):
        """Test marking a notification as read"""
        response = await client.post(
            f"/notifications/{test_notification.id}/read"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "notification_id" in data
        assert data["notification_id"] == str(test_notification.id)
        assert "read_at" in data
    
    @pytest.mark.asyncio
    async def test_mark_notification_as_read_not_found(self, client):
        """Test marking non-existent notification as read"""
        fake_id = str(uuid.uuid4())
        
        response = await client.post(f"/notifications/{fake_id}/read")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_mark_all_as_read(self, client, test_notification):
        """Test marking all notifications as read"""
        response = await client.post(
            "/notifications/read-all",
            headers={"x-user-id": str(test_notification.user_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "marked_read" in data
        assert data["user_id"] == str(test_notification.user_id)
    
    @pytest.mark.asyncio
    async def test_mark_all_as_read_unauthorized(self, client):
        """Test marking all as read without authentication"""
        response = await client.post("/notifications/read-all")
        
        assert response.status_code == 401


# ============================================================================
# NOTIFICATION LOGS AND STATS TESTS
# ============================================================================

class TestNotificationLogsAndStats:
    """Test notification log and statistics endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_notification_log(self, client, test_notification):
        """Test getting notification log"""
        response = await client.get(
            "/notifications/log",
            headers={"x-user-id": str(test_notification.user_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_get_notification_log_with_pagination(self, client, test_notification):
        """Test getting notification log with pagination"""
        response = await client.get("/notifications/log?limit=10&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert len(data["notifications"]) <= 10
    
    @pytest.mark.asyncio
    async def test_get_notification_stats(self, client, test_notification, db_session):
        """Test getting notification statistics"""
        response = await client.get("/notifications/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "sent" in data
        assert "failed" in data
        assert "pending" in data


# ============================================================================
# DATABASE INTEGRATION TESTS
# ============================================================================

class TestDatabaseIntegration:
    """Test database operations directly"""
    
    @pytest.mark.asyncio
    async def test_notification_persistence(self, db_session):
        """Test that notification data persists correctly"""
        notification_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        # Create notification
        created_notification = await crud.create_notification(
            db=db_session,
            notification_id=notification_id,
            user_id=user_id,
            notification_type="test",
            channel=NotificationChannel.EMAIL,
            body="Test body"
        )
        
        # Retrieve notification
        retrieved_notification = await crud.get_notification_by_id(
            db_session,
            notification_id
        )
        
        assert retrieved_notification is not None
        assert retrieved_notification.id == created_notification.id
        assert retrieved_notification.user_id == created_notification.user_id
        assert retrieved_notification.channel == NotificationChannel.EMAIL
    
    @pytest.mark.asyncio
    async def test_notification_status_update(self, db_session):
        """Test updating notification status"""
        notification_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        # Create notification
        notification = await crud.create_notification(
            db=db_session,
            notification_id=notification_id,
            user_id=user_id,
            notification_type="test",
            channel=NotificationChannel.EMAIL,
            body="Test body"
        )
        
        assert notification.status == NotificationStatus.PENDING
        
        # Update to SENT
        updated = await crud.update_notification_status(
            db_session,
            notification_id,
            NotificationStatus.SENT
        )
        
        assert updated.status == NotificationStatus.SENT
        assert updated.sent_at is not None
    
    @pytest.mark.asyncio
    async def test_get_user_notifications_filtering(self, db_session):
        """Test filtering user notifications by channel and status"""
        user_id = str(uuid.uuid4())
        
        # Create multiple notifications
        await crud.create_notification(
            db=db_session,
            notification_id=str(uuid.uuid4()),
            user_id=user_id,
            notification_type="email_test",
            channel=NotificationChannel.EMAIL,
            body="Email notification"
        )
        
        await crud.create_notification(
            db=db_session,
            notification_id=str(uuid.uuid4()),
            user_id=user_id,
            notification_type="sms_test",
            channel=NotificationChannel.SMS,
            body="SMS notification"
        )
        
        # Get all notifications
        all_notifications = await crud.get_user_notifications(
            db_session,
            user_id,
            limit=100
        )
        assert len(all_notifications) >= 2
        
        # Filter by channel
        email_notifications = await crud.get_user_notifications(
            db_session,
            user_id,
            channel=NotificationChannel.EMAIL,
            limit=100
        )
        assert all(n.channel == NotificationChannel.EMAIL for n in email_notifications)
    
    @pytest.mark.asyncio
    async def test_mark_notification_as_read(self, db_session):
        """Test marking notification as read updates timestamp"""
        notification_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        # Create notification
        notification = await crud.create_notification(
            db=db_session,
            notification_id=notification_id,
            user_id=user_id,
            notification_type="test",
            channel=NotificationChannel.EMAIL,
            body="Test body"
        )
        
        assert notification.read_at is None
        
        # Mark as read
        updated = await crud.mark_notification_as_read(db_session, notification_id)
        
        assert updated.read_at is not None
        assert isinstance(updated.read_at, datetime)
    
    @pytest.mark.asyncio
    async def test_get_unread_count(self, db_session):
        """Test getting unread notification count"""
        user_id = str(uuid.uuid4())
        
        # Create unread IN_APP notifications (get_unread_count filters by IN_APP)
        for i in range(3):
            await crud.create_notification(
                db=db_session,
                notification_id=str(uuid.uuid4()),
                user_id=user_id,
                notification_type="test",
                channel=NotificationChannel.IN_APP,
                body=f"Notification {i}"
            )
        
        # Get unread count
        count = await crud.get_unread_count(db_session, user_id)
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_notification_stats(self, db_session):
        """Test getting notification statistics"""
        user_id = str(uuid.uuid4())
        
        # Create notifications with different statuses
        notif1_id = str(uuid.uuid4())
        await crud.create_notification(
            db=db_session,
            notification_id=notif1_id,
            user_id=user_id,
            notification_type="test",
            channel=NotificationChannel.EMAIL,
            body="Test 1"
        )
        
        # Update one to SENT
        await crud.update_notification_status(
            db_session,
            notif1_id,
            NotificationStatus.SENT
        )
        
        # Get stats
        stats = await crud.get_notification_stats(db_session)
        
        assert stats["total"] >= 1
        assert isinstance(stats["by_status"], dict)
        assert isinstance(stats["by_channel"], dict)


# ============================================================================
# END-TO-END FLOW TESTS
# ============================================================================

class TestEndToEndFlows:
    """Test complete notification journeys"""
    
    @pytest.mark.asyncio
    async def test_complete_notification_lifecycle(self, client, test_user_id, db_session):
        """Test: create notification -> check notifications -> mark as read"""
        # 1. Create notification directly in database
        notification_id = str(uuid.uuid4())
        notification = await crud.create_notification(
            db=db_session,
            notification_id=notification_id,
            user_id=test_user_id,
            notification_type="lifecycle_test",
            channel=NotificationChannel.IN_APP,
            body="Testing complete lifecycle"
        )
        
        # 2. Check unread count
        unread_response = await client.get(
            "/notifications/unread",
            headers={"x-user-id": test_user_id}
        )
        assert unread_response.status_code == 200
        assert unread_response.json()["unread_count"] >= 1
        
        # 3. Get my notifications
        list_response = await client.get(
            "/notifications/my",
            headers={"x-user-id": test_user_id}
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] >= 1
        
        # 4. Mark as read
        read_response = await client.post(f"/notifications/{notification_id}/read")
        assert read_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_multi_channel_notifications(self, client, test_user_id, db_session):
        """Test creating notifications through different channels"""
        # Create email notification
        await crud.create_notification(
            db=db_session,
            notification_id=str(uuid.uuid4()),
            user_id=test_user_id,
            notification_type="email_test",
            channel=NotificationChannel.EMAIL,
            body="Email test"
        )
        
        # Create SMS notification
        await crud.create_notification(
            db=db_session,
            notification_id=str(uuid.uuid4()),
            user_id=test_user_id,
            notification_type="sms_test",
            channel=NotificationChannel.SMS,
            body="SMS test"
        )
        
        # Create IN_APP notification
        await crud.create_notification(
            db=db_session,
            notification_id=str(uuid.uuid4()),
            user_id=test_user_id,
            notification_type="in_app_test",
            channel=NotificationChannel.IN_APP,
            body="In-app test"
        )
        
        # Check notifications list
        list_response = await client.get(
            "/notifications/my",
            headers={"x-user-id": test_user_id}
        )
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["total"] >= 3
    
    @pytest.mark.asyncio
    async def test_bulk_mark_as_read_flow(self, client, db_session, test_user_id):
        """Test marking multiple notifications as read"""
        # Create multiple IN_APP notifications (for unread count tracking)
        for i in range(5):
            await crud.create_notification(
                db=db_session,
                notification_id=str(uuid.uuid4()),
                user_id=test_user_id,
                notification_type="test",
                channel=NotificationChannel.IN_APP,
                body=f"Test notification {i}"
            )
        
        # Check unread count
        unread_before = await client.get(
            "/notifications/unread",
            headers={"x-user-id": test_user_id}
        )
        assert unread_before.json()["unread_count"] >= 5
        
        # Mark all as read
        mark_all_response = await client.post(
            "/notifications/read-all",
            headers={"x-user-id": test_user_id}
        )
        assert mark_all_response.status_code == 200
        assert mark_all_response.json()["marked_read"] >= 5
        
        # Check unread count is now 0
        unread_after = await client.get(
            "/notifications/unread",
            headers={"x-user-id": test_user_id}
        )
        assert unread_after.json()["unread_count"] == 0
