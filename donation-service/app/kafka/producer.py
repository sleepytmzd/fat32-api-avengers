import json
import asyncio
import sys
from typing import Optional
import structlog
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class KafkaProducer:
    """Kafka producer for publishing events"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        
    async def start(self):
        """Initialize and start Kafka producer"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type='gzip',
                acks='all',  # Wait for all in-sync replicas
                retry_backoff_ms=500,
                request_timeout_ms=30000,
            )
            await self.producer.start()
            logger.info("Kafka producer started", bootstrap_servers=self.bootstrap_servers)
            print(f"[KAFKA] Producer started - bootstrap_servers: {self.bootstrap_servers}")
            sys.stdout.flush()
        except KafkaError as e:
            logger.error("Failed to start Kafka producer", error=str(e))
            raise
            
    async def stop(self):
        """Stop Kafka producer gracefully"""
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.error("Error stopping Kafka producer", error=str(e))
    
    async def publish_donation_created(self, donation_data: dict):
        """
        Publish donation_created event to Kafka for notification service
        
        Args:
            donation_data: Dictionary containing donation information
        """
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return
            
        try:
            event = {
                "event_type": "donation_created",
                "donation_id": donation_data.get("id"),
                "user_id": donation_data.get("user_id"),
                "campaign_id": donation_data.get("campaign_id"),
                "amount": float(donation_data.get("amount", 0)),
                "status": donation_data.get("status", "initiated"),
                "payment_method": donation_data.get("payment_method"),
                "is_anonymous": donation_data.get("is_anonymous", False),
                "message": donation_data.get("message"),
                "timestamp": donation_data.get("created_at")
            }
            
            # Send to Kafka
            await self.producer.send_and_wait(
                settings.kafka_topic_donation_created,
                value=event
            )
            
            print(f"[KAFKA] ✓ Published donation_created event - donation_id: {event['donation_id']}, topic: {settings.kafka_topic_donation_created}")
            sys.stdout.flush()
            
            logger.info(
                "Published donation_created event",
                donation_id=event["donation_id"],
                topic=settings.kafka_topic_donation_created
            )
            sys.stdout.flush()
            
        except KafkaError as e:
            print(f"[KAFKA] ✗ Failed to publish - donation_id: {donation_data.get('id')}, error: {e}")
            sys.stdout.flush()
            logger.error(
                "Failed to publish donation_created event",
                donation_id=donation_data.get("id"),
                error=str(e)
            )
        except Exception as e:
            print(f"[KAFKA] ✗ Unexpected error - donation_id: {donation_data.get('id')}, error: {e}")
            sys.stdout.flush()
            logger.error(
                "Unexpected error publishing to Kafka",
                donation_id=donation_data.get("id"),
                error=str(e)
            )
                
    async def publish_order_created(self, order_data: dict):
        """
        Publish order_created event to Kafka
        
        Args:
            order_data: Dictionary containing order information
        """
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return
            
        try:
            event = {
                "event_type": "order_created",
                "order_id": str(order_data.get("id")),
                "user_id": str(order_data.get("user_id")),
                "items": order_data.get("items", []),
                "total_amount": float(order_data.get("total_amount", 0)),
                "status": order_data.get("status", "pending"),
                "timestamp": order_data.get("created_at")
            }
            
            # Send to Kafka
            await self.producer.send_and_wait(
                settings.kafka_topic_order_created,
                value=event
            )
            
            print(f"[KAFKA] ✓ Published order_created event - order_id: {event['order_id']}, topic: {settings.kafka_topic_order_created}")
            sys.stdout.flush()
            
            logger.info(
                "Published order_created event",
                order_id=event["order_id"],
                topic=settings.kafka_topic_order_created
            )
            sys.stdout.flush()
            
        except KafkaError as e:
            print(f"[KAFKA] ✗ Failed to publish - order_id: {order_data.get('id')}, error: {e}")
            sys.stdout.flush()
            logger.error(
                "Failed to publish order_created event",
                order_id=order_data.get("id"),
                error=str(e)
            )
        except Exception as e:
            print(f"[KAFKA] ✗ Unexpected error - order_id: {order_data.get('id')}, error: {e}")
            sys.stdout.flush()
            logger.error(
                "Unexpected error publishing to Kafka",
                order_id=order_data.get("id"),
                error=str(e)
            )


# Global producer instance
kafka_producer = KafkaProducer()


async def get_kafka_producer() -> KafkaProducer:
    """Get Kafka producer instance"""
    return kafka_producer
