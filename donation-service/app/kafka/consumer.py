import json
import asyncio
import sys
import structlog
from typing import Optional
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from app.core.config import get_settings
from app.database.database import SessionLocal
from app.models.donation import DonationStatus
from app.schemas.donation import UpdateDonationRequest
from app.services.donation import DonationService

logger = structlog.get_logger(__name__)
settings = get_settings()


class KafkaConsumer:
    """Kafka consumer for payment events"""
    
    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.payment_events_topic = "payment.events"
        
    async def start(self):
        """Initialize and start Kafka consumer"""
        try:
            self.consumer = AIOKafkaConsumer(
                self.payment_events_topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id='donation-service',
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
            )
            await self.consumer.start()
            logger.info("Kafka consumer started", 
                       bootstrap_servers=self.bootstrap_servers,
                       topic=self.payment_events_topic)
            print(f"[KAFKA CONSUMER] Started - topic: {self.payment_events_topic}")
            sys.stdout.flush()
        except KafkaError as e:
            logger.error("Failed to start Kafka consumer", error=str(e))
            raise
            
    async def stop(self):
        """Stop Kafka consumer gracefully"""
        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error("Error stopping Kafka consumer", error=str(e))
    
    async def consume_events(self):
        """
        Consume payment events and update donation status
        """
        if not self.consumer:
            logger.error("Kafka consumer not initialized")
            print("[KAFKA CONSUMER] ✗ Consumer not initialized")
            sys.stdout.flush()
            return
            
        logger.info("Starting to consume payment events...")
        print("[KAFKA CONSUMER] 🔄 Listening for payment events...")
        sys.stdout.flush()
        
        try:
            async for message in self.consumer:
                try:
                    event = message.value
                    event_type = event.get("event_type")
                    
                    logger.info("Received payment event", event_type=event_type, event_data=event)
                    print(f"[KAFKA CONSUMER] 📥 Received: {event_type}")
                    sys.stdout.flush()
                    
                    if event_type == "payment.verified":
                        await self._handle_payment_verified(event)
                    
                    elif event_type == "payment.failed":
                        await self._handle_payment_failed(event)
                        
                except Exception as e:
                    logger.error("Error processing payment event", error=str(e), event_data=message.value)
                    
        except Exception as e:
            logger.error("Kafka consumer error", error_message=str(e))
    
    async def _handle_payment_verified(self, event: dict):
        """
        Handle payment.verified event
        Update donation status to CAPTURED
        """
        donation_id = event.get("donation_id")
        payment_id = event.get("payment_id")
        
        print(f"[KAFKA] 🔍 Processing payment.verified - donation_id: {donation_id}, payment_id: {payment_id}")
        sys.stdout.flush()
        
        if not donation_id:
            logger.warning("Missing donation_id in payment.verified event", event_data=event)
            print(f"[KAFKA] ⚠️  Missing donation_id in event")
            sys.stdout.flush()
            return
        
        try:
            # Convert donation_id to int
            donation_id_int = int(donation_id)
            
            # Update donation status in database
            print(f"[KAFKA] 💾 Updating donation {donation_id} to CAPTURED...")
            sys.stdout.flush()
            
            db = SessionLocal()
            try:
                update_data = UpdateDonationRequest(
                    status=DonationStatus.CAPTURED.value,
                    payment_id=payment_id
                )
                
                result = DonationService.update_donation_status(db, donation_id_int, update_data)
                
                if result:
                    logger.info(
                        "✅ Donation status updated to CAPTURED",
                        donation_id=donation_id,
                        payment_id=payment_id
                    )
                    print(f"[KAFKA] ✅ Updated donation {donation_id} to CAPTURED")
                    sys.stdout.flush()
                else:
                    logger.warning("Donation not found for status update", donation_id=donation_id)
                    print(f"[KAFKA] ⚠️  Donation {donation_id} not found")
                    sys.stdout.flush()
                    
            finally:
                db.close()
                
        except ValueError:
            logger.error("Invalid donation_id format", donation_id=donation_id)
        except Exception as e:
            logger.error(
                "Failed to update donation status",
                error=str(e),
                donation_id=donation_id
            )
    
    async def _handle_payment_failed(self, event: dict):
        """
        Handle payment.failed event
        Update donation status to FAILED
        """
        donation_id = event.get("donation_id")
        reason = event.get("reason", "Payment processing failed")
        
        print(f"[KAFKA] 🔍 Processing payment.failed - donation_id: {donation_id}, reason: {reason}")
        sys.stdout.flush()
        
        if not donation_id:
            logger.warning("Missing donation_id in payment.failed event", event_data=event)
            print(f"[KAFKA] ⚠️  Missing donation_id in event")
            sys.stdout.flush()
            return
        
        try:
            # Convert donation_id to int
            donation_id_int = int(donation_id)
            
            # Update donation status in database
            print(f"[KAFKA] 💾 Updating donation {donation_id} to FAILED...")
            sys.stdout.flush()
            
            db = SessionLocal()
            try:
                update_data = UpdateDonationRequest(
                    status=DonationStatus.FAILED.value,
                    payment_id=None
                )
                
                result = DonationService.update_donation_status(db, donation_id_int, update_data)
                
                if result:
                    logger.info(
                        "❌ Donation status updated to FAILED",
                        donation_id=donation_id,
                        reason=reason
                    )
                    print(f"[KAFKA] ❌ Updated donation {donation_id} to FAILED - {reason}")
                    sys.stdout.flush()
                else:
                    logger.warning("Donation not found for status update", donation_id=donation_id)
                    print(f"[KAFKA] ⚠️  Donation {donation_id} not found")
                    sys.stdout.flush()
                    
            finally:
                db.close()
                
        except ValueError:
            logger.error("Invalid donation_id format", donation_id=donation_id)
        except Exception as e:
            logger.error(
                "Failed to update donation status",
                error=str(e),
                donation_id=donation_id
            )


# Global consumer instance
kafka_consumer = KafkaConsumer()


async def get_kafka_consumer() -> KafkaConsumer:
    """Get Kafka consumer instance"""
    return kafka_consumer
