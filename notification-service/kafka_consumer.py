"""
Notification Service - Kafka Consumer (Confluent Kafka)
"""
import json
import logging
import os
from confluent_kafka import Consumer, KafkaError
import asyncio
from functools import partial
from datetime import datetime

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
PAYMENT_EVENTS_TOPIC = "payment.events"
DONATION_EVENTS_TOPIC = "donation_created"

class KafkaHandler:
    """Kafka consumer for notification events using Confluent Kafka"""
    
    def __init__(self):
        self.consumer = None
        self._connected = False
        self._running = False
    
    async def start(self):
        """Start Kafka consumer"""
        try:
            config = {
                'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
                'group.id': 'notification-service',
                'auto.offset.reset': 'latest',
                'enable.auto.commit': True
            }
            
            self.consumer = Consumer(config)
            self.consumer.subscribe([PAYMENT_EVENTS_TOPIC, DONATION_EVENTS_TOPIC])
            
            self._connected = True
            self._running = True
            logger.info(f"Kafka consumer started, connected to {KAFKA_BOOTSTRAP_SERVERS}")
            logger.info(f"Subscribed to topics: {PAYMENT_EVENTS_TOPIC}, {DONATION_EVENTS_TOPIC}")
        
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            self._connected = False
    
    async def stop(self):
        """Stop Kafka consumer"""
        self._running = False
        
        if self.consumer:
            self.consumer.close()
        
        self._connected = False
        logger.info("Kafka consumer stopped")
    
    def is_connected(self) -> bool:
        """Check if connected to Kafka"""
        return self._connected
    
    async def consume_events(self):
        """Consume events from Kafka"""
        logger.info("Starting Kafka event consumer...")
        
        # Import here to avoid circular dependency
        from main import send_email_async
        
        try:
            while self._running:
                # Poll for messages (non-blocking with timeout)
                msg = await asyncio.get_event_loop().run_in_executor(
                    None,
                    partial(self.consumer.poll, timeout=1.0)
                )
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue
                
                try:
                    # Decode message
                    event = json.loads(msg.value().decode('utf-8'))
                    event_type = event.get("event_type")
                    
                    logger.info(f"Received Kafka event: {event_type}")
                    
                    if event_type == "payment.completed":
                        await self._handle_payment_completed(event, send_email_async)
                    
                    elif event_type == "payment.failed":
                        await self._handle_payment_failed(event, send_email_async)
                    
                    elif event_type == "payment.refunded":
                        await self._handle_payment_refunded(event, send_email_async)
                    
                    elif event_type == "payment.verified":
                        await self._handle_payment_verified(event)
                    
                    elif event_type == "donation_created":
                        await self._handle_donation_created(event)
                
                except Exception as e:
                    logger.error(f"Error processing Kafka event: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Kafka consumer error: {e}", exc_info=True)
    
    async def _handle_payment_completed(self, event: dict, send_email_func):
        """Handle payment.completed event - Send payment confirmation"""
        order_id = event.get("order_id")
        payment_id = event.get("payment_id")
        amount = event.get("amount")
        transaction_id = event.get("transaction_id")
        
        logger.info(f"Payment completed for order {order_id}: {transaction_id}")
        logger.info(f"Payment confirmation notification ready for order {order_id}")
    
    async def _handle_payment_failed(self, event: dict, send_email_func):
        """Handle payment.failed event - Send payment failure notification"""
        from database import AsyncSessionLocal
        from crud import create_notification
        from models import NotificationChannel, NotificationStatus
        
        donation_id = event.get("donation_id")
        user_id = event.get("user_id")
        campaign_id = event.get("campaign_id")
        amount = event.get("amount")
        reason = event.get("reason", "Unknown error")
        
        reference_id = donation_id
        reference_type = "donation"
        
        logger.warning(f"Payment failed for {reference_type} {reference_id}: {reason}")
        
        if not user_id or not reference_id:
            logger.warning(f"Missing required fields in payment.failed event: {event}")
            return
        
        # Create notification ID
        notification_id = f"notif-payment-failed-{reference_id}-{datetime.utcnow().timestamp()}"
        
        # Create notification body
        body = f"❌ Payment Failed\n\n"
        body += f"Your payment of ${amount:.2f} could not be processed.\n\n"
        body += f"Reason: {reason}\n\n"
        if campaign_id:
            body += f"Campaign ID: {campaign_id}\n"
        body += f"Donation ID: {donation_id}\n"
        body += f"\nPlease check your account balance and try again."
        
        # Insert notification into database
        async with AsyncSessionLocal() as db:
            try:
                notification = await create_notification(
                    db=db,
                    notification_id=notification_id,
                    user_id=user_id,
                    notification_type="payment_failed",
                    channel=NotificationChannel.IN_APP,
                    body=body,
                    status=NotificationStatus.PENDING,
                    data={
                        "donation_id": donation_id,
                        "campaign_id": campaign_id,
                        "amount": amount,
                        "reason": reason
                    }
                )
                
                logger.info(f"✅ Created payment failure notification {notification_id} for {reference_type} {reference_id}")
            
            except Exception as e:
                logger.error(f"Failed to create payment failure notification: {e}", exc_info=True)
    
    async def _handle_payment_refunded(self, event: dict, send_email_func):
        """Handle payment.refunded event - Send refund confirmation"""
        payment_id = event.get("payment_id")
        order_id = event.get("order_id")
        amount = event.get("amount")
        reason = event.get("reason")
        
        logger.info(f"Payment {payment_id} refunded for order {order_id}")
        logger.info(f"Refund confirmation notification ready for order {order_id}")
    
    async def _handle_payment_verified(self, event: dict):
        """Handle payment.verified event - Insert payment verification notification"""
        from database import AsyncSessionLocal
        from crud import create_notification
        from models import NotificationChannel, NotificationStatus
        
        payment_id = event.get("payment_id")
        donation_id = event.get("donation_id")
        user_id = event.get("user_id")
        campaign_id = event.get("campaign_id")
        amount = event.get("amount")
        transaction_id = event.get("transaction_id")
        
        if not user_id or not payment_id:
            logger.warning(f"Missing required fields in payment.verified event: {event}")
            return
        
        # Create notification ID
        notification_id = f"notif-payment-verified-{payment_id}-{datetime.utcnow().timestamp()}"
        
        # Create notification body
        body = f"✅ Payment Verified!\n\n"
        body += f"Your donation payment of ${amount:.2f} has been successfully verified and processed.\n\n"
        body += f"Campaign ID: {campaign_id}\n"
        body += f"Donation ID: {donation_id}\n"
        body += f"Transaction ID: {transaction_id}\n"
        body += f"Payment ID: {payment_id}\n\n"
        body += "Thank you for your generous contribution!"
        
        # Insert notification into database
        async with AsyncSessionLocal() as db:
            try:
                notification = await create_notification(
                    db=db,
                    notification_id=notification_id,
                    user_id=user_id,
                    notification_type="payment_verified",
                    channel=NotificationChannel.IN_APP,
                    body=body,
                    status=NotificationStatus.PENDING,
                    data={
                        "payment_id": payment_id,
                        "donation_id": donation_id,
                        "campaign_id": campaign_id,
                        "amount": amount,
                        "transaction_id": transaction_id
                    }
                )
                
                logger.info(f"✅ Created payment verification notification {notification_id} for payment {payment_id}")
                logger.info(f"📧 Notification saved - User: {user_id}, Donation: {donation_id}")
            
            except Exception as e:
                logger.error(f"Failed to create payment verification notification: {e}", exc_info=True)
    
    async def _handle_donation_created(self, event: dict):
        """Handle donation_created event - Insert notification into database"""
        from database import AsyncSessionLocal
        from crud import create_notification
        from models import NotificationChannel, NotificationStatus
        
        donation_id = event.get("donation_id")
        user_id = event.get("user_id")
        campaign_id = event.get("campaign_id")
        amount = event.get("amount")
        status = event.get("status")
        payment_method = event.get("payment_method")
        is_anonymous = event.get("is_anonymous", False)
        message = event.get("message", "")
        timestamp = event.get("timestamp")
        
        if not user_id or not donation_id:
            logger.warning(f"Missing required fields in donation event: {event}")
            return
        
        # Create notification ID
        notification_id = f"notif-donation-{donation_id}-{datetime.utcnow().timestamp()}"
        
        # Create notification body
        body = f"Thank you for your donation of ${amount:.2f} to campaign #{campaign_id}!"
        if message:
            body += f"\n\nYour message: {message}"
        body += f"\n\nDonation ID: {donation_id}"
        body += f"\nPayment Method: {payment_method}"
        body += f"\nStatus: {status}"
        
        # Insert notification into database
        async with AsyncSessionLocal() as db:
            try:
                notification = await create_notification(
                    db=db,
                    notification_id=notification_id,
                    user_id=user_id,
                    notification_type="donation_created",
                    channel=NotificationChannel.IN_APP,
                    body=body,
                    status=NotificationStatus.PENDING,
                    data={
                        "donation_id": donation_id,
                        "campaign_id": campaign_id,
                        "amount": amount,
                        "payment_method": payment_method,
                        "is_anonymous": is_anonymous,
                        "timestamp": timestamp
                    }
                )
                
                logger.info(f"✅ Created notification {notification_id} for donation {donation_id}")
                logger.info(f"📬 Notification saved to database - User: {user_id}, Amount: ${amount}")
            
            except Exception as e:
                logger.error(f"Failed to create notification for donation {donation_id}: {e}", exc_info=True)
