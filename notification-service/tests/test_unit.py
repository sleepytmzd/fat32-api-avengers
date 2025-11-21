"""
Unit Tests for Notification Service
Tests CRUD operations, endpoints, Kafka handler, and models with mocking
"""
import sys
from pathlib import Path
# Add parent folder (project root) to sys.path so local modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
proj_root_str = str(PROJECT_ROOT)
if proj_root_str not in sys.path:
    sys.path.insert(0, proj_root_str)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid
import json
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Import models and functions to test
from models import Notification, NotificationStatus, NotificationChannel
from crud import (
    create_notification,
    get_notification_by_id,
    get_user_notifications,
    get_unread_notifications,
    get_all_notifications,
    update_notification_status,
    mark_notification_as_read,
    mark_all_as_read,
    get_notification_stats,
    get_unread_count
)
from config import Settings
from main import app, EmailNotification, SMSNotification, PushNotification

# Test client
client = TestClient(app)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_notification_id():
    """Generate a sample notification ID"""
    return f"notif-{uuid.uuid4()}"


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID"""
    return f"user-{uuid.uuid4()}"


@pytest.fixture
def sample_notification(sample_notification_id, sample_user_id):
    """Create a sample notification object"""
    return Notification(
        id=sample_notification_id,
        user_id=sample_user_id,
        user_email="test@example.com",
        notification_type="order_confirmation",
        channel=NotificationChannel.EMAIL,
        status=NotificationStatus.PENDING,
        title="Order Confirmation",
        subject="Your Order #12345",
        body="Your order has been confirmed",
        html="<p>Your order has been confirmed</p>",
        data={"order_id": "12345"},
        created_at=datetime.utcnow(),
        sent_at=None,
        read_at=None,
        retry_count="0"
    )


@pytest.fixture
def sample_email_notification():
    """Sample email notification data"""
    return EmailNotification(
        to="user@example.com",
        subject="Test Email",
        body="This is a test email",
        html="<p>This is a test email</p>",
        user_id="user-123"
    )


@pytest.fixture
def sample_sms_notification():
    """Sample SMS notification data"""
    return SMSNotification(
        to="+1234567890",
        message="This is a test SMS",
        user_id="user-123"
    )


@pytest.fixture
def sample_push_notification():
    """Sample push notification data"""
    return PushNotification(
        user_id="user-123",
        title="Test Push",
        body="This is a test push notification",
        data={"action": "view_order"}
    )


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_kafka_consumer():
    """Mock Kafka consumer"""
    consumer = MagicMock()
    consumer.subscribe = MagicMock()
    consumer.poll = MagicMock()
    consumer.commit = MagicMock()
    consumer.close = MagicMock()
    return consumer


@pytest.fixture
def mock_kafka_message():
    """Mock Kafka message"""
    message = MagicMock()
    message.error = MagicMock(return_value=None)
    message.value = MagicMock(return_value=b'{"event": "test"}')
    message.topic = MagicMock(return_value="test-topic")
    message.partition = MagicMock(return_value=0)
    message.offset = MagicMock(return_value=1)
    return message


# ============================================================================
# CRUD TESTS
# ============================================================================

class TestCRUD:
    """Test CRUD operations - success and failure scenarios"""
    
    @pytest.mark.asyncio
    async def test_create_notification_success(self, mock_db_session, sample_notification_id, sample_user_id):
        """Test successful notification creation"""
        notification = await create_notification(
            db=mock_db_session,
            notification_id=sample_notification_id,
            user_id=sample_user_id,
            notification_type="test",
            channel=NotificationChannel.EMAIL,
            body="Test notification"
        )
        
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        assert mock_db_session.refresh.called
    
    @pytest.mark.asyncio
    async def test_create_notification_failure(self, mock_db_session, sample_notification_id, sample_user_id):
        """Test notification creation handles database errors"""
        mock_db_session.commit.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            await create_notification(
                db=mock_db_session,
                notification_id=sample_notification_id,
                user_id=sample_user_id,
                notification_type="test",
                channel=NotificationChannel.EMAIL,
                body="Test notification"
            )
    
    @pytest.mark.asyncio
    async def test_get_notification_by_id_success(self, mock_db_session, sample_notification, sample_notification_id):
        """Test successfully getting notification by ID"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_notification
        mock_db_session.execute.return_value = mock_result
        
        notification = await get_notification_by_id(mock_db_session, sample_notification_id)
        
        assert notification == sample_notification
        assert mock_db_session.execute.called
    
    @pytest.mark.asyncio
    async def test_get_notification_by_id_not_found(self, mock_db_session, sample_notification_id):
        """Test getting notification by ID when not found"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        notification = await get_notification_by_id(mock_db_session, sample_notification_id)
        
        assert notification is None
    
    @pytest.mark.asyncio
    async def test_get_user_notifications_success(self, mock_db_session, sample_notification, sample_user_id):
        """Test successfully getting user notifications"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_notification]
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result
        
        notifications = await get_user_notifications(
            mock_db_session,
            sample_user_id,
            limit=100,
            offset=0
        )
        
        assert len(notifications) == 1
        assert notifications[0] == sample_notification
    
    @pytest.mark.asyncio
    async def test_get_user_notifications_with_filters(self, mock_db_session, sample_user_id):
        """Test getting user notifications with channel and status filters"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result
        
        notifications = await get_user_notifications(
            mock_db_session,
            sample_user_id,
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.SENT,
            limit=50
        )
        
        assert notifications == []
        assert mock_db_session.execute.called
    
    @pytest.mark.asyncio
    async def test_update_notification_status_to_sent_success(self, mock_db_session, sample_notification, sample_notification_id):
        """Test successfully updating notification status to SENT"""
        with patch('crud.get_notification_by_id', return_value=sample_notification):
            updated = await update_notification_status(
                mock_db_session,
                sample_notification_id,
                NotificationStatus.SENT
            )
            
            assert updated.status == NotificationStatus.SENT
            assert updated.sent_at is not None
            assert mock_db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_update_notification_status_to_failed(self, mock_db_session, sample_notification, sample_notification_id):
        """Test updating notification status to FAILED with error message"""
        with patch('crud.get_notification_by_id', return_value=sample_notification):
            updated = await update_notification_status(
                mock_db_session,
                sample_notification_id,
                NotificationStatus.FAILED,
                error_message="Connection timeout"
            )
            
            assert updated.status == NotificationStatus.FAILED
            assert updated.error_message == "Connection timeout"
    
    @pytest.mark.asyncio
    async def test_update_notification_status_to_retry(self, mock_db_session, sample_notification, sample_notification_id):
        """Test updating notification status to RETRY increments retry count"""
        with patch('crud.get_notification_by_id', return_value=sample_notification):
            updated = await update_notification_status(
                mock_db_session,
                sample_notification_id,
                NotificationStatus.RETRY
            )
            
            assert updated.status == NotificationStatus.RETRY
            assert updated.retry_count == "1"
    
    @pytest.mark.asyncio
    async def test_update_notification_status_not_found(self, mock_db_session, sample_notification_id):
        """Test updating notification status when notification doesn't exist"""
        with patch('crud.get_notification_by_id', return_value=None):
            updated = await update_notification_status(
                mock_db_session,
                sample_notification_id,
                NotificationStatus.SENT
            )
            
            assert updated is None
    
    @pytest.mark.asyncio
    async def test_mark_notification_as_read_success(self, mock_db_session, sample_notification, sample_notification_id):
        """Test successfully marking notification as read"""
        with patch('crud.get_notification_by_id', return_value=sample_notification):
            updated = await mark_notification_as_read(mock_db_session, sample_notification_id)
            
            assert updated.read_at is not None
            assert mock_db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_mark_notification_as_read_not_found(self, mock_db_session, sample_notification_id):
        """Test marking notification as read when not found"""
        with patch('crud.get_notification_by_id', return_value=None):
            updated = await mark_notification_as_read(mock_db_session, sample_notification_id)
            
            assert updated is None
    
    @pytest.mark.asyncio
    async def test_mark_all_as_read_success(self, mock_db_session, sample_user_id):
        """Test successfully marking all notifications as read"""
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_db_session.execute.return_value = mock_result
        
        count = await mark_all_as_read(mock_db_session, sample_user_id)
        
        assert count == 5
        assert mock_db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_get_notification_stats_success(self, mock_db_session):
        """Test successfully getting notification statistics"""
        mock_row1 = MagicMock()
        mock_row1.total = 10
        mock_row1.status = NotificationStatus.SENT
        mock_row1.channel = NotificationChannel.EMAIL
        
        mock_row2 = MagicMock()
        mock_row2.total = 5
        mock_row2.status = NotificationStatus.PENDING
        mock_row2.channel = NotificationChannel.SMS
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row1, mock_row2]
        mock_db_session.execute.return_value = mock_result
        
        stats = await get_notification_stats(mock_db_session)
        
        assert stats["total"] == 15
        assert stats["by_status"][NotificationStatus.SENT] == 10
        assert stats["by_status"][NotificationStatus.PENDING] == 5
    
    @pytest.mark.asyncio
    async def test_get_unread_count_success(self, mock_db_session, sample_user_id):
        """Test successfully getting unread notification count"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 7
        mock_db_session.execute.return_value = mock_result
        
        count = await get_unread_count(mock_db_session, sample_user_id)
        
        assert count == 7


# ============================================================================
# KAFKA HANDLER TESTS
# ============================================================================

class TestKafkaHandler:
    """Test Kafka consumer and event handlers - success and failure scenarios"""
    
    @pytest.mark.asyncio
    @patch('kafka_consumer.Consumer')
    async def test_kafka_handler_start_success(self, mock_consumer_class):
        """Test successful Kafka consumer connection"""
        from kafka_consumer import KafkaHandler
        
        mock_consumer_instance = MagicMock()
        mock_consumer_class.return_value = mock_consumer_instance
        
        handler = KafkaHandler()
        await handler.start()
        
        assert handler.consumer is not None
        assert handler._connected is True
        assert mock_consumer_instance.subscribe.called
    
    @pytest.mark.asyncio
    @patch('kafka_consumer.Consumer')
    async def test_kafka_handler_start_failure(self, mock_consumer_class):
        """Test Kafka consumer connection failure"""
        from kafka_consumer import KafkaHandler
        
        mock_consumer_class.side_effect = Exception("Connection failed")
        
        handler = KafkaHandler()
        await handler.start()
        
        assert handler._connected is False
    
    @pytest.mark.asyncio
    @patch('kafka_consumer.Consumer')
    async def test_kafka_handler_stop_success(self, mock_consumer_class):
        """Test successfully stopping Kafka consumer"""
        from kafka_consumer import KafkaHandler
        
        mock_consumer_instance = MagicMock()
        mock_consumer_class.return_value = mock_consumer_instance
        
        handler = KafkaHandler()
        await handler.start()
        await handler.stop()
        
        assert handler._running is False
        assert mock_consumer_instance.close.called
    
    @pytest.mark.asyncio
    @patch('main.send_email_async')
    async def test_handle_order_created_success(self, mock_send_email):
        """Test successfully processing order.created event"""
        from kafka_consumer import KafkaHandler
        
        handler = KafkaHandler()
        event_data = {
            "order_id": "order-123",
            "user_id": "user-456",
            "user_email": "user@example.com",
            "total_amount": 99.99,
            "currency": "USD"
        }
        
        await handler._handle_order_created(event_data, mock_send_email)
        
        assert mock_send_email.called
        call_args = mock_send_email.call_args
        assert "user@example.com" in str(call_args)
        assert "order-123" in str(call_args)
    
    @pytest.mark.asyncio
    @patch('main.send_email_async')
    async def test_handle_order_created_missing_email(self, mock_send_email):
        """Test processing order.created event with missing user email"""
        from kafka_consumer import KafkaHandler
        
        handler = KafkaHandler()
        event_data = {
            "order_id": "order-123",
            "user_id": "user-456",
            "total_amount": 99.99
            # Missing user_email
        }
        
        await handler._handle_order_created(event_data, mock_send_email)
        
        # Should not send email when email is missing
        assert not mock_send_email.called
    
    @pytest.mark.asyncio
    @patch('main.send_email_async')
    async def test_handle_order_cancelled_success(self, mock_send_email):
        """Test processing order.cancelled event"""
        from kafka_consumer import KafkaHandler
        
        handler = KafkaHandler()
        event_data = {
            "order_id": "order-123",
            "user_email": "user@example.com",
            "reason": "Customer request"
        }
        
        # Currently this handler only logs
        await handler._handle_order_cancelled(event_data, mock_send_email)
    
    @pytest.mark.asyncio
    @patch('main.send_email_async')
    async def test_handle_payment_completed_success(self, mock_send_email):
        """Test processing payment.completed event"""
        from kafka_consumer import KafkaHandler
        
        handler = KafkaHandler()
        event_data = {
            "payment_id": "pay-123",
            "order_id": "order-456",
            "amount": 149.99,
            "transaction_id": "txn-789"
        }
        
        # Currently this handler only logs
        await handler._handle_payment_completed(event_data, mock_send_email)
    
    @pytest.mark.asyncio
    @patch('main.send_email_async')
    async def test_handle_payment_failed_success(self, mock_send_email):
        """Test processing payment.failed event"""
        from kafka_consumer import KafkaHandler
        
        handler = KafkaHandler()
        event_data = {
            "payment_id": "pay-123",
            "order_id": "order-456",
            "reason": "Insufficient funds"
        }
        
        # Currently this handler only logs
        await handler._handle_payment_failed(event_data, mock_send_email)
    
    @pytest.mark.asyncio
    @patch('main.send_email_async')
    async def test_handle_payment_refunded_success(self, mock_send_email):
        """Test processing payment.refunded event"""
        from kafka_consumer import KafkaHandler
        
        handler = KafkaHandler()
        event_data = {
            "payment_id": "pay-123",
            "order_id": "order-456",
            "amount": 149.99,
            "reason": "Customer request"
        }
        
        # Currently this handler only logs
        await handler._handle_payment_refunded(event_data, mock_send_email)



