# Product Service - FastAPI Ecommerce Microservice

## Features

- Product CRUD operations
- Inventory management
- Search and filtering
- PostgreSQL database with async SQLAlchemy
- Redis caching for product data
- OpenTelemetry tracing
- Prometheus metrics
- Health checks
- Structured logging
- Docker support

## API Endpoints

### Product Management

- `POST /api/v1/products` - Create product
- `GET /api/v1/products` - List products with pagination
- `GET /api/v1/products/{id}` - Get product by ID
- `PUT /api/v1/products/{id}` - Update product
- `DELETE /api/v1/products/{id}` - Delete product

### Inventory

- `PUT /api/v1/products/{id}/stock` - Update product stock

### Search

- `GET /api/v1/products/search?q={query}` - Search products by name

### Health & Monitoring

- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Environment Variables

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=productdb
REDIS_URL=redis://localhost:6379
JAEGER_ENDPOINT=http://localhost:14268/api/traces
```

## Run with Docker

```bash
docker build -t product-service-fastapi .
docker run -p 8001:8001 product-service-fastapi
```