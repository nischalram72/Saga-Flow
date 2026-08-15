# Saga Flow: Distributed Transaction Orchestrator

Saga Flow is a full-stack, event-driven e-commerce microservices platform demonstrating the **Saga Design Pattern**. It showcases how to handle distributed transactions across multiple independent databases without relying on Two-Phase Commit (2PC).

## 🚀 Architecture Overview

In a microservices architecture, each service has its own database. A simple action like "Checkout" spans multiple services (Orders, Inventory, Payments). If one fails, the entire transaction must be rolled back. 

This project uses an **Orchestration-based Saga**. A central Orchestrator coordinates the workflow. If a failure occurs (e.g., payment fails), the Orchestrator automatically fires **Compensating Transactions** to reverse previous successful steps (e.g., releasing reserved inventory).

### Microservices
The backend is built with **FastAPI (Python)** and relies heavily on **RabbitMQ** for asynchronous event-driven communication.

1. **Order Service (Port 8001)**
   - Entry point for customers.
   - Database: PostgreSQL (Neon)
   - Responsibilities: Creates `PENDING` orders, triggers the start of a Saga workflow.
2. **Inventory Service (Port 8002)**
   - Database: PostgreSQL (Neon)
   - Responsibilities: Checks available stock, reserves items, and releases reservations if a compensation is triggered.
3. **Payment Service (Port 8003)**
   - Database: PostgreSQL (Neon)
   - Responsibilities: Processes payments. Includes a developer toggle to explicitly force payment failures, triggering the Saga rollback mechanism.
4. **Orchestrator Service (Port 8004)**
   - The central brain of the transaction.
   - Database: PostgreSQL (Neon)
   - Responsibilities: Tracks the state machine of the order. Listens to events, publishes commands, and coordinates compensating transactions on failure. Exposes a **WebSocket** endpoint for real-time tracking.

### Frontend
- **Tech Stack:** React, Vite, TailwindCSS (Custom CSS)
- **Storefront:** Allows users to add items to their cart, configure a delivery address, and toggle the "Simulate Payment Failure" switch.
- **Live Saga Tracker:** An interactive UI that establishes a WebSocket connection with the Orchestrator to visually step through the distributed transaction in real-time.
- **Admin Dashboard:** Displays live polling of inventory stock levels and a history of all executed sagas (successes and rollbacks).

---

## 🛠️ Tech Stack & Infrastructure
* **Backend:** FastAPI, SQLAlchemy, Pydantic
* **Frontend:** React.js, Vite
* **Database:** PostgreSQL (Hosted on Neon Serverless)
* **Message Broker:** RabbitMQ (Hosted on CloudAMQP)
* **Caching (Optional):** Redis (Hosted on Upstash)
* **Migrations:** Alembic

---

## ⚙️ How to Run Locally

### Prerequisites
- Python 3.10+
- Node.js 18+
- Active `.env` variables for PostgreSQL and RabbitMQ URIs.

### 1. Start the Backend Services
You can start all 4 Python microservices simultaneously using the provided PowerShell script:

```powershell
.\run_all.ps1
```
*(This script activates the virtual environment and launches Order, Inventory, Payment, and Orchestrator on their respective ports).*

### 2. Start the Frontend
In a new terminal window, navigate to the frontend directory and start the Vite development server:

```powershell
cd frontend
npm install
npm run dev
```

The application will be accessible at `http://localhost:5173`.

---

## 🧪 Testing the Saga Rollback
The highlight of this project is the fault tolerance mechanism. To see it in action:

1. Navigate to the storefront and add items to your cart.
2. Proceed to Checkout.
3. Check the **"Simulate Payment Failure?"** toggle.
4. Click Submit.
5. Watch the Live Saga Tracker visually walk through the following events:
   - `Order Created` (Order Service)
   - `Inventory Reserved` (Inventory Service)
   - 🔴 `Payment Failed` (Payment Service intentionally throws an error)
   - 🔙 `Inventory Released` (Compensating Transaction restores stock)
   - ❌ `Order Rejected` (Order Service marks order as failed)

If you check the Admin Panel, you will notice the inventory stock numbers remain exactly as they were before the transaction started, proving the distributed rollback was successful!
