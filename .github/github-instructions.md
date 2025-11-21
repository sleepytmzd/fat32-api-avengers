# CareForAll – API Avengers Microservices Backend

This repository contains a *FastAPI-based microservices backend* for the CareForAll donation platform, designed for the *Api Avengers Microservice Hackathon (CUET, 21 Nov 2025)*.

The system is built to handle:
- High traffic (1000+ requests/sec)
- Idempotent & reliable payment processing
- Transparent donation histories
- Robust observability (logs/metrics/tracing)
- *Docker Compose*

---

## 1. Services Overview

This repo follows a *monorepo* layout with six core services:

1. *api-gateway*
   - Single entrypoint for frontend (/api/...)
   - Routes requests to internal services
   - Handles authentication, basic rate limiting, request IDs

2. *user-service*
   - Manages users & donor profiles (registered + guest)
   - Auth (JWT), roles: DONOR, CAMPAIGN_OWNER, ADMIN
   - Exposes user profile and history endpoints (via other services)

3. *campaign-service* you can think of it as the product-service 
   - CRUD for fundraising campaigns
   - Stores campaign metadata, goal amount, status, etc.

4. *donation-service* you can think of it as the order-service
   - Handles pledges/donation intents
   - Manages donation state machine: INITIATED → AUTHORIZED → CAPTURED → REFUNDED
   - Emits events for payment & totals

5. *payment-service*
   - Integrates with external payment provider (mocked in this project)
   - Responsible for:
     - Creating payment sessions
     - Handling *webhooks with idempotency*
   - Updates payment status & publishes events

6. *notification-service*
   - Listens to domain events (e.g., donation captured)
   - Sends email/in-app notifications (mocked)
   - Can be extended for admin alerts & real-time updates

**Note:** Additional services like `totals-service`, `ledger-service`, `chat-service`, etc. can be added later if needed. For now, we focus on the six above.


---

## 2. Tech Stack

- *Language:* Python 3.11+
- *Framework:* FastAPI
- *ASGI Server:* Uvicorn / Gunicorn
- *Database:* PostgreSQL (per service or shared with separate schemas)
- *Message broker:* Kafka (TBD in later steps)
- *Containerization:* Docker & Docker Compose
- *Testing:* pytest
- *Auth:* JWT (via user-service)

---

## 3. Repository Structure

This is the **intended** structure. Some folders may be placeholders until implemented.


```bash
.
├── api-gateway/
│   └── src/...
├── user-service/
│   └── src/...
├── campaign-service/
│   └── src/...
├── donation-service/
│   └── src/...
├── payment-service/
│   └── src/...
├── notification-service/
│   └── src/...
├── docker-compose.yml