"""
Payment Service - Kafka Consumer and Producer (Confluent Kafka)
"""
import json
import logging
import os
from confluent_kafka import Consumer, Producer, KafkaError
from decimal import Decimal
import asyncio
from functools import partial
import httpx

from database import AsyncSessionLocal
from models import PaymentCreate, PaymentStatus, PaymentMethod
from crud import create_payment, update_payment_status, process_refund

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
BANKING_SERVICE_URL = os.getenv("BANKING_SERVICE_URL", "http://banking-service:8004")
ORDER_EVENTS_TOPIC = "order.events"
PAYMENT_EVENTS_TOPIC = "payment.events"
DONATION_EVENTS_TOPIC = "donation_created"
BANKING_SERVICE_URL = os.getenv("BANKING_SERVICE_URL", "http://banking-service:8006")

class KafkaHandler:
    """Kafka consumer and producer for Payment Service using Confluent Kafka"""
    
    def __init__(self):
        self.consumer = None
        self.producer = None
        self._connected = False
        self._running = False
    
    async def start(self):
        """Start Kafka consumer and producer"""
        try:
            # Consumer configuration
            consumer_config = {
                'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
                'group.id': 'payment-service',
                'auto.offset.reset': 'latest',
                'enable.auto.commit': True
            }
            
            # Producer configuration
            producer_config = {
                'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
                'client.id': 'payment-service',
                'compression.type': 'gzip'
            }
            
            self.consumer = Consumer(consumer_config)
            self.consumer.subscribe([ORDER_EVENTS_TOPIC, DONATION_EVENTS_TOPIC])
            
            self.producer = Producer(producer_config)
            
            self._connected = True
            self._running = True
            logger.info(f"Kafka handler started, connected to {KAFKA_BOOTSTRAP_SERVERS}")
            
            # Produce bootstrap JSON message
            bootstrap_event = {
                "event_type": "bootstrap",
                "message": "initial payment.events topic creation"
            }
            value_bytes = json.dumps(bootstrap_event).encode("utf-8")
            key_bytes = "setup".encode("utf-8")

            await asyncio.get_event_loop().run_in_executor(
                None,
                partial(
                    self.producer.produce,
                    PAYMENT_EVENTS_TOPIC,
                    value=value_bytes,
                    key=key_bytes,
                    callback=self._delivery_callback
                )
            )
            self.producer.poll(0)
            self.producer.flush()
            logger.info("Kafka producer bootstrap message sent")
        
        except Exception as e:
            logger.error(f"Failed to start Kafka handler: {e}")
            self._connected = False
    
    async def stop(self):
        """Stop Kafka consumer and producer"""
        self._running = False
        
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.flush()
        
        self._connected = False
        logger.info("Kafka handler stopped")
    
    def is_connected(self) -> bool:
        """Check if connected to Kafka"""
        return self._connected
    
    def _delivery_callback(self, err, msg):
        """Callback for producer delivery reports"""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()}")
    
    async def consume_events(self):
        """Consume events from Kafka"""
        logger.info("Starting Kafka event consumer...")
        
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
                    
                    if event_type == "order.created":
                        await self._handle_order_created(event)
                    
                    elif event_type == "order.cancelled":
                        await self._handle_order_cancelled(event)
                    
                    elif event_type == "donation_created":
                        await self._handle_donation_created(event)
                
                except Exception as e:
                    logger.error(f"Error processing Kafka event: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Kafka consumer error: {e}", exc_info=True)
    
    async def _handle_order_created(self, event: dict):
        """
        Handle order.created event
        Create payment and process it
        """
        order_id = event.get("order_id")
        user_id = event.get("user_id")
        amount = Decimal(str(event.get("total_amount")))
        currency = event.get("currency", "USD")
        payment_method = event.get("payment_method", "card")
        
        logger.info(f"Processing payment for order {order_id}")
        
        async with AsyncSessionLocal() as db:
            try:
                # Create payment record
                payment_data = PaymentCreate(
                    user_id=user_id,
                    order_id=order_id,
                    amount=amount,
                    currency=currency,
                    payment_method=PaymentMethod(payment_method),
                    status=PaymentStatus.PENDING
                )
                
                payment = await create_payment(db, payment_data)
                payment_id = str(payment.id)
                
                # Call banking service to debit account
                success = False
                failure_reason = None
                
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.post(
                            f"{BANKING_SERVICE_URL}/internal/debit",
                            json={
                                "user_id": user_id,
                                "amount": float(amount)
                            }
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            success = result.get("success", False)
                            if not success:
                                failure_reason = result.get("message", "Debit failed")
                        else:
                            failure_reason = f"Banking service error: {response.status_code}"
                            logger.error(f"Banking service returned {response.status_code}: {response.text}")
                
                except httpx.RequestError as e:
                    failure_reason = f"Banking service unavailable: {str(e)}"
                    logger.error(f"Failed to reach banking service: {e}")
                
                except Exception as e:
                    failure_reason = f"Banking service error: {str(e)}"
                    logger.error(f"Error calling banking service: {e}", exc_info=True)
                
                if success:
                    # Payment successful
                    payment = await update_payment_status(
                        db,
                        payment_id,
                        PaymentStatus.COMPLETED
                    )
                    
                    payment.transaction_id = f"TXN-{payment.id}"
                    await db.commit()
                    
                    logger.info(f"Payment {payment_id} completed successfully")
                    
                    # Publish payment.completed event
                    await self._publish_event({
                        "event_type": "payment.completed",
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "user_id": user_id,
                        "amount": float(amount),
                        "transaction_id": payment.transaction_id,
                        "timestamp": payment.completed_at.isoformat() if payment.completed_at else None
                    })
                
                else:
                    # Payment failed
                    payment = await update_payment_status(
                        db,
                        payment_id,
                        PaymentStatus.FAILED
                    )
                    
                    payment.failure_reason = failure_reason or "Payment declined"
                    await db.commit()
                    
                    logger.warning(f"Payment {payment_id} failed: {payment.failure_reason}")
                    
                    # Publish payment.failed event
                    await self._publish_event({
                        "event_type": "payment.failed",
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "user_id": user_id,
                        "reason": payment.failure_reason,
                        "timestamp": payment.updated_at.isoformat() if payment.updated_at else None
                    })
            
            except Exception as e:
                logger.error(f"Error processing payment for order {order_id}: {e}", exc_info=True)
    
    async def _handle_order_cancelled(self, event: dict):
        """
        Handle order.cancelled event
        Refund payment if exists
        """
        order_id = event.get("order_id")
        payment_id = event.get("payment_id")
        
        if not payment_id:
            logger.info(f"No payment to refund for cancelled order {order_id}")
            return
        
        logger.info(f"Processing refund for cancelled order {order_id}")
        
        async with AsyncSessionLocal() as db:
            try:
                payment = await process_refund(
                    db,
                    payment_id,
                    reason="Order cancelled"
                )
                
                if payment:
                    logger.info(f"Refunded payment {payment_id}")
                    
                    # Publish payment.refunded event
                    await self._publish_event({
                        "event_type": "payment.refunded",
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "user_id": str(payment.user_id),
                        "amount": float(payment.amount),
                        "reason": payment.refund_reason,
                        "timestamp": payment.refunded_at.isoformat() if payment.refunded_at else None
                    })
            
            except Exception as e:
                logger.error(f"Error refunding payment {payment_id}: {e}", exc_info=True)
    
    async def _handle_donation_created(self, event: dict):
        """
        Handle donation_created event
        Verify funds with banking service and create payment record
        """
        donation_id = event.get("donation_id")
        user_id = event.get("user_id")
        campaign_id = event.get("campaign_id")
        amount = Decimal(str(event.get("amount")))
        payment_method = event.get("payment_method", "card")
        
        logger.info(f"Processing payment verification for donation {donation_id}")
        
        async with AsyncSessionLocal() as db:
            try:
                # Step 1: Verify funds with banking service
                has_sufficient_funds = await self._verify_funds_with_banking(user_id, amount)
                
                if not has_sufficient_funds:
                    logger.warning(f"Insufficient funds for user {user_id}, amount: {amount}")
                    
                    # Publish payment failed event
                    await self._publish_event({
                        "event_type": "payment.failed",
                        "donation_id": donation_id,
                        "user_id": user_id,
                        "campaign_id": campaign_id,
                        "amount": float(amount),
                        "reason": "Insufficient funds",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    return
                
                # Step 2: Create payment record
                payment_data = PaymentCreate(
                    user_id=user_id,
                    order_id=str(donation_id),  # Use donation_id as order_id
                    amount=amount,
                    currency="USD",
                    payment_method=PaymentMethod(payment_method),
                    status=PaymentStatus.COMPLETED
                )
                
                payment = await create_payment(db, payment_data)
                payment_id = str(payment.id)
                payment.transaction_id = f"TXN-DONATION-{donation_id}"
                await db.commit()
                
                logger.info(f"✅ Payment {payment_id} created and verified for donation {donation_id}")
                
                # Step 3: Publish payment verified event
                await self._publish_event({
                    "event_type": "payment.verified",
                    "payment_id": payment_id,
                    "donation_id": donation_id,
                    "user_id": user_id,
                    "campaign_id": campaign_id,
                    "amount": float(amount),
                    "transaction_id": payment.transaction_id,
                    "status": "completed",
                    "timestamp": payment.created_at.isoformat() if payment.created_at else None
                })
            
            except Exception as e:
                logger.error(f"Error processing payment for donation {donation_id}: {e}", exc_info=True)
                
                # Publish payment failed event
                await self._publish_event({
                    "event_type": "payment.failed",
                    "donation_id": donation_id,
                    "user_id": user_id,
                    "campaign_id": campaign_id,
                    "amount": float(amount),
                    "reason": str(e),
                    "timestamp": asyncio.get_event_loop().time()
                })
    
    async def _verify_funds_with_banking(self, user_id: str, amount: Decimal) -> bool:
        """
        Verify if user has sufficient funds via banking service HTTP request
        """
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{BANKING_SERVICE_URL}/verify-funds"
                payload = {
                    "user_id": user_id,
                    "amount": int(amount)  # Send as integer
                }
                
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        has_funds = data.get("sufficient_funds", False)
                        logger.info(f"Banking service response for user {user_id}: sufficient_funds={has_funds}")
                        return has_funds
                    else:
                        logger.error(f"Banking service returned status {response.status}")
                        return False
        
        except asyncio.TimeoutError:
            logger.error(f"Banking service timeout for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error calling banking service: {e}")
            return False
    
    async def _publish_event(self, event: dict):
        """Publish event to payment events topic"""
        try:
            value = json.dumps(event).encode('utf-8')
            key = event.get("payment_id", event.get("donation_id", "")).encode('utf-8')
            
            # Produce message asynchronously
            await asyncio.get_event_loop().run_in_executor(
                None,
                partial(
                    self.producer.produce,
                    PAYMENT_EVENTS_TOPIC,
                    value=value,
                    key=key,
                    callback=self._delivery_callback
                )
            )
            
            # Trigger callbacks
            self.producer.poll(0)
            
            logger.info(f"📤 Published event: {event.get('event_type')} for donation/payment {event.get('donation_id', event.get('payment_id'))}")
        
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")