# Database Schema: Services & Pricing

## Overview

This document describes the database schema for services and pricing in the Pixora system, and how FacePass integrates with it.

## Table Structure

### 1. `photo_sessions`

Main table for photo sessions.

```sql
CREATE TABLE photo_sessions (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    photographer_id UUID NOT NULL,
    studio_id UUID NOT NULL,
    status VARCHAR NOT NULL,
    scheduled_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    settings JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    service_package_id UUID,  -- Links to service_packages
    facepass_enabled BOOLEAN DEFAULT false NOT NULL
);
```

**Key Fields:**
- `service_package_id`: Links to the service package for this session
- `facepass_enabled`: Whether FacePass is enabled for this session

---

### 2. `service_packages`

Service packages that can be assigned to sessions.

```sql
CREATE TABLE service_packages (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    studio_id UUID NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

**Purpose:** Groups multiple services together into a package that can be assigned to sessions.

---

### 3. `services`

Individual services (digital copy, print, etc.).

```sql
CREATE TABLE services (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    type VARCHAR NOT NULL,  -- 'digital', 'print', 'package', etc.
    photo_count INTEGER,
    is_active BOOLEAN DEFAULT true,
    studio_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

**Key Fields:**
- `price`: Service price in rubles
- `type`: Service type (used for filtering)
- `photo_count`: Number of photos included (optional)
- `is_active`: Whether service is currently available

---

### 4. `service_package_services`

Junction table linking service packages to services.

```sql
CREATE TABLE service_package_services (
    id UUID PRIMARY KEY,
    service_package_id UUID NOT NULL REFERENCES service_packages(id),
    service_id UUID NOT NULL REFERENCES services(id),
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL,
    
    UNIQUE(service_package_id, service_id)
);
```

**Key Fields:**
- `is_default`: Marks the default service (usually full archive)
- Links services to packages with many-to-many relationship

---

## Relationship Diagram

```
┌─────────────────────┐
│  photo_sessions     │
│  ─────────────────  │
│  id                 │
│  name               │
│  service_package_id │◄─────┐
│  facepass_enabled   │      │
└─────────────────────┘      │
                             │
                             │
┌─────────────────────┐      │
│  service_packages   │      │
│  ─────────────────  │      │
│  id                 │◄─────┘
│  name               │
│  description        │
└──────────┬──────────┘
           │
           │ 1:N
           │
           ↓
┌─────────────────────────┐
│ service_package_services│
│ ─────────────────────── │
│ service_package_id      │
│ service_id              │◄─────┐
│ is_default              │      │
└─────────────────────────┘      │
                                 │
                                 │ N:1
                                 │
                        ┌────────┴────────┐
                        │   services      │
                        │   ────────────  │
                        │   id            │
                        │   name          │
                        │   price         │
                        │   type          │
                        │   is_active     │
                        └─────────────────┘
```

---

## SQL Query for FacePass

FacePass uses this query to fetch services for a session:

```sql
SELECT 
    s.id,
    s.name,
    s.description,
    s.price,
    sps.is_default,
    s.type,
    s.photo_count,
    s.is_active
FROM public.photo_sessions ps
INNER JOIN public.service_packages sp ON ps.service_package_id = sp.id
INNER JOIN public.service_package_services sps ON sp.id = sps.service_package_id
INNER JOIN public.services s ON sps.service_id = s.id
WHERE ps.id = :session_id
    AND s.is_active = true
ORDER BY sps.is_default DESC, s.price ASC
```

**Query Logic:**
1. Start from `photo_sessions` with given `session_id`
2. Join to `service_packages` via `service_package_id`
3. Join to `service_package_services` to get services in package
4. Join to `services` to get service details
5. Filter only active services
6. Order by default first, then by price

---

## Example Data

### Session with Services

```sql
-- 1. Create a service package
INSERT INTO service_packages (id, name, description, studio_id, is_active)
VALUES (
    '550e8400-e29b-41d4-a716-446655440001',
    'Standard Package',
    'Standard photo package with digital and print options',
    '550e8400-e29b-41d4-a716-446655440000',
    true
);

-- 2. Create services
INSERT INTO services (id, name, description, price, type, is_active)
VALUES 
    (
        '550e8400-e29b-41d4-a716-446655440010',
        'Цифровая копия',
        'Одна фотография в цифровом формате',
        150.00,
        'digital',
        true
    ),
    (
        '550e8400-e29b-41d4-a716-446655440011',
        'Весь архив',
        'Все фотографии с фотосессии',
        2500.00,
        'package',
        true
    );

-- 3. Link services to package
INSERT INTO service_package_services (id, service_package_id, service_id, is_default)
VALUES 
    (
        '550e8400-e29b-41d4-a716-446655440020',
        '550e8400-e29b-41d4-a716-446655440001',
        '550e8400-e29b-41d4-a716-446655440010',
        false  -- Single photo
    ),
    (
        '550e8400-e29b-41d4-a716-446655440021',
        '550e8400-e29b-41d4-a716-446655440001',
        '550e8400-e29b-41d4-a716-446655440011',
        true   -- Full archive (default)
    );

-- 4. Assign package to session
UPDATE photo_sessions
SET service_package_id = '550e8400-e29b-41d4-a716-446655440001'
WHERE id = 'your-session-id';
```

---

## API Response Format

When FacePass queries `/api/v1/sessions/{session_id}/services`, it returns:

```json
{
  "sessionId": "550e8400-e29b-41d4-a716-446655440030",
  "sessionName": "Wedding Photoshoot",
  "services": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440011",
      "name": "Весь архив",
      "description": "Все фотографии с фотосессии",
      "price": 2500.0,
      "isDefault": true,
      "type": "package",
      "photoCount": null,
      "isActive": true
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440010",
      "name": "Цифровая копия",
      "description": "Одна фотография в цифровом формате",
      "price": 150.0,
      "isDefault": false,
      "type": "digital",
      "photoCount": 1,
      "isActive": true
    }
  ],
  "defaultService": {
    "id": "550e8400-e29b-41d4-a716-446655440011",
    "name": "Весь архив",
    "price": 2500.0,
    "isDefault": true
  },
  "currency": "RUB",
  "mainUrl": "https://staging.pixorasoft.ru"
}
```

---

## Price Extraction Logic

FacePass extracts two prices from the services:

1. **price_single**: Price for one photo
   - Finds service with `type = 'digital'`
   - Or service with name containing "цифровая" or "digital"
   - Used for price badges on individual photos

2. **price_all**: Price for full archive
   - Finds service with `isDefault = true`
   - Used for "Buy Full Archive" button

```javascript
getServicePrices(services) {
    // Find default service (full archive)
    const defaultService = services.find(s => s.isDefault === true);
    const price_all = defaultService ? defaultService.price : 0;
    
    // Find single photo service
    const singleService = services.find(s => 
        s.type === 'digital' || 
        s.name?.toLowerCase().includes('цифровая')
    );
    const price_single = singleService ? singleService.price : 0;
    
    return { price_single, price_all };
}
```

---

## Common Operations

### Add New Service to Existing Package

```sql
-- 1. Create the service
INSERT INTO services (id, name, description, price, type, is_active)
VALUES (
    gen_random_uuid(),
    'Печать 10x15',
    'Печать фотографии 10x15 см',
    50.00,
    'print',
    true
);

-- 2. Link to package
INSERT INTO service_package_services (id, service_package_id, service_id, is_default)
SELECT 
    gen_random_uuid(),
    ps.service_package_id,
    s.id,
    false
FROM photo_sessions ps
CROSS JOIN services s
WHERE ps.id = 'session-id' 
    AND s.name = 'Печать 10x15';
```

### Update Service Price

```sql
UPDATE services
SET price = 200.00, updated_at = NOW()
WHERE type = 'digital' AND name = 'Цифровая копия';
```

### Disable Service

```sql
UPDATE services
SET is_active = false, updated_at = NOW()
WHERE id = 'service-id';
```

### Change Session Package

```sql
UPDATE photo_sessions
SET service_package_id = 'new-package-id', updated_at = NOW()
WHERE id = 'session-id';
```

---

## Migration Notes

### Old Schema (Incorrect)

```sql
-- ❌ This table doesn't exist in Pixora
FROM public.packages p
WHERE p.photo_session_id = :session_id
```

### New Schema (Correct)

```sql
-- ✅ Correct schema with proper joins
FROM public.photo_sessions ps
INNER JOIN public.service_packages sp ON ps.service_package_id = sp.id
INNER JOIN public.service_package_services sps ON sp.id = sps.service_package_id
INNER JOIN public.services s ON sps.service_id = s.id
WHERE ps.id = :session_id
```

---

## Troubleshooting

### No Services Returned

**Possible causes:**
1. Session has no `service_package_id` set
2. Service package has no services linked
3. All services are `is_active = false`
4. Service package doesn't exist

**Check:**
```sql
-- Check if session has package
SELECT id, name, service_package_id 
FROM photo_sessions 
WHERE id = 'session-id';

-- Check package services
SELECT sp.name, s.name, s.price, s.is_active
FROM service_packages sp
JOIN service_package_services sps ON sp.id = sps.service_package_id
JOIN services s ON sps.service_id = s.id
WHERE sp.id = 'package-id';
```

### Wrong Prices Displayed

**Check:**
```sql
-- Verify service prices
SELECT name, price, type, is_active
FROM services
WHERE id IN (
    SELECT service_id 
    FROM service_package_services 
    WHERE service_package_id = 'package-id'
);
```

---

## References

- **Implementation:** `app/api/v1/endpoints/sessions.py`
- **Model:** `models/photo_session.py`
- **Frontend:** `app/static/js/face-search-pricing.js`
- **Documentation:** `docs/REAL_TIME_PRICING_SUMMARY.md`

---

**Last Updated:** 2026-02-20  
**Version:** 1.0
