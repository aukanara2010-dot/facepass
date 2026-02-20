# Database Schema Visual Guide

## 🗂️ Table Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                        PHOTO SESSIONS                           │
├─────────────────────────────────────────────────────────────────┤
│  id: UUID (PK)                                                  │
│  name: TEXT                                                     │
│  photographer_id: UUID                                          │
│  studio_id: UUID                                                │
│  status: VARCHAR                                                │
│  service_package_id: UUID (FK) ────────────┐                   │
│  facepass_enabled: BOOLEAN                 │                   │
│  created_at: TIMESTAMPTZ                   │                   │
│  updated_at: TIMESTAMPTZ                   │                   │
└────────────────────────────────────────────┼───────────────────┘
                                             │
                                             │ 1:1 (optional)
                                             │
                                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE PACKAGES                           │
├─────────────────────────────────────────────────────────────────┤
│  id: UUID (PK) ◄───────────────────────────┘                   │
│  name: VARCHAR                                                  │
│  description: TEXT                                              │
│  studio_id: UUID                                                │
│  is_active: BOOLEAN                                             │
│  created_at: TIMESTAMPTZ                                        │
│  updated_at: TIMESTAMPTZ                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ 1:N
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                SERVICE PACKAGE SERVICES                         │
│                    (Junction Table)                             │
├─────────────────────────────────────────────────────────────────┤
│  id: UUID (PK)                                                  │
│  service_package_id: UUID (FK) ◄────────────┘                  │
│  service_id: UUID (FK) ─────────────────────┐                  │
│  is_default: BOOLEAN                        │                  │
│  created_at: TIMESTAMPTZ                    │                  │
│                                             │                  │
│  UNIQUE(service_package_id, service_id)     │                  │
└─────────────────────────────────────────────┼──────────────────┘
                                              │
                                              │ N:1
                                              │
                                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                          SERVICES                               │
├─────────────────────────────────────────────────────────────────┤
│  id: UUID (PK) ◄──────────────────────────────┘                │
│  name: VARCHAR                                                  │
│  description: TEXT                                              │
│  price: DECIMAL(10,2)                                           │
│  type: VARCHAR ('digital', 'print', 'package')                 │
│  photo_count: INTEGER                                           │
│  is_active: BOOLEAN                                             │
│  studio_id: UUID                                                │
│  created_at: TIMESTAMPTZ                                        │
│  updated_at: TIMESTAMPTZ                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow for FacePass

```
┌──────────────────────────────────────────────────────────────────┐
│  STEP 1: User opens FacePass session page                       │
│  URL: /api/v1/sessions/{session_id}/interface                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│  STEP 2: Frontend loads and fetches services                    │
│  Request: GET /api/v1/sessions/{session_id}/services            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│  STEP 3: Backend executes SQL query                             │
│                                                                  │
│  SELECT s.id, s.name, s.price, sps.is_default, s.type          │
│  FROM photo_sessions ps                                          │
│  JOIN service_packages sp                                        │
│    ON ps.service_package_id = sp.id                             │
│  JOIN service_package_services sps                               │
│    ON sp.id = sps.service_package_id                            │
│  JOIN services s                                                 │
│    ON sps.service_id = s.id                                     │
│  WHERE ps.id = :session_id AND s.is_active = true              │
│  ORDER BY sps.is_default DESC, s.price ASC                      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│  STEP 4: Return services JSON                                   │
│                                                                  │
│  {                                                               │
│    "services": [                                                 │
│      {                                                           │
│        "id": "uuid",                                             │
│        "name": "Весь архив",                                    │
│        "price": 2500.0,                                          │
│        "isDefault": true,                                        │
│        "type": "package"                                         │
│      },                                                          │
│      {                                                           │
│        "id": "uuid",                                             │
│        "name": "Цифровая копия",                                │
│        "price": 150.0,                                           │
│        "isDefault": false,                                       │
│        "type": "digital"                                         │
│      }                                                           │
│    ]                                                             │
│  }                                                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│  STEP 5: Frontend displays prices                               │
│                                                                  │
│  • Photo cards show: "150 ₽"                                    │
│  • Floating bar shows total                                      │
│  • "Buy Full Archive" button: "2500 ₽"                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📊 Example Data Flow

### Scenario: Wedding Photoshoot

```
1. PHOTO SESSION
   ├─ id: "a1b2c3d4-..."
   ├─ name: "Wedding Photoshoot - Ivan & Maria"
   ├─ studio_id: "studio-123"
   ├─ service_package_id: "pkg-456" ──┐
   └─ facepass_enabled: true          │
                                       │
2. SERVICE PACKAGE                     │
   ├─ id: "pkg-456" ◄──────────────────┘
   ├─ name: "Wedding Package"
   ├─ studio_id: "studio-123"
   └─ is_active: true
          │
          ├─────────────────────────────┐
          │                             │
3. SERVICE PACKAGE SERVICES             │
   ├─ service_package_id: "pkg-456"    │
   ├─ service_id: "svc-digital" ───────┼──┐
   ├─ is_default: false                │  │
   └─ created_at: 2026-01-15           │  │
                                       │  │
   ├─ service_package_id: "pkg-456"    │  │
   ├─ service_id: "svc-archive" ───────┼──┼──┐
   ├─ is_default: true                 │  │  │
   └─ created_at: 2026-01-15           │  │  │
                                       │  │  │
4. SERVICES                             │  │  │
   ┌────────────────────────────────────┘  │  │
   │                                       │  │
   ├─ id: "svc-digital" ◄─────────────────┘  │
   ├─ name: "Цифровая копия"                 │
   ├─ price: 150.00                          │
   ├─ type: "digital"                        │
   ├─ photo_count: 1                         │
   └─ is_active: true                        │
                                             │
   ├─ id: "svc-archive" ◄────────────────────┘
   ├─ name: "Весь архив"
   ├─ price: 2500.00
   ├─ type: "package"
   ├─ photo_count: null
   └─ is_active: true
```

### Result in FacePass UI:

```
┌─────────────────────────────────────────────────────────────┐
│  Wedding Photoshoot - Ivan & Maria                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ [150 ₽]      │  │ [150 ₽]      │  │ [150 ₽]      │    │
│  │              │  │              │  │              │    │
│  │   Photo 1    │  │   Photo 2    │  │   Photo 3    │    │
│  │   95% match  │  │   92% match  │  │   88% match  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Выбрано: 2  Итого: 300 ₽                                 │
│  [Купить выбранные]  [Купить весь архив - 2500 ₽]         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Query Breakdown

### Step-by-Step Join Explanation

```sql
-- Start with the session
FROM photo_sessions ps
WHERE ps.id = 'a1b2c3d4-...'

-- Result:
-- id: a1b2c3d4-...
-- name: Wedding Photoshoot
-- service_package_id: pkg-456
```

```sql
-- Join to get the package
INNER JOIN service_packages sp 
  ON ps.service_package_id = sp.id

-- Result:
-- ps.id: a1b2c3d4-...
-- ps.name: Wedding Photoshoot
-- sp.id: pkg-456
-- sp.name: Wedding Package
```

```sql
-- Join to get package-service relationships
INNER JOIN service_package_services sps 
  ON sp.id = sps.service_package_id

-- Result (2 rows):
-- Row 1:
--   sp.id: pkg-456
--   sps.service_id: svc-digital
--   sps.is_default: false
-- Row 2:
--   sp.id: pkg-456
--   sps.service_id: svc-archive
--   sps.is_default: true
```

```sql
-- Join to get service details
INNER JOIN services s 
  ON sps.service_id = s.id

-- Final Result (2 rows):
-- Row 1:
--   s.id: svc-digital
--   s.name: Цифровая копия
--   s.price: 150.00
--   sps.is_default: false
--   s.type: digital
-- Row 2:
--   s.id: svc-archive
--   s.name: Весь архив
--   s.price: 2500.00
--   sps.is_default: true
--   s.type: package
```

---

## 🎯 Key Points

### 1. service_package_id is in photo_sessions

```
✅ CORRECT:
photo_sessions.service_package_id → service_packages.id

❌ WRONG:
packages.photo_session_id → photo_sessions.id
```

### 2. is_default is in service_package_services

```
✅ CORRECT:
service_package_services.is_default

❌ WRONG:
services.is_default
```

### 3. Many-to-Many Relationship

One service package can have many services.
One service can be in many packages.

```
service_packages ←→ service_package_services ←→ services
     (1:N)                                         (N:1)
```

### 4. Service Types

```
'digital'  → Single photo download
'print'    → Physical print
'package'  → Full archive/bundle
```

---

## 🧪 Testing Queries

### Check if session has services

```sql
SELECT 
    ps.name as session,
    sp.name as package,
    COUNT(s.id) as service_count
FROM photo_sessions ps
LEFT JOIN service_packages sp ON ps.service_package_id = sp.id
LEFT JOIN service_package_services sps ON sp.id = sps.service_package_id
LEFT JOIN services s ON sps.service_id = s.id
WHERE ps.id = 'session-id'
GROUP BY ps.name, sp.name;
```

### List all services for a session

```sql
SELECT 
    s.name,
    s.price,
    s.type,
    sps.is_default,
    s.is_active
FROM photo_sessions ps
JOIN service_packages sp ON ps.service_package_id = sp.id
JOIN service_package_services sps ON sp.id = sps.service_package_id
JOIN services s ON sps.service_id = s.id
WHERE ps.id = 'session-id'
ORDER BY sps.is_default DESC, s.price ASC;
```

### Find sessions without services

```sql
SELECT 
    ps.id,
    ps.name,
    ps.service_package_id
FROM photo_sessions ps
WHERE ps.facepass_enabled = true
    AND (
        ps.service_package_id IS NULL
        OR NOT EXISTS (
            SELECT 1 
            FROM service_package_services sps
            WHERE sps.service_package_id = ps.service_package_id
        )
    );
```

---

## 📝 Common Patterns

### Pattern 1: Add service to existing package

```sql
-- Insert service
INSERT INTO services (id, name, price, type, is_active)
VALUES (gen_random_uuid(), 'New Service', 100.00, 'digital', true)
RETURNING id;

-- Link to package
INSERT INTO service_package_services (id, service_package_id, service_id, is_default)
VALUES (gen_random_uuid(), 'package-id', 'service-id', false);
```

### Pattern 2: Create package with services

```sql
-- Create package
INSERT INTO service_packages (id, name, studio_id, is_active)
VALUES (gen_random_uuid(), 'Premium Package', 'studio-id', true)
RETURNING id;

-- Link existing services
INSERT INTO service_package_services (id, service_package_id, service_id, is_default)
SELECT 
    gen_random_uuid(),
    'new-package-id',
    id,
    false
FROM services
WHERE type IN ('digital', 'print');
```

### Pattern 3: Clone package for new studio

```sql
-- Create new package
INSERT INTO service_packages (id, name, description, studio_id, is_active)
SELECT 
    gen_random_uuid(),
    name,
    description,
    'new-studio-id',
    is_active
FROM service_packages
WHERE id = 'template-package-id';

-- Copy service links
INSERT INTO service_package_services (id, service_package_id, service_id, is_default)
SELECT 
    gen_random_uuid(),
    'new-package-id',
    service_id,
    is_default
FROM service_package_services
WHERE service_package_id = 'template-package-id';
```

---

**Last Updated:** 2026-02-20  
**Version:** 1.0  
**See Also:** `docs/DATABASE_SCHEMA_SERVICES.md`
