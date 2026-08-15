# Sagaflow

This project uses a Saga pattern with 4 FastAPI microservices and a React frontend.

## Prerequisites

- Python 3.10+
- Node.js 18+
- Accounts on:
  - Neon Postgres (Database)
  - CloudAMQP (RabbitMQ)
  - Upstash (Redis)

## Setup Instructions

1. **Configure Environment Variables**
   Copy .env.example to .env in each of the 4 backend directories:
   - order-service
   - inventory-service
   - payment-service
   - orchestrator-service
   Fill in your actual connection strings for Postgres, RabbitMQ, and Redis.

2. **Backend Setup**
   For each backend service, create a virtual environment and install dependencies:
   ``powershell
   cd order-service
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ``
   Repeat this for all 4 services.

3. **Database Migrations**
   Run Alembic migrations in each service:
   ``powershell
   alembic upgrade head
   ``

4. **Frontend Setup**
   ``powershell
   cd frontend
   npm install
   ``

## Running the Application Locally

We provide a un_all.ps1 script to start all 5 services simultaneously.
Open PowerShell in the root directory and run:

``powershell
.\run_all.ps1
``

### Ports:
- **Order Service**: 8001
- **Inventory Service**: 8002
- **Payment Service**: 8003
- **Orchestrator Service**: 8004
- **Frontend**: 5173
