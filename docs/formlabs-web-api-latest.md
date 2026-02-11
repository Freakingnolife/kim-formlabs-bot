# Formlabs Web API (v0.8.1)

> Source: https://formlabs-dashboard-api-resources.s3.amazonaws.com/formlabs-web-api-latest.html

## Overview

The Formlabs Web API is a REST HTTP API providing remote control and monitoring for internet-connected Formlabs 3D printers. The API uses JSON responses and requires OAuth2 authentication.

- **Base URL:** `https://api.formlabs.com/developer/v1/`
- **Authentication:** OAuth2 Client Credentials flow
- **Rate Limits:** 100 requests/second per IP; 1,500 requests/hour per user
- **Prerequisites:** Active Formlabs.com account with registered printers

---

## Authentication

### POST /developer/v1/o/token/
Request an access token.

**Content-Type:** application/x-www-form-urlencoded

**Body Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `grant_type` | string | Yes | Must be `client_credentials` |
| `client_id` | string | Yes | Your Client ID |
| `client_secret` | string | Yes | Your Client Secret |

**Response (200):**
```json
{
  "access_token": "string",
  "token_type": "Bearer",
  "expires_in": 86400,
  "scope": "developer-api"
}
```

**Errors:**
- 400: Invalid credentials
- 401: Unauthorized

**Usage:** Include in all subsequent requests as `Authorization: bearer <access_token>`

### POST /developer/v1/o/revoke_token/
Revoke an access token.

**Content-Type:** application/x-www-form-urlencoded

**Body Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `token` | string | Yes | Access token to revoke |
| `client_id` | string | Yes | Your Client ID |
| `client_secret` | string | Yes | Your Client Secret |

**Response (200):** No response body

---

## Data Models

### Printer
```json
{
  "serial": "string",
  "alias": "string",
  "machine_type_id": "string",
  "firmware_version": "string",
  "location": "string",
  "printer_status": {
    "status": "string",
    "last_pinged_at": "datetime",
    "hopper_level": 0,
    "material_credit": 0.0,
    "hopper_material": "string",
    "last_modified": "datetime",
    "current_temperature": 0.0,
    "build_platform_contents": "BUILD_PLATFORM_CONTENTS_NOT_SUPPORTED",
    "tank_mixer_state": "TANK_MIXER_STATE_NOT_SUPPORTED",
    "ready_to_print": "READY_TO_PRINT_NOT_SUPPORTED",
    "camera_status": "UNKNOWN",
    "printer_capabilities": ["string"],
    "printernet_capabilities": ["string"],
    "current_print_run": "PrintRun or null",
    "form_cell": {
      "serial": "string",
      "firmware_version": "string",
      "status": "string",
      "rotation": "string"
    },
    "last_printer_cooldown_started": "datetime",
    "outer_boundary_offset_corrections": null
  },
  "cartridge_status": [
    {
      "cartridge": "Cartridge",
      "last_modified": "datetime",
      "cartridge_slot": "FRONT | BACK"
    }
  ],
  "tank_status": {
    "tank": "Tank",
    "last_modified": "datetime"
  },
  "group": {
    "id": "uuid",
    "name": "string"
  },
  "previous_print_run": "object | null"
}
```

### PrintRun
```json
{
  "guid": "uuid",
  "name": "string",
  "printer": "string",
  "status": "QUEUED | PREPRINT | PRINTING | PAUSING | PAUSED | FINISHED | ABORTING | ABORTED | ERROR | WAITING_FOR_RESOLUTION | PREHEAT | PRECOAT | POSTCOAT",
  "using_open_mode": false,
  "z_height_offset_mm": 0.0,
  "print_started_at": "datetime | null",
  "print_finished_at": "datetime | null",
  "layer_count": 0,
  "volume_ml": 0.0,
  "material": "string",
  "layer_thickness_mm": 0.0,
  "currently_printing_layer": 0,
  "estimated_duration_ms": 0,
  "elapsed_duration_ms": 0,
  "estimated_time_remaining_ms": 0,
  "created_at": "datetime",
  "firmware_version": "string",
  "cartridge": "string | null",
  "front_cartridge": "string | null",
  "back_cartridge": "string | null",
  "tank": "string | null",
  "cylinder": "string | null",
  "material_name": "string",
  "print_settings_name": "string",
  "print_settings_code": "string",
  "form_auto_serial": "string | null",
  "form_auto_fw_version": "string | null",
  "harvest_status": "FORM_CELL_HARVEST_UNKNOWN",
  "print_job": "string | null",
  "user_custom_label": "string | null",
  "message": "string | null",
  "adaptive_thickness": false,
  "print_run_success": {
    "print_run": "string",
    "print_run_success": "UNKNOWN",
    "created_at": "datetime"
  },
  "note": {
    "print_run": "string",
    "note": "string",
    "author": {
      "id": 0,
      "username": "string",
      "first_name": "string",
      "last_name": "string",
      "email": "string"
    },
    "updated_at": "datetime"
  },
  "print_thumbnail": {
    "thumbnail": "string (URL)"
  },
  "post_print_photo_url": "string | null",
  "user": "User | null",
  "group": "Group | null",
  "cloud_queue_item": "object | null",
  "parts": [
    {
      "id": 0,
      "guid": "uuid",
      "display_name": "string",
      "name": "string",
      "end_layer": 0,
      "start_layer": 0,
      "volume_ml": 0.0,
      "raw_mesh_hash": "string",
      "prepared_scene": "string"
    }
  ],
  "print_intent": "uuid | null"
}
```

### Tank
```json
{
  "serial": "string",
  "material": "string",
  "layers_printed": 0,
  "print_time_ms": 0,
  "heatmap": "string (URL)",
  "heatmap_gif": "string (URL)",
  "mechanical_version": "string",
  "manufacture_date": "datetime",
  "manufacturer": "string",
  "display_name": "string",
  "lot_number": "string",
  "layer_count": 0,
  "last_modified": "datetime",
  "inside_printer": "string",
  "write_count": 0,
  "tank_type": "string",
  "connected_group": "uuid | null",
  "first_fill_date": "datetime",
  "created_at": "datetime",
  "last_print_date": "datetime | null"
}
```

### Cartridge
```json
{
  "serial": "string",
  "consumable_type": "string",
  "machine_type_id": "string",
  "material": "string",
  "initial_volume_ml": 0.0,
  "volume_dispensed_ml": 0.0,
  "dispense_count": 0,
  "write_count": 0,
  "mechanical_version": "string",
  "manufacture_date": "datetime",
  "manufacturer": "string",
  "display_name": "string",
  "lot_number": "string",
  "last_modified": "datetime",
  "is_empty": false,
  "inside_printer": "string | null",
  "connected_group": "uuid | null",
  "created_at": "datetime",
  "last_print_date": "datetime | null"
}
```

### Group
```json
{
  "id": "uuid",
  "name": "string",
  "remote_print_enabled_override": "boolean | null",
  "created_at": "datetime",
  "memberships": [
    {
      "is_admin": false,
      "user": "string",
      "email": "string",
      "first_name": "string",
      "last_name": "string"
    }
  ],
  "printers": ["string"],
  "invitations": [
    {
      "email": "string",
      "is_admin": false
    }
  ],
  "has_fleet_control": false,
  "has_fleet_control_updated_by": 0,
  "settings": {
    "group": "uuid",
    "update_mode": "string"
  }
}
```

### Event
```json
{
  "id": 0,
  "printer": "string",
  "created_at": "datetime",
  "print_run": "PrintRun | null",
  "tank": "string | null",
  "cartridge": "string | null",
  "type": "string",
  "type_label": "string",
  "action": "string",
  "message": "string",
  "was_read": false,
  "group": "Group | null"
}
```

### Queue Item
```json
{
  "id": "uuid",
  "name": "string",
  "volume_ml": 0.0,
  "material_name": "string",
  "created_at": "datetime",
  "username": "string",
  "allowed_machine_type_ids": ["string"]
}
```

---

## Endpoints

### Printers

#### GET /developer/v1/printers/
List all printers associated with the account.

**Authorization:** Bearer token required

**Response (200):** Array of Printer objects

#### GET /developer/v1/printers/{printer_serial}/
Retrieve a specific printer by serial number.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `printer_serial` | string | Yes | Unique printer serial |

**Response (200):** Printer object

---

### Prints

#### GET /developer/v1/prints/
List all prints for the account with filtering.

**Authorization:** Bearer token required

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `date` | datetime | No | Exact match (ISO 8601) |
| `date__gt` | datetime | No | Greater than date |
| `date__lt` | datetime | No | Less than date |
| `machine_type_id` | array[string] | No | Filter by machine types |
| `material` | string | No | Material type filter |
| `name` | string | No | Substring match on print name |
| `page` | integer | No | Page number |
| `per_page` | integer | No | Results per page |
| `printer` | string | No | Filter by printer serial |
| `status` | string | No | Filter by status |

**Status Values:**
`QUEUED`, `PREPRINT`, `PRINTING`, `PAUSING`, `PAUSED`, `FINISHED`, `ABORTING`, `ABORTED`, `ERROR`, `WAITING_FOR_RESOLUTION`, `PREHEAT`, `PRECOAT`, `POSTCOAT`

**Response (200):**
```json
{
  "count": 0,
  "next": "string | null",
  "previous": "string | null",
  "results": [PrintRun]
}
```

#### GET /developer/v1/printers/{printer_serial}/prints/
List all prints for a specific printer.

**Path Parameters:**
| Name | Type | Required |
|------|------|----------|
| `printer_serial` | string | Yes |

**Query Parameters:** Same as GET /prints/

**Response (200):** Same paginated structure

---

### Tanks

#### GET /developer/v1/tanks/
List all resin tanks for the account.

**Authorization:** Bearer token required

**Query Parameters:**
| Name | Type | Required |
|------|------|----------|
| `page` | integer | No |
| `per_page` | integer | No |

**Response (200):** Paginated array of Tank objects

---

### Cartridges

#### GET /developer/v1/cartridges/
List all resin cartridges for the account.

**Authorization:** Bearer token required

**Query Parameters:**
| Name | Type | Required |
|------|------|----------|
| `page` | integer | No |
| `per_page` | integer | No |

**Response (200):** Paginated array of Cartridge objects

---

### Events

#### GET /developer/v1/events/
List events for the account with filtering.

**Authorization:** Bearer token required

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `cartridge` | string | No | Filter by cartridge serial |
| `date__gt` | datetime | No | Greater than date |
| `date__lt` | datetime | No | Less than date |
| `page` | integer | No | Page number |
| `per_page` | integer | No | Results per page |
| `print_run` | string | No | Filter by print ID |
| `printer` | string | No | Filter by printer serial |
| `tank` | string | No | Filter by tank serial |
| `type` | string | No | Filter by event type |

**Response (200):** Paginated array of Event objects

---

### Printer Groups

#### GET /developer/v1/groups/
List all groups for the account.

**Response (200):** Array of Group objects

#### POST /developer/v1/groups/
Create a new printer group.

**Request Body:**
```json
{
  "name": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Group name (non-empty) |

**Response (201):**
```json
{
  "id": "uuid",
  "name": "string",
  "created_at": "datetime",
  "has_fleet_control": false,
  "has_fleet_control_updated_by": 0
}
```

#### POST /developer/v1/groups/bulk-add-printers/
Move printers to a group.

**Request Body:**
```json
{
  "target_group": "uuid",
  "printers": ["string"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target_group` | uuid | Yes | Destination group ID |
| `printers` | array[string] | Yes | Printer serials to move |

**Note:** Requester must be admin of target group and all source groups.

**Response (200):** No body

#### PATCH /developer/v1/groups/{group_id}/
Update group details.

**Path Parameters:**
| Name | Type | Required |
|------|------|----------|
| `group_id` | uuid | Yes |

**Request Body:**
```json
{
  "name": "string | null",
  "remote_print_enabled_override": "string | null"
}
```

**Response (200):** Full Group object

#### DELETE /developer/v1/groups/{group_id}/
Delete a printer group.

**Response (204):** No content

#### POST /developer/v1/groups/{group_id}/members/
Invite a user to a group.

**Request Body:**
```json
{
  "user": "email@example.com",
  "is_admin": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user` | string | Yes | Email address to invite |
| `is_admin` | boolean | No | Admin privilege flag |

**Response (201):**
```json
{
  "is_admin": false,
  "user": "string",
  "email": "string",
  "first_name": "string",
  "last_name": "string"
}
```

#### PUT /developer/v1/groups/{group_id}/members/
Update group membership.

**Request Body:**
```json
{
  "user": "email@example.com",
  "is_admin": true
}
```

**Warning:** Cannot revoke own admin rights if no other admins exist.

**Response (200):** Updated membership object

#### DELETE /developer/v1/groups/{group_id}/members/
Remove a group member.

**Request Body:**
```json
{
  "user": "email@example.com"
}
```

**Response (204):** No content

#### GET /developer/v1/groups/{group_id}/queue/
List printer group queue items.

**Response (200):** Array of Queue Item objects (empty if queue feature disabled)

---

## Rate Limiting

| Limit | Value |
|-------|-------|
| Per IP | 100 requests/second |
| Per User | 1,500 requests/hour |
| Exceeded response | HTTP 429 with `Retry-after` header |

## Technical Details

| Detail | Value |
|--------|-------|
| API Version | 0.8.1 (Beta) |
| Token Lifetime | 86,400 seconds (24 hours) |
| Data Format | JSON |
| Timestamps | ISO 8601 |
| Pagination | `count`, `next`, `previous`, `results` |
