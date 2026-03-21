
# Smart Laundry Backend

## App Structure
```text
app/
  main.py
  core/
  db/
  api/v1/
  modules/
  shared/
  tests/
```

## Current Module Pattern
Each module follows the same split:

```text
app/modules/<module_name>/
  models.py
  schema.py
  service.py
  router.py
```

This is already used by `users`, `businesses`, `drivers`, `business_services`, `laundry_services`, and now `orders`.

## Orders Module
The `orders` module now supports:

- Order creation
- Order listing and single-order lookup
- Order status transitions
- Order price recalculation after measurement

Main files:

- [app/modules/orders/models.py](/Users/lyheng/Documents/IU-Practice/smart_laundry_backend/app/modules/orders/models.py)
- [app/modules/orders/schema.py](/Users/lyheng/Documents/IU-Practice/smart_laundry_backend/app/modules/orders/schema.py)
- [app/modules/orders/service.py](/Users/lyheng/Documents/IU-Practice/smart_laundry_backend/app/modules/orders/service.py)
- [app/modules/orders/router.py](/Users/lyheng/Documents/IU-Practice/smart_laundry_backend/app/modules/orders/router.py)

### Order Model Shape
`Order` includes both marketplace relations and the business-facing order summary fields:

- `id`
- `order_no`
- `customer_id`
- `business_id`
- `driver_id`
- `status`
- `pickup_method`
- `placed_at`
- `scheduled_pickup_at`
- `scheduled_dropoff_at`
- `pickup_address`
- `delivery_address`
- `notes`
- `subtotal`
- `discount`
- `total`

`OrderItem` stores a snapshot of pricing data at order time:

- `id`
- `order_id`
- `business_service_id`
- `service_id`
- `service_name`
- `pricing_type`
- `measure_type`
- `unit_price`
- `quantity`
- `sub_total`
- `note`

## Order Lifecycle
Supported status flow:

`PENDING -> ACCEPTED -> PICKED_UP -> DELIVERED_TO_SHOP -> WASHING -> READY_FOR_DELIVERY -> OUT_FOR_DELIVERY -> COMPLETED`

Cancellation is allowed from:

- `PENDING`
- `ACCEPTED`

## Database Migrations
The project now includes Alembic:

```text
alembic.ini
alembic/
  env.py
  versions/
```

Current initial revision for orders:

- [alembic/versions/20260313_000001_create_orders_tables.py](/Users/lyheng/Documents/IU-Practice/smart_laundry_backend/alembic/versions/20260313_000001_create_orders_tables.py)

### Commands
Run migrations:

```bash
make migrate
```

or

```bash
make migrate-db
```

Create a new migration:

```bash
make revision m="describe_change"
```

Rollback one revision:

```bash
make downgrade
```

### Important Note
The app now defaults to migration-based schema management. `app/db/init_db.py` only runs `SQLModel.metadata.create_all()` when `DB_INIT_STRATEGY=create_all` is explicitly set.

Recommended default:

```bash
DB_INIT_STRATEGY=migrate
```

Only use this for temporary local bootstrapping without Alembic:

```bash
DB_INIT_STRATEGY=create_all
```
