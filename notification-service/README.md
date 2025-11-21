# Notification Service - Database Integration

## Overview
The Notification Service now includes PostgreSQL database integration using SQLAlchemy with asyncpg for storing all user notifications persistently.

## What's New

### Database Schema
- **Notification Table**: Stores all notifications with full metadata
  - User-specific notifications (user_id indexed)
  - Multiple channels: EMAIL, SMS, PUSH, IN_APP
  - Status tracking: PENDING, SENT, FAILED, RETRY
  - Read status for in-app notifications
  - Error logging for failed notifications
  - Retry counter for failed deliveries

### New Files
1. **models.py** - SQLAlchemy models
2. **database.py** - Database connection and session management
3. **crud.py** - Database operations (CRUD)
4. **config.py** - Configuration management

### New API Endpoints

#### User Notification Endpoints
```bash
# Get all notifications for a user
GET /notifications/user/{user_id}
  ?limit=100&offset=0&channel=email&status=sent

# Get unread notifications
GET /notifications/user/{user_id}/unread?limit=100

# Mark notification as read
POST /notifications/{notification_id}/read

# Mark all notifications as read for a user
POST /notifications/user/{user_id}/read-all
```

#### Admin/Monitoring Endpoints
```bash
# Get notification log (supports pagination)
GET /notifications/log?limit=100&offset=0

# Get statistics (optionally filtered by user)
GET /notifications/stats?user_id={user_id}
```

### Database Configuration

**Environment Variable:**
```bash
DATABASE_URL=postgresql+asyncpg://notification_user:notification_pass@localhost:5432/notification_db
```

**Docker Compose:**
The notification service now has its own PostgreSQL instance:
- Container: `postgres-notification-demo`
- Port: 5434 (host) → 5432 (container)
- Database: `notification_db`
- User: `notification_user`
- Password: `notification_pass`

## Features

### 1. Persistent Storage
- All notifications are now saved to the database
- No data loss on service restart
- Historical notification tracking

### 2. User-Centric Design
- Query notifications by user_id
- Filter by channel (email/sms/push/in-app)
- Filter by status (pending/sent/failed)
- Track read/unread status for in-app notifications

### 3. Statistics & Monitoring
- Total notifications sent
- Success/failure rates
- Breakdown by channel
- Breakdown by status
- User-specific statistics

### 4. Retry Mechanism
- Tracks retry count for failed notifications
- Status transitions: PENDING → SENT/FAILED → RETRY

## Usage Examples

### Send Email Notification
```python
POST /notifications/email
{
  "to": "user@example.com",
  "subject": "Welcome!",
  "body": "Thank you for signing up."
}
```
→ Automatically saved to database with PENDING status
→ Marked as SENT after delivery

### Get User's Notifications
```python
GET /notifications/user/user123?limit=50&channel=email&status=sent

Response:
{
  "user_id": "user123",
  "total": 15,
  "notifications": [
    {
      "id": "notif-123",
      "type": "order_confirmation",
      "channel": "email",
      "status": "sent",
      "subject": "Order Confirmation",
      "body": "Your order has been confirmed",
      "created_at": "2025-11-21T10:30:00",
      "sent_at": "2025-11-21T10:30:01",
      "read_at": null
    }
  ]
}
```

### Get Unread Count
```python
GET /notifications/user/user123/unread

Response:
{
  "user_id": "user123",
  "unread_count": 5,
  "notifications": [...]
}
```

### Mark as Read
```python
POST /notifications/notif-123/read

Response:
{
  "success": true,
  "notification_id": "notif-123",
  "read_at": "2025-11-21T11:00:00"
}
```

## Database Schema

```sql
CREATE TABLE notifications (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    user_email VARCHAR,
    notification_type VARCHAR NOT NULL,
    channel VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    title VARCHAR,
    subject VARCHAR,
    body TEXT NOT NULL,
    html TEXT,
    data JSON,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL,
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    retry_count VARCHAR DEFAULT '0'
);

CREATE INDEX idx_user_id ON notifications(user_id);
CREATE INDEX idx_notification_id ON notifications(id);
```

## Running the Service

### With Docker Compose
```bash
docker-compose up notification-service postgres-notification
```

### Local Development
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variable:
```bash
export DATABASE_URL="postgresql+asyncpg://notification_user:notification_pass@localhost:5434/notification_db"
```

3. Run the service:
```bash
python main.py
```

The database tables will be created automatically on first startup.

## Integration with Other Services

Other services can now:
1. Send notifications via API
2. Query notification history for users
3. Check delivery status
4. Get notification statistics

Example from another service:
```python
# Send notification
response = await http_client.post(
    "http://notification-service:8005/notifications/email",
    json={
        "to": user_email,
        "subject": "Payment Successful",
        "body": f"Your payment of ${amount} was successful"
    }
)

# Check user's notifications
notifications = await http_client.get(
    f"http://notification-service:8005/notifications/user/{user_id}"
)
```

## Monitoring

- Health check: `GET /health`
- Metrics: `GET /metrics` (Prometheus format)
- Statistics: `GET /notifications/stats`

## Future Enhancements

1. **Notification Templates**: Predefined templates for common notifications
2. **Scheduling**: Schedule notifications for future delivery
3. **Batch Operations**: Send notifications to multiple users
4. **Webhook Support**: Callbacks for notification status updates
5. **Priority Queue**: Priority-based notification delivery
6. **User Preferences**: Allow users to configure notification preferences
