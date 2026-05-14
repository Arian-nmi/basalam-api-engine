# 🚀 Marketplace Integration Engine

A scalable backend system for integrating internal shop items with external marketplaces such as **Basalam** and **Digikala**.

This project demonstrates how to design and implement a **production-ready asynchronous pipeline** for product creation, transformation, and synchronization across third-party platforms.

---

## 🧠 Overview

This system handles the full lifecycle of publishing a product to a marketplace:

* Transform internal product data into marketplace-specific format
* Process and upload images
* Queue tasks using Redis
* Execute async jobs using Celery workers
* Communicate with external APIs
* Track status and handle failures
* Send real-time Telegram notifications

---

## 🏗 Architecture

The system follows an **asynchronous, queue-based architecture**:

        +-------------+
        | Shop Item   |
        +-------------+
               |
               v
        +----------------------+
        | Basalam Builder      |
        +----------------------+
               |
               v
        +----------------------+
        | Redis Queue          |
        +----------------------+
               |
               v
        +----------------------+
        | Celery Worker        |
        +----------------------+
               |
               v
        +----------------------+
        | Basalam API          |
        +----------------------+
               |
               v
        +----------------------+
        | Database Update      |
        +----------------------+
               |
               v
        +----------------------+
        | Telegram Notification|
        +----------------------+

### Key Concepts:

* Decoupled components
* Idempotent operations
* Fault-tolerant pipeline
* Scalable worker-based processing

---

## ⚙️ Tech Stack

* **Django** – ORM, signals, transactions
* **Celery** – Distributed task queue
* **Redis** – Message broker / queue
* **PostgreSQL** – Data storage
* **External APIs** – Marketplace integrations
* **Thread-based notifications** – Telegram alerts

---

## 🔄 Example Flow (Basalam)

1. A shop item is marked for marketplace publishing
2. System validates and builds a `BasalamProduct`
3. Images are processed and prepared
4. Product is pushed to Redis queue
5. Celery worker picks up the task
6. Images are uploaded to Basalam
7. Product is created via API
8. Status is updated in database
9. Telegram notification is sent

---

## 🧩 Modules

### `bs_bridge.py`

Transforms internal models into marketplace-compatible structures.

### `bs_routine_tasks.py`

Finds eligible shop items and queues them for processing.

### `bs_queue_workers.py`

Consumes queue and processes products asynchronously.

### `image_uploader.py`

Handles uploading product images to external APIs.

### `product.py`

Orchestrates product publishing flow.

### `client.py`

Handles HTTP communication with marketplace APIs.

### `creation.py`

Responsible for creating products via API.

### `signals.py`

Keeps system state in sync and triggers notifications.

---

## 🚨 Error Handling

* Custom exception system (`BasalamBuildError`)
* Step-based failure tracking
* Graceful fallback to `imperfect` state
* Transaction-safe operations using `transaction.atomic`
* Retry-safe and idempotent design

---

## 📣 Monitoring & Notifications

* Telegram notifications for:

  * Product creation
  * Failures
  * Successful publish
* Enables real-time system monitoring

---

## 💡 Key Features

* Asynchronous processing with Celery & Redis
* Clean separation of concerns
* Scalable queue-based architecture
* Idempotent operations (safe re-runs)
* Race-condition-aware design
* External API integration
* Production-style error handling

---

## 🎯 Why This Project Matters

This project showcases:

* Real-world backend system design
* Asynchronous architecture and task queues
* Integration with external APIs
* Scalable and maintainable code structure
* Production-level thinking (failures, retries, monitoring)

---

## 📌 Notes

This repository is a **simplified and generalized version** of a real-world production system.
Sensitive business logic and private configurations have been removed or abstracted.

---

## 👨‍💻 Author

Developed as part of a real-world backend system for marketplace automation.

