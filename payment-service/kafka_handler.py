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

from database import AsyncSessionLocal
from models import PaymentCreate, PaymentStatus, PaymentMethod
from crud import create_payment

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
BANKING_SERVICE_URL = os.getenv("BANKING_SERVICE_URL", "http://banking-service:8006")
PAYMENT_EVENTS_TOPIC = "payment.events"
DONATION_EVENTS_TOPIC = "donation_created"

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
            self.consumer.subscribe([DONATION_EVENTS_TOPIC])
            
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
                    
                    if event_type == "donation_created":
                        await self._handle_donation_created(event)
                
                except Exception as e:
                    logger.error(f"Error processing Kafka event: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Kafka consumer error: {e}", exc_info=True)
    
    async def _handle_donation_created(self, event: dict):
        """
        Handle donation_created event
        1. Verify funds with banking service
        2. Debit the account
        3. Create payment record
        4. Publish payment.verified or payment.failed event
        """
        donation_id = event.get("donation_id")
        user_id = event.get("user_id")
        campaign_id = event.get("campaign_id")
        amount = Decimal(str(event.get("amount")))
        payment_method = event.get("payment_method", "card")
        
        logger.info(f"🔄 Processing payment for donation {donation_id} - User: {user_id}, Amount: ${amount}")
        
        async with AsyncSessionLocal() as db:
            payment_id = None
            try:
                # Step 1: Verify funds with banking service
                logger.info(f"Step 1: Checking balance for user {user_id}...")
                has_sufficient_funds, balance_info = await self._verify_funds_with_banking(user_id, amount)
                
                if not has_sufficient_funds:
                    logger.warning(f"❌ Insufficient funds - User: {user_id}, Required: ${amount}, Available: ${balance_info.get('current_balance', 0)}")
                    
                    # Publish payment failed event
                    await self._publish_event({
                        "event_type": "payment.failed",
                        "donation_id": donation_id,
                        "user_id": user_id,
                        "campaign_id": campaign_id,
                        "amount": float(amount),
                        "reason": f"Insufficient funds. Available: ${balance_info.get('current_balance', 0)}",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    return
                
                logger.info(f"✅ Step 1 Complete: User has sufficient funds")
                
                # Step 2: Debit the account
                logger.info(f"Step 2: Debiting ${amount} from user {user_id}...")
                debit_success, debit_message, new_balance = await self._debit_account(user_id, amount)
                
                if not debit_success:
                    logger.error(f"❌ Debit failed: {debit_message}")
                    
                    # Publish payment failed event
                    await self._publish_event({
                        "event_type": "payment.failed",
                        "donation_id": donation_id,
                        "user_id": user_id,
                        "campaign_id": campaign_id,
                        "amount": float(amount),
                        "reason": f"Debit failed: {debit_message}",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    return
                
                logger.info(f"✅ Step 2 Complete: Account debited. New balance: ${new_balance}")
                
                # Step 3: Create payment record
                logger.info(f"Step 3: Creating payment record...")
                payment_data = PaymentCreate(
                    user_id=user_id,
                    order_id=str(donation_id),
                    amount=amount,
                    currency="USD",
                    payment_method=PaymentMethod(payment_method),
                    status=PaymentStatus.COMPLETED
                )
                
                payment = await create_payment(db, payment_data)
                payment_id = str(payment.id)
                payment.transaction_id = f"TXN-DONATION-{donation_id}"
                await db.commit()
                
                logger.info(f"✅ Step 3 Complete: Payment record created - ID: {payment_id}")
                
                # Step 4: Publish payment verified event
                logger.info(f"Step 4: Publishing payment.verified event...")
                await self._publish_event({
                    "event_type": "payment.verified",
                    "payment_id": payment_id,
                    "donation_id": donation_id,
                    "user_id": user_id,
                    "campaign_id": campaign_id,
                    "amount": float(amount),
                    "transaction_id": payment.transaction_id,
                    "status": "completed",
                    "new_balance": float(new_balance),
                    "timestamp": payment.created_at.isoformat() if payment.created_at else None
                })
                
                logger.info(f"🎉 Payment processing complete for donation {donation_id}!")
            
            except Exception as e:
                logger.error(f"💥 Error processing payment for donation {donation_id}: {e}", exc_info=True)
                
                # Publish payment failed event
                await self._publish_event({
                    "event_type": "payment.failed",
                    "donation_id": donation_id,
                    "user_id": user_id,
                    "campaign_id": campaign_id,
                    "amount": float(amount),
                    "reason": f"Payment processing error: {str(e)}",
                    "timestamp": asyncio.get_event_loop().time()
                })
    
    async def _verify_funds_with_banking(self, user_id: str, amount: Decimal) -> tuple[bool, dict]:
        """
        Verify if user has sufficient funds via banking service HTTP request
        Returns: (has_sufficient_funds, balance_info)
        """
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                # Use the correct banking service endpoint
                url = f"{BANKING_SERVICE_URL}/internal/balance/{user_id}"
                params = {"amount": float(amount)}
                
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        has_funds = data.get("has_sufficient_balance", False)
                        current_balance = data.get("current_balance", 0)
                        logger.info(f"🏦 Banking check - User: {user_id}, Has Funds: {has_funds}, Balance: ${current_balance}")
                        return has_funds, data
                    else:
                        error_text = await response.text()
                        logger.error(f"Banking service returned status {response.status}: {error_text}")
                        return False, {"error": f"Banking service error: {response.status}"}
        
        except asyncio.TimeoutError:
            logger.error(f"⏰ Banking service timeout for user {user_id}")
            return False, {"error": "Banking service timeout"}
        except Exception as e:
            logger.error(f"💥 Error calling banking service: {e}")
            return False, {"error": str(e)}
    
    async def _debit_account(self, user_id: str, amount: Decimal) -> tuple[bool, str, Decimal]:
        """
        Debit amount from user's bank account via banking service HTTP request
        Returns: (success, message, new_balance)
        """
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{BANKING_SERVICE_URL}/internal/debit"
                payload = {
                    "user_id": user_id,
                    "amount": float(amount)
                }
                
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        success = data.get("success", False)
                        message = data.get("message", "")
                        new_balance = Decimal(str(data.get("new_balance", 0)))
                        
                        if success:
                            logger.info(f"💰 Debit successful - User: {user_id}, Amount: ${amount}, New Balance: ${new_balance}")
                        else:
                            logger.warning(f"⚠️ Debit failed - User: {user_id}, Reason: {message}")
                        
                        return success, message, new_balance
                    else:
                        error_text = await response.text()
                        logger.error(f"Banking service debit failed with status {response.status}: {error_text}")
                        return False, f"Banking service error: {response.status}", Decimal("0")
        
        except asyncio.TimeoutError:
            logger.error(f"⏰ Banking service timeout during debit for user {user_id}")
            return False, "Banking service timeout", Decimal("0")
        except Exception as e:
            logger.error(f"💥 Error calling banking service debit: {e}")
            return False, str(e), Decimal("0")
    
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