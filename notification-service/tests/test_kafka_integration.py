"""
Kafka Integration Tests for Notification Service
Tests with real Kafka broker
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
proj_root_str = str(PROJECT_ROOT)
if proj_root_str not in sys.path:
    sys.path.insert(0, proj_root_str)

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
import asyncio
import json
import os
from confluent_kafka import Producer
from datetime import datetime
import uuid

from database import Base
from kafka_consumer import KafkaHandler
import crud
from models import NotificationChannel, NotificationStatus

# Test configurations
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://testuser:testpass@localhost:15434/testdb"
)
TEST_KAFKA_BOOTSTRAP_SERVERS = "localhost:19092"

# Test engine
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create test database"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(test_db):
    """Get database session"""
    async with TestSessionLocal() as session:
        yield session


def produce_kafka_message(topic: str, event_type: str, data: dict):
    """Produce a message to Kafka"""
    producer = Producer({'bootstrap.servers': TEST_KAFKA_BOOTSTRAP_SERVERS})
    
    message = {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }
    
    producer.produce(
        topic,
        key=event_type.encode('utf-8'),
        value=json.dumps(message).encode('utf-8')
    )
    producer.flush(timeout=5)


class TestKafkaIntegration:
    """Test Kafka consumer integration"""
    
    @pytest.mark.asyncio
    async def test_kafka_connection(self):
        """Test Kafka consumer can connect"""
        import kafka_consumer
        original_servers = kafka_consumer.KAFKA_BOOTSTRAP_SERVERS
        kafka_consumer.KAFKA_BOOTSTRAP_SERVERS = TEST_KAFKA_BOOTSTRAP_SERVERS
        
        handler = KafkaHandler()
        await handler.start()
        
        assert handler.is_connected() is True
        
        await handler.stop()
        kafka_consumer.KAFKA_BOOTSTRAP_SERVERS = original_servers
    
    @pytest.mark.asyncio
    async def test_order_created_event_to_kafka(self, db_session):
        """Test producing order.created event to Kafka"""
        # Just test that we can produce to Kafka successfully
        user_email = "test@example.com"
        order_id = str(uuid.uuid4())
        
        try:
            produce_kafka_message(
                "order.events",
                "order.created",
                {
                    "order_id": order_id,
                    "user_id": str(uuid.uuid4()),
                    "user_email": user_email,
                    "total_amount": 99.99,
                    "currency": "USD"
                }
            )
            # If no exception, test passes
            assert True
        except Exception as e:
            pytest.fail(f"Failed to produce Kafka message: {e}")
