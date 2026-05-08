# Smart Laundry Backend API

Backend service for the Smart Laundry Management System built with FastAPI, PostgreSQL, Docker, and Alembic.

---

# Technologies Used

* FastAPI
* PostgreSQL
* Docker & Docker Compose
* Alembic
* Pytest

---

# Prerequisites

Make sure the following tools are installed on your machine:

| Tool           | Purpose                 |
| -------------- | ----------------------- |
| Python 3.11+   | Backend runtime         |
| Docker         | Container runtime       |
| Docker Compose | Container orchestration |
| Make           | Command automation      |
| Git            | Source control          |

---

# Installation Guide

## 1. Clone the Repository

```bash
git clone <repository-url>
cd smart-laundry-backend
```

---

## 2. Create Python Virtual Environment

```bash
python -m venv venv
```

Activate the virtual environment:

### Linux / macOS

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create a `.env` file in the project root.

Example:

```env
DATABASE_URL=postgresql://app_user:password@localhost:5432/smart_laundry
SECRET_KEY=your_secret_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=ap-southeast-1
AWS_SQS_ENDPOINT_URL=your_sqs_queue_url
AWS_S3_ENDPOINT_URL=your_s3_url
FIREBASE_PROJECT_ID=firebase_project_id
FIREBASE_CREDENTIALS_PATH=path_to_service.json
DB_INIT_STRATEGY=create_all
TOPIC_PICKUP_ASSIGNMENT=pickup_assignment
TOPIC_DELIVERY_ASSIGNMENT=delivery_assignment
```

---

# Running the Application

## Start Docker Services

```bash
make up
```

This command starts:

* PostgreSQL database
* other Docker services defined in `docker-compose.yml`

---

## Build and Start Services

```bash
make up-build
```

---

## Run FastAPI Development Server

```bash
make run
```

Application will run at:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

ReDoc documentation:

```text
http://127.0.0.1:8000/redoc
```

---

# Database Migration

## Apply Latest Migration

```bash
make migrate-db
```

---

## Create New Migration

```bash
make revision m="create_user_table"
```

---

## Downgrade Last Migration

```bash
make downgrade
```

---

# Testing

Run unit/integration tests:

```bash
make test
```

---

# Useful Make Commands

| Command                     | Description                    |
| --------------------------- | ------------------------------ |
| `make up`                   | Start Docker containers        |
| `make up-build`             | Build and start containers     |
| `make down`                 | Stop containers                |
| `make restart`              | Restart containers             |
| `make logs`                 | View container logs            |
| `make ps`                   | Show running containers        |
| `make clean`                | Remove containers and volumes  |
| `make run`                  | Run FastAPI development server |
| `make test`                 | Run tests                      |
| `make migrate-db`           | Apply database migrations      |
| `make downgrade`            | Rollback last migration        |
| `make revision m="message"` | Create Alembic migration       |
| `make backup`               | Backup PostgreSQL database     |
| `make freeze`               | Update requirements.txt        |

---

# Docker Commands

## View Logs

```bash
make logs
```

---

## Stop Services

```bash
make down
```

---

## Remove Containers and Volumes

```bash
make clean
```

---

# Project Structure

```text
app/
├── api/                    # API route definitions and endpoint registration
├── consumer/               # Message queue consumers (e.g., SQS consumers)
├── core/                   # Core application configuration and settings
├── db/                     # Database configuration and session management
├── exceptions/             # Custom exception handling
├── lib/                    # Shared libraries and utility helpers
├── modules/                # Business domain modules
│   ├── auth/               # Authentication and authorization
│   ├── business_services/  # Business service management
│   ├── businesses/         # Business-related operations
│   ├── device_tokens/      # Device token management for notifications
│   ├── drivers/            # Driver management
│   ├── files/              # File upload and file management
│   ├── laundry_services/   # Laundry service management
│   ├── notifications/      # Notification handling
│   ├── orders/             # Laundry order processing
│   ├── payments/           # Payment processing
│   ├── realtime/           # Real-time communication features
│   ├── reviews/            # Customer reviews and ratings
│   └── users/              # User management
├── patterns/               # Design patterns and reusable abstractions
├── seeds/                  # Database seed scripts
├── shared/                 # Shared resources and common components
├── tests/                  # Unit and integration tests
└── __init__.py             # Python package initialization
```
---

# Notes

* Ensure Docker is running before executing Docker-related commands.
* Do not commit `.env` files or secret credentials to Git.
* Keep `firebaseServiceAccount.json` excluded using `.gitignore`.
* `firebaseServiceAccount.json` must be placed in the **root of the project** before running `docker compose up`. It is mounted into the backend container at `/app/msg/firebaseServiceAccount.json`. Without this file, the backend will fail to start.

---

docker exec -t cc16b0454a58 pg_dump \
  -U app_user \
  -d smart_laundry \
  -C \
  --exclude-table=alembic_version \
  --exclude-table=device_tokens \
  --exclude-table=driver_assignment_histories \
  --exclude-table=driver_assignments \
  --exclude-table=notifications \
  --exclude-table=order_items \
  --exclude-table=orders \
  --exclude-table=payments \
  --exclude-table=shop_reviews \
  --exclude-table=used_verbs \
  > backup.sql



