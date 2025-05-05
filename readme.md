# Partial Food Delivery Order Management System

This project demonstrates a partial implementation of a backend system for a food delivery service, focusing on the order management lifecycle. It utilizes a microservices architecture pattern with event-driven communication via Kafka.

The primary goal is to showcase the interaction between different services (Order Manager, Inventory, Pricing) using FastAPI, Kafka, Redis, and PostgreSQL, all orchestrated with Docker Compose.

**Note:** This is a partial implementation. Features like payment processing, delivery assignment, user management, and the final persistence of order status to PostgreSQL are not fully implemented.

## Architecture

The system consists of the following core components:

**Services:**

* **Order Manager (`order_manager`):**
    * A FastAPI service.
    * Consumes validated order requests from the `validated_orders` Kafka topic.
    * Orchestrates the order processing flow.
    * Calls the Inventory Service to check stock availability.
    * Calls the Pricing Service to calculate the final order price.
    * Updates the current order status in the Redis cache.
    * Publishes status update events (`order_status_updates` Kafka topic).
    * Publishes events intended for database persistence (`db_write_order_status` Kafka topic) upon reaching terminal states (CONFIRMED, FAILED).
* **Inventory Service (`inventory_service`):**
    * A FastAPI service.
    * Provides an HTTP API (`/check_inventory`) to check item availability.
    * Connects directly to the PostgreSQL database to query the `inventory_items` table.
    * (Note: Stock decrement logic is not implemented).
* **Pricing Service (`pricing_service`):**
    * A FastAPI service.
    * Provides an HTTP API (`/calculate_price`) to calculate the final order cost.
    * Takes item details (including price per item) as input.
    * Applies simple hardcoded discount and fee rules.

**Infrastructure:**

* **Kafka (`kafka` & `zookeeper`):** Acts as the central message broker for asynchronous communication between services. Key topics:
    * `validated_orders`: Input topic for orders ready for processing.
    * `order_status_updates`: Topic where `order_manager` publishes general status changes.
    * `db_write_order_status`: Topic where `order_manager` publishes enriched data for orders reaching a final state, intended for persistence.
* **Redis (`redis`):** An in-memory data store used as a cache to hold the *current* status of orders for quick lookups. Status keys have a TTL (Time-To-Live).
* **PostgreSQL (`postgres`):** A relational database used for:
    * Storing inventory item stock counts (accessed by `inventory_service`).
    * *Intended* persistent storage for final order details (via the `orders` table).

**Missing Components:**

* **Postgres Writer Service:** The service responsible for consuming messages from the `db_write_order_status` Kafka topic and writing/updating the final order state in the `orders` PostgreSQL table **is NOT implemented in this version.**

**Workflow:**

1.  A message representing a validated order (including user ID, items with quantity and price-per-item) is published to the `validated_orders` Kafka topic.
2.  The `order_manager` consumes the message.
3.  `order_manager` calls the `inventory_service` API to check stock.
4.  If stock is available, `order_manager` calls the `pricing_service` API to get the final calculated price.
5.  If pricing succeeds, `order_manager` updates the order status to `PROCESSING` in Redis and publishes corresponding events to Kafka topics (`order_status_updates`, potentially a simple event to `db_write_order_status`).
6.  After a simulated delay (representing payment/other checks), `order_manager` updates the status to `CONFIRMED` in Redis and publishes corresponding events, including the *enriched* event to `db_write_order_status`.
7.  If inventory or pricing checks fail, the status is set to `FAILED` in Redis, and corresponding events (including the enriched event to `db_write_order_status`) are published.

## Prerequisites

* Docker ([Install Docker](https://docs.docker.com/engine/install/))
* Docker Compose (Usually included with Docker Desktop, or install separately. V2 `docker compose` command recommended).

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```
2.  **Verify Project Structure:** Ensure the following directories and files exist:
    * `order_manager/` (with its Python files and `Dockerfile`)
    * `inventory_service/` (with its Python files and `Dockerfile`)
    * `pricing_service/` (with its Python files and `Dockerfile`)
    * `postgres_init/` (containing `init-db.sql`)
    * `docker-compose.yaml`
3.  **(Optional) Environment Variables:** The `docker-compose.yaml` uses default credentials for PostgreSQL (`user`/`password`/`food_delivery_db`). You can override these by creating a `.env` file in the root directory with:
    ```dotenv
    POSTGRES_USER=your_custom_user
    POSTGRES_PASSWORD=your_secure_password
    POSTGRES_DB=your_custom_db_name
    ```

## Running the System

1.  **Build and Start Services:** Open a terminal in the project's root directory and run:
    ```bash
    docker compose up --build -d
    ```
    * `--build`: Builds the images for the services if they don't exist or if the code/Dockerfile has changed.
    * `-d`: Runs the containers in detached mode (in the background).

2.  **Check Container Status:**
    ```bash
    docker compose ps
    ```
    All services (zookeeper, kafka, redis, postgres, inventory_service, pricing_service, order_manager) should show as `Up` or `running` (healthchecks might take a few moments).

3.  **View Logs:** To see the output from a specific service:
    ```bash
    docker compose logs -f <service_name>
    ```
    Examples:
    ```bash
    docker compose logs -f order_manager
    docker compose logs -f inventory_service
    docker compose logs -f pricing_service
    ```
    Use `Ctrl+C` to stop following logs.

4.  **Stop the System:**
    ```bash
    docker compose down
    ```
    To remove the data volumes (PostgreSQL data, Redis data) as well:
    ```bash
    docker compose down -v
    ```

## Testing the Flow

1.  **Send a Test Order:**
    * Orders are triggered by sending a JSON message to the `validated_orders` Kafka topic.
    * Use the `kafka-console-producer` tool running inside the Kafka container:
        ```bash
        docker exec -it kafka kafka-console-producer --broker-list kafka:9092 --topic validated_orders
        ```
    * The command will wait for input (you might see a `>` prompt or just a blinking cursor).
    * Paste a valid JSON message representing an order. **Ensure the `item_id` values match items seeded in `postgres_init/init-db.sql` for inventory checks to pass.**
        ```json
        {"user_id": "user-001", "items": [{"item_id": "sushi-set", "quantity": 1, "price": 25.50}, {"item_id": "pho-bo", "quantity": 2, "price": 9.00}]}
        ```
    * Press `Enter`. The message is sent to Kafka.
    * You can send more messages. Press `Ctrl+C` to exit the producer when done.

2.  **Observe Logs:**
    * Tail the logs for the main services: `docker compose logs -f order_manager inventory_service pricing_service`
    * **Expected Sequence:**
        * `order_manager`: Logs "Received validated order..."
        * `order_manager`: Logs "Checking inventory..."
        * `inventory_service`: Logs receiving the check request and potentially the database query (if SQL echo is enabled).
        * `order_manager`: Logs the inventory check result (e.g., "Available=True").
        * `order_manager`: Logs "Calculating price..."
        * `pricing_service`: Logs receiving the calculation request.
        * `order_manager`: Logs the pricing result (e.g., "Final Price=...").
        * `order_manager`: Logs "Processing order..."
        * `order_manager`: Logs "Confirming order..."
        * `order_manager`: Logs "Finished processing order..."

3.  **Check Redis Cache:**
    * Find the `order_id` (UUID) from the `order_manager` logs for the order you sent.
    * Connect to Redis:
        ```bash
        docker exec -it redis redis-cli
        ```
    * Get the status (replace `<actual_order_id>` with the UUID):
        ```redis
        GET order_status:<actual_order_id>
        ```
    * You should see a JSON string showing the latest status, likely `CONFIRMED` if everything worked, along with calculated price details.
    * Type `exit` to leave redis-cli.

4.  **Check Kafka Output Topics (Optional):**
    * See status update events:
        ```bash
        docker exec -it kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic order_status_updates --from-beginning
        ```
    * See events intended for the database writer:
        ```bash
        docker exec -it kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic db_write_order_status --from-beginning
        ```
    * Press `Ctrl+C` to stop consumers. You should see JSON messages corresponding to the statuses published by `order_manager`.

5.  **Check PostgreSQL Inventory Data:**
    * Verify the initial inventory items exist:
        ```bash
        docker exec -it postgres psql -U user -d food_delivery_db -c "SELECT * FROM inventory_items;"
        ```
