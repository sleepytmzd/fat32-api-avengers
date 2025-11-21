# CareForAll - API Avengers Microservices Platform

<div align="center">

**Team FAT32**

*A highly scalable, event-driven donation platform built for the CUET API Avengers Microservice Hackathon 2025*

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Technologies Used](#-technologies-used)
- [Microservices](#-microservices)
- [Infrastructure Components](#-infrastructure-components)
- [Observability Stack](#-observability-stack)
- [Getting Started](#-getting-started)
- [API Documentation](#-api-documentation)
- [System Features](#-system-features)

---

## 🎯 Overview

**CareForAll** is a production-ready, cloud-native donation platform designed to handle:

- ✅ **High Traffic**: 1000+ requests/second capacity
- ✅ **Event-Driven Architecture**: Kafka-based asynchronous communication
- ✅ **Idempotent Operations**: Reliable payment processing with webhook handling
- ✅ **Complete Observability**: Distributed tracing, log aggregation, and metrics
- ✅ **Transparent Donation Tracking**: Full donation lifecycle management
- ✅ **Scalable Design**: Independent microservices with dedicated databases

---

## 🏗️ Architecture

```
┌─────────────┐
│   Frontend  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway (8000)                      │
│   • Authentication & Authorization (JWT)                     │
│   • Rate Limiting & Circuit Breaking                         │
│   • Request Routing & Load Balancing                         │
│   • Distributed Tracing                                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│User Service │    │  Campaign   │    │  Donation   │
│   (8001)    │    │  Service    │    │  Service    │
│             │    │   (8002)    │    │   (8004)    │
│ • Auth/JWT  │    │             │    │             │
│ • Profiles  │    │ • CRUD      │◄───┤ • Pledges   │
│ • Roles     │    │ • gRPC      │gRPC│ • FSM       │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                              │
                   ┌──────────────────────────┤
                   │                          │
                   ▼                          ▼
            ┌─────────────┐          ┌─────────────┐
            │  Payment    │          │ Notification│
            │  Service    │          │  Service    │
            │   (8003)    │          │   (8005)    │
            │             │          │             │
            │ • Webhooks  ├──────────►│ • Events   │
            │ • Banking   │  Kafka   │ • Alerts    │
            └──────┬──────┘          └─────────────┘
                   │
                   ▼
            ┌─────────────┐
            │  Banking    │
            │  Service    │
            │   (8006)    │
            │             │
            │ • Accounts  │
            │ • Verify    │
            └─────────────┘

         ┌─────────────────────────┐
         │   Infrastructure        │
         ├─────────────────────────┤
         │ Kafka + Zookeeper       │
         │ PostgreSQL (per service)│
         │ Redis (caching)         │
         │ Jaeger (tracing)        │
         │ Loki + Promtail (logs)  │
         │ Grafana (visualization) │
         └─────────────────────────┘
```

---

## 🛠️ Technologies Used

### **Core Framework**
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.11+ | Primary programming language |
| **FastAPI** | 0.104+ | High-performance async web framework |
| **Uvicorn** | Latest | ASGI server for production |
| **Pydantic** | 2.x | Data validation and settings management |

### **Databases**
| Technology | Usage |
|------------|-------|
| **PostgreSQL** | 15-alpine - Dedicated database per service |
| **Redis** | 7-alpine - Caching, rate limiting, session storage |

### **Message Broker**
| Technology | Purpose |
|------------|---------|
| **Apache Kafka** | Event streaming, async communication |
| **Zookeeper** | Kafka cluster coordination |
| **Kafka UI** | Web-based Kafka management |

### **Communication Protocols**
- **REST API**: HTTP/JSON for synchronous communication
- **gRPC**: High-performance RPC between donation-service ↔ campaign-service
- **Kafka Events**: Asynchronous event-driven messaging

### **Observability**
| Tool | Purpose | Port |
|------|---------|------|
| **Jaeger** | Distributed tracing | 16686 |
| **Loki** | Log aggregation | 3100 |
| **Promtail** | Log collection agent | - |
| **Grafana** | Metrics & logs visualization | 3000 |
| **OpenTelemetry** | Instrumentation SDK | - |

### **DevOps & Infrastructure**
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **GitHub Actions** - CI/CD (future)

---

## 🔬 Microservices

### 1️⃣ **API Gateway** (Port 8000)

**Role**: Single entry point for all client requests

**Responsibilities**:
- 🔐 **Authentication**: JWT token validation
- 🚦 **Rate Limiting**: Redis-based request throttling
- ⚡ **Circuit Breaking**: Fault tolerance for downstream services
- 🔄 **Load Balancing**: Intelligent request distribution
- 📊 **Request Tracing**: Distributed tracing with Jaeger
- 🗂️ **Service Registry**: Dynamic service discovery

**Tech Stack**:
- FastAPI, Redis, OpenTelemetry, JWT

**Key Features**:
- Configurable rate limits per endpoint
- Automatic circuit breaking on service failures
- Request/Response logging with correlation IDs
- Health check aggregation

---

### 2️⃣ **User Service** (Port 8001)

**Role**: User authentication and profile management

**Database**: `userdb` (PostgreSQL)

**Responsibilities**:
- 👤 **User Management**: Registration, login, profile updates
- 🔑 **Authentication**: JWT token generation and validation
- 🎭 **Role-Based Access**: DONOR, CAMPAIGN_OWNER, ADMIN roles
- 📝 **User Profiles**: Donor and campaign owner information

**Tech Stack**:
- FastAPI, SQLAlchemy, PostgreSQL, JWT, Bcrypt

**API Endpoints**:
```
POST   /register          - Create new user account
POST   /login             - Authenticate and get JWT token
GET    /users/me          - Get current user profile
PUT    /users/me          - Update user profile
GET    /users/{id}        - Get user by ID (admin)
```

**Key Features**:
- Password hashing with bcrypt
- JWT token with expiry
- Role-based authorization
- User session management

---

### 3️⃣ **Campaign Service** (Port 8002)

**Role**: Fundraising campaign management

**Database**: `campaigndb` (PostgreSQL)

**Responsibilities**:
- 📢 **Campaign CRUD**: Create, read, update, delete campaigns
- 🎯 **Goal Tracking**: Monitor fundraising goals and progress
- ✅ **Status Management**: ACTIVE, PAUSED, COMPLETED, CANCELLED
- 🔌 **gRPC Server**: High-performance RPC endpoint for donation-service

**Tech Stack**:
- FastAPI, SQLAlchemy, PostgreSQL, gRPC, Redis (caching)

**API Endpoints**:
```
POST   /campaigns         - Create new campaign
GET    /campaigns         - List all campaigns (paginated)
GET    /campaigns/{id}    - Get campaign details
PUT    /campaigns/{id}    - Update campaign
DELETE /campaigns/{id}    - Delete campaign
```

**gRPC Methods**:
```protobuf
rpc GetCampaign(CampaignRequest) returns (CampaignResponse);
rpc UpdateCampaignTotal(UpdateTotalRequest) returns (UpdateTotalResponse);
```

**Key Features**:
- Redis caching for frequently accessed campaigns
- Real-time goal progress updates via gRPC
- Campaign owner verification
- Media attachments support

---

### 4️⃣ **Donation Service** (Port 8004)

**Role**: Donation pledge and lifecycle management

**Database**: `donation_db` (PostgreSQL)

**Responsibilities**:
- 💝 **Donation Creation**: Handle donation intents
- 🔄 **State Machine**: INITIATED → PENDING → AUTHORIZED → CAPTURED → COMPLETED/FAILED/REFUNDED
- 📤 **Event Publishing**: Emit donation events to Kafka
- 📥 **Event Consumption**: Listen to payment events
- 🔌 **gRPC Client**: Communicate with campaign-service

**Tech Stack**:
- FastAPI, SQLAlchemy, PostgreSQL, AIOKafka, gRPC client

**Kafka Topics**:
- **Produces**: `donation_created` - When new donation is initiated
- **Consumes**: `payment.events` - Payment verification results

**API Endpoints**:
```
POST   /donations         - Create new donation
GET    /donations/{id}    - Get donation details
GET    /donations         - List user donations
GET    /campaigns/{id}/donations - List campaign donations
```

**State Machine Flow**:
```
INITIATED → payment verification request
         ↓
PENDING → awaiting payment service
         ↓
AUTHORIZED → payment verified
         ↓
CAPTURED → funds debited
         ↓
COMPLETED ✅
```

**Key Features**:
- Comprehensive emoji-based logging
- Automatic campaign total updates via gRPC
- Kafka-based async payment processing
- Donation history tracking

---

### 5️⃣ **Payment Service** (Port 8003)

**Role**: Payment processing and banking integration

**Database**: `payment_db` (PostgreSQL)

**Responsibilities**:
- 💳 **Payment Verification**: Validate payment requests
- 🏦 **Banking Integration**: Communicate with banking-service
- 🔁 **Idempotent Webhooks**: Handle duplicate webhook deliveries
- 📤 **Event Publishing**: Emit payment success/failure events

**Tech Stack**:
- FastAPI, SQLAlchemy, PostgreSQL, Confluent Kafka, HTTPx

**Kafka Topics**:
- **Consumes**: `donation_created` - New donation events
- **Produces**: `payment.events` - Payment verification results

**Payment Flow**:
```
1. Consume donation_created event
2. Call banking-service to verify funds
3. Debit user account if sufficient balance
4. Publish payment.verified or payment.failed event
5. Update donation-service via Kafka
```

**Key Features**:
- Async payment processing
- Fund verification before debit
- Detailed transaction logging
- Webhook signature verification (future)

---

### 6️⃣ **Banking Service** (Port 8006)

**Role**: Mock banking system for account operations

**Database**: `banking_db` (PostgreSQL)

**Responsibilities**:
- 💰 **Account Management**: Create and manage user accounts
- 💵 **Balance Operations**: Check balance, debit, credit
- ✅ **Transaction Validation**: Verify sufficient funds
- 📊 **Transaction History**: Track all account operations

**Tech Stack**:
- FastAPI, SQLAlchemy, PostgreSQL

**API Endpoints**:
```
POST   /accounts          - Create new account
GET    /accounts/{id}     - Get account details
POST   /verify            - Verify sufficient funds
POST   /debit             - Debit from account
POST   /credit            - Credit to account
GET    /transactions/{account_id} - Get transaction history
```

**Key Features**:
- Thread-safe balance operations
- Transaction atomicity
- Audit trail for all operations
- Negative balance prevention

---

### 7️⃣ **Notification Service** (Port 8005)

**Role**: Event-driven notification system

**Database**: `notification_db` (PostgreSQL)

**Responsibilities**:
- 📧 **Email Notifications**: Send donation receipts (mocked)
- 📱 **In-app Alerts**: Store notifications for users
- 📥 **Event Listening**: Consume Kafka events
- 🔔 **Real-time Updates**: WebSocket support (future)

**Tech Stack**:
- FastAPI, SQLAlchemy, PostgreSQL, Confluent Kafka

**Kafka Topics**:
- **Consumes**: `payment.events` - Payment verification results

**Notification Types**:
- Donation success confirmation
- Payment failure alerts
- Campaign milestone reached
- Campaign owner updates

**Key Features**:
- Async event processing
- Template-based notifications
- Notification history
- User preference management (future)

---

## 🏭 Infrastructure Components

### **Kafka Ecosystem**

| Component | Purpose | Port |
|-----------|---------|------|
| **Zookeeper** | Kafka cluster coordination | 2181 |
| **Kafka Broker** | Message streaming | 9092 |
| **Kafka UI** | Web-based management | 8080 |

**Topics**:
- `donation_created` - New donation events
- `payment.events` - Payment verification results

**Consumer Groups**:
- `payment-service-group` - Payment processing
- `donation-service-group` - Donation status updates
- `notification-service-group` - Notification delivery

---

### **Databases**

Each service has a dedicated PostgreSQL database for data isolation:

| Service | Database | Port |
|---------|----------|------|
| User | `userdb` | 5433 |
| Campaign | `campaigndb` | 5434 |
| Notification | `notification_db` | 5435 |
| Payment | `payment_db` | 5436 |
| Donation | `donation_db` | 5437 |
| Banking | `banking_db` | 5438 |

**Benefits**:
- Service autonomy
- Independent scaling
- Failure isolation
- Schema evolution flexibility

---

### **Redis**

**Purpose**: Distributed caching and session management

**Port**: 6379

**Use Cases**:
- API Gateway rate limiting
- Campaign data caching
- Session storage
- Distributed locks

---

## 📊 Observability Stack

### **Distributed Tracing - Jaeger**

**Port**: 16686

**Features**:
- End-to-end request tracing
- Service dependency visualization
- Performance bottleneck identification
- gRPC call tracing

**Access**: http://localhost:16686

---

### **Log Aggregation - Loki + Promtail**

**Loki Port**: 3100

**Features**:
- Centralized log collection from all containers
- Label-based log filtering
- Real-time log streaming
- Long-term log retention (31 days)

**Log Labels**:
- `container_name` - Service identifier
- `service` - Service name
- `version` - Service version
- `level` - Log level (INFO, ERROR, etc.)

---

### **Visualization - Grafana**

**Port**: 3000

**Credentials**: admin/admin

**Dashboards**:
1. **CareForAll Logs Dashboard** - Service-specific log panels
2. **Error Monitoring** - Platform-wide error aggregation
3. **Trace-to-Log Correlation** - Jump from traces to logs

**Datasources**:
- Loki (logs)
- Jaeger (traces)

**Access**: http://localhost:3000

---

## 🚀 Getting Started

### **Prerequisites**

- Docker Desktop (latest)
- Docker Compose (latest)
- 8GB+ RAM
- 20GB+ disk space

### **Quick Start**

1. **Clone the repository**
```bash
git clone https://github.com/sleepytmzd/fat32-api-avengers.git
cd fat32-api-avengers
```

2. **Start all services**
```bash
docker-compose up -d
```

3. **Verify services are healthy**
```bash
docker-compose ps
```

4. **Access the platform**
- API Gateway: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Jaeger UI: http://localhost:16686
- Kafka UI: http://localhost:8080
- Grafana: http://localhost:3000

### **Development Setup**

For individual service development:

```bash
# User Service
cd user-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Similar for other services...
```

### **Stop All Services**

```bash
docker-compose down
```

### **Clean Everything (including data)**

```bash
docker-compose down -v
rm -rf data/
```

---

## 📚 API Documentation

### **Interactive API Docs**

Each service exposes Swagger UI documentation:

- API Gateway: http://localhost:8000/docs
- User Service: http://localhost:8001/docs
- Campaign Service: http://localhost:8002/docs
- Donation Service: http://localhost:8004/docs
- Payment Service: http://localhost:8003/docs
- Banking Service: http://localhost:8006/docs
- Notification Service: http://localhost:8005/docs

### **Example API Flow**

#### **1. Register User**
```bash
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "donor@example.com",
    "password": "securepass123",
    "name": "John Doe",
    "role": "DONOR"
  }'
```

#### **2. Login**
```bash
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "donor@example.com",
    "password": "securepass123"
  }'
```

#### **3. Create Campaign**
```bash
curl -X POST http://localhost:8000/api/campaigns \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Help Build School",
    "description": "Building school in rural area",
    "goal_amount": 50000,
    "category": "EDUCATION"
  }'
```

#### **4. Make Donation**
```bash
curl -X POST http://localhost:8000/api/donations \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": 1,
    "amount": 1000,
    "is_anonymous": false
  }'
```

---

## ✨ System Features

### **High Availability**
- ✅ Health checks for all services
- ✅ Automatic container restart
- ✅ Circuit breaking for fault tolerance
- ✅ Database connection pooling

### **Security**
- ✅ JWT-based authentication
- ✅ Role-based authorization
- ✅ Password hashing (bcrypt)
- ✅ Rate limiting per user/IP
- ✅ CORS configuration
- ✅ SQL injection prevention (ORM)

### **Performance**
- ✅ Async I/O with FastAPI
- ✅ Redis caching
- ✅ Database indexing
- ✅ Connection pooling
- ✅ gRPC for internal communication
- ✅ Kafka for async operations

### **Observability**
- ✅ Distributed tracing (Jaeger)
- ✅ Centralized logging (Loki)
- ✅ Metrics visualization (Grafana)
- ✅ Correlation IDs
- ✅ Structured logging
- ✅ Health check endpoints

### **Scalability**
- ✅ Microservices architecture
- ✅ Database per service
- ✅ Stateless services
- ✅ Event-driven communication
- ✅ Horizontal scaling ready
- ✅ Load balancing support

---

## 🔧 Configuration

### **Environment Variables**

Each service can be configured via environment variables in `docker-compose.yml`:

```yaml
# Example: User Service
environment:
  DATABASE_URL: postgresql+asyncpg://user:password@postgres-user:5432/userdb
  JWT_SECRET: your-secret-key
  JWT_EXPIRY_HOURS: 24
  JAEGER_ENDPOINT: http://jaeger:14268/api/traces
  TRACING_ENABLED: "true"
```

### **Kafka Configuration**

Topics are auto-created, but you can pre-create them:

```bash
docker exec -it kafka-demo kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic donation_created \
  --partitions 3 \
  --replication-factor 1
```

---

## 📈 Monitoring & Troubleshooting

### **Check Service Health**
```bash
# All services
curl http://localhost:8000/health

# Individual service
curl http://localhost:8001/health
```

### **View Logs**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f user-service

# Last 100 lines
docker-compose logs --tail=100 donation-service
```

### **View Traces in Jaeger**
1. Open http://localhost:16686
2. Select service (e.g., "api-gateway")
3. Click "Find Traces"
4. Explore request flows

### **View Logs in Grafana**
1. Open http://localhost:3000
2. Import `careforall-logs-dashboard.json`
3. Filter by service: `{container_name="user-service-demo"}`

### **Monitor Kafka**
1. Open http://localhost:8080
2. View topics, consumers, and message flow

---

## 🧪 Testing

### **Health Check All Services**
```bash
./scripts/health-check.sh
```

### **Run Integration Tests**
```bash
pytest tests/integration/
```

### **Load Testing**
```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api/campaigns

# Using Locust
locust -f tests/load/locustfile.py
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team FAT32

- **Project Lead**: CareForAll Platform Development
- **Hackathon**: CUET API Avengers Microservice Hackathon 2025
- **Date**: November 21, 2025

---

## 🙏 Acknowledgments

- FastAPI community for excellent documentation
- CUET for organizing the hackathon
- Open source contributors

---

## 📞 Support

For issues and questions:
- GitHub Issues: [Report Bug](https://github.com/sleepytmzd/fat32-api-avengers/issues)
- Documentation: Check service-specific READMEs
- Logs: Use Grafana dashboard for debugging

---

<div align="center">

**Built with ❤️ by Team FAT32**

*Making donations transparent and accessible*

</div>
