# Formlabs Local API v0.9.12

> Source: https://formlabs-dashboard-api-resources.s3.us-east-1.amazonaws.com/formlabs-local-api-v0.9.12.html

## Overview

The Formlabs Local API enables automation of job preparation and printer management without launching PreForm's graphical interface. It follows RESTful principles organized around resources and collections, accessible via HTTP methods at resource-specific URIs.

## Core Architecture

**PreFormServer Application:**
- Background service (Windows/MacOS) that exposes the HTTP API
- Requires `--port` argument to specify listening port
- Outputs "READY FOR INPUT" when operational
- Maintains a stateful cache of up to 100 scenes (configurable via `--scene-cache-size`)

## Key Concepts

- **Scenes:** Current job state for a specific printer, including models, support structures, and printer/material configuration
- **Stateful Interactions:** The server caches scenes with IDs. The special ID "default" references a global scene
- **Asynchronous Operations:** Long-running tasks support `?async=true` parameter, returning immediately with an operation ID for polling via `/operations/{operation_id}/`
- **File Paths:** Require full OS paths (e.g., `C:\Users\user\Desktop\part.stl`); relative paths, environment variables, and URLs are unsupported
- **Timeout:** 10-minute maximum for all requests

---

## Data Models

### Scene Object
```json
{
  "models": [Model],
  "scene_settings": {
    "machine_type": "string",
    "material_code": "string",
    "print_setting": "string",
    "layer_thickness_mm": "ADAPTIVE",
    "custom_print_setting_id": "string"
  },
  "material_usage": {
    "volume_ml": 0,
    "unsupported_volume_ml": 0
  },
  "layer_count": 0,
  "id": "string"
}
```

### Model Object
```json
{
  "id": "string",
  "name": "string",
  "position": {"x": 0, "y": 0, "z": 0},
  "orientation": {"x": 0, "y": 0, "z": 0},
  "scale": 0,
  "units": "MILLIMETERS",
  "bounding_box": {
    "min_corner": {"x": 0, "y": 0, "z": 0},
    "max_corner": {"x": 0, "y": 0, "z": 0}
  },
  "original_file": "string",
  "visible": true,
  "has_supports": true,
  "in_bounds": true,
  "raw_mesh_hash": "string",
  "canonical_model_hash": "string",
  "lock": "FREE"
}
```

### Device Object
```json
{
  "id": "string",
  "product_name": "string",
  "status": "string",
  "is_connected": true,
  "connection_type": "UNKNOWN",
  "ip_address": "string",
  "firmware_version": "string"
}
```

### Lock Enum
- `FREE`
- `LOCKED_XY_ROTATION_FREE_TRANSLATION`
- `LOCKED_ROTATION_FREE_TRANSLATION`
- `FULLY_LOCKED`

### Units Enum
- `DETECTED`
- `MILLIMETERS`
- `INCHES`

### Repair Behavior Enum
- `REPAIR`
- `ERROR`
- `IGNORE`

### Raft Type Enum
- `FULL_RAFT`
- `MINI_RAFT`
- `MINI_RAFTS_ON_BP`

---

## Endpoints

### Devices

#### GET /devices/
List of previously discovered device statuses.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `can_print` | boolean | No | If true, only devices that can receive prints |

**Response (200):**
```json
{
  "count": 0,
  "devices": [Device]
}
```

#### GET /devices/{id}/
Get a previously discovered device's status.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Unique printer identifier |

**Response (200):** Device object

#### POST /discover-devices/
Discover new devices on the network.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `async` | boolean | No | Run asynchronously |

**Request Body:**
```json
{
  "timeout_seconds": 10,
  "ip_address": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timeout_seconds` | integer | Yes | Seconds to wait discovering |
| `ip_address` | string | No | Specific IP to attempt |

**Response (200/202):** Device list

#### POST /upload-firmware/
Upload new firmware to a device.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `async` | boolean | No | Run asynchronously |

**Request Body:**
```json
{
  "printer": "Form4-TestyTest",
  "file_path": "C:\\Users\\user\\Desktop\\form4-public-1.9.0-2444.formware"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `printer` | string | Yes | IP or serial name |
| `file_path` | string | Yes | Local path to .formware file |

---

### Scene Management

#### POST /scene/
Create a new scene.

**Request Body:**
```json
{
  "machine_type": "FORM-4-0",
  "material_code": "FLGPBK05",
  "print_setting": "DEFAULT",
  "layer_thickness_mm": 0.025,
  "custom_print_setting_id": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `machine_type` | string | Yes | Printer type identifier |
| `material_code` | string | Yes | Material identifier |
| `print_setting` | string | No | Print setting name |
| `layer_thickness_mm` | number | Yes | Slice thickness |
| `custom_print_setting_id` | string | No | Custom setting ID |

**Response (200):** Scene object

#### POST /scene/default/
Create a default scene with given printing setup.

**Request/Response:** Same as POST /scene/

#### GET /scene/
Get all scenes.

**Response (200):** Array of Scene objects

#### GET /scene/{scene_id}/
Get a specific scene.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `scene_id` | string | Yes | Unique scene identifier |

**Response (200):** Scene object

#### PUT /scene/{scene_id}/
Update a scene's properties.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `scene_id` | string | Yes | Unique scene identifier |

**Request Body:** Same as POST /scene/

**Response (200):** Scene object

#### DELETE /scene/{scene_id}/
Delete a scene.

**Response (200):** Scene object

#### DELETE /scene/default/
Delete the default scene, replace with blank scene.

**Response (200):** Scene object

#### POST /load-form/
Load a .form file and create a new scene.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `async` | boolean | No | Run asynchronously |

**Request Body:**
```json
{
  "file": "C:\\Users\\user\\Desktop\\test.form"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | string | Yes | Full path to .form file |

**Response (200/202):** Scene object

---

### Models

#### POST /scene/{scene_id}/import-model/
Import a model into current scene.

**Path Parameters:**
| Name | Type | Required |
|------|------|----------|
| `scene_id` | string | Yes |

**Query Parameters:**
| Name | Type | Required |
|------|------|----------|
| `async` | boolean | No |

**Request Body:**
```json
{
  "file": "C:\\Users\\user\\Desktop\\test.stl",
  "repair_behavior": "ERROR",
  "name": "string",
  "position": {"x": 0, "y": 0, "z": 0},
  "orientation": {"x": 0, "y": 0, "z": 0},
  "scale": 1,
  "units": "DETECTED",
  "lock": "FREE"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | string | Yes | - | Full OS path to model file |
| `repair_behavior` | string | No | "ERROR" | REPAIR, ERROR, or IGNORE |
| `name` | string | No | - | Model name |
| `position` | object | No | - | {x, y, z} coordinates |
| `orientation` | object | No | - | Euler angles, matrix, or vectors |
| `scale` | number | No | 1 | Scale factor |
| `units` | string | No | "DETECTED" | DETECTED, MILLIMETERS, INCHES |
| `lock` | string | No | "FREE" | Lock constraint |

**Response (200/202):** Model object

#### GET /scene/{scene_id}/models/{id}/
Get a specific model.

**Response (200):** Model object

#### POST /scene/{scene_id}/models/{id}/
Update a model's properties.

**Request Body:**
```json
{
  "name": "string",
  "position": {"x": 10, "y": 1, "z": 2},
  "orientation": {"x": 0, "y": 0, "z": 0},
  "scale": 1.0,
  "units": "MILLIMETERS",
  "lock": "FREE"
}
```

**Response (200):** Model object

#### DELETE /scene/{scene_id}/models/{id}/
Delete a model from scene.

**Response (200):** OK

#### POST /scene/{scene_id}/models/{id}/duplicate/
Duplicate a model.

**Request Body:**
```json
{
  "count": 2
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `count` | integer | Yes | Number of duplicates |

**Response (200):** Scene object

#### POST /scene/{scene_id}/models/{id}/replace/
Replace model with new file, copying existing setup.

**Request Body:**
```json
{
  "file": "string",
  "repair_behavior": "REPAIR"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | string | Yes | Full path to new file |
| `repair_behavior` | string | No | REPAIR, ERROR, or IGNORE |

**Response (200):**
```json
{
  "warnings": ["string"],
  "model_properties": Model
}
```

---

### Auto-Operations

#### POST /scene/{scene_id}/auto-orient/
Automatically choose model orientation for printing.

**Query Parameters:** `async` (boolean, optional)

**Request Body:**
```json
{
  "models": "ALL"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `models` | string/array | No | "ALL" | "ALL" or array of model IDs |

**Response (202):** `{ "operationId": "string" }`

#### POST /scene/{scene_id}/auto-support/
Generate support structures on models.

**Query Parameters:** `async` (boolean, optional)

**Request Body:**
```json
{
  "models": "ALL",
  "density": 1.0,
  "slope_multiplier": 1.0,
  "only_minima": false,
  "raft_type": "FULL_RAFT",
  "raft_label_enabled": true,
  "breakaway_structure_enabled": true,
  "touchpoint_size_mm": 0.5,
  "internal_supports_enabled": false,
  "raft_thickness_mm": 0,
  "height_above_raft_mm": 0,
  "z_compression_correction_mm": 0,
  "early_layer_merge_mm": 0
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `models` | string/array | No | "ALL" | Target models |
| `density` | number | No | 1.0 | Support density (>= 0) |
| `slope_multiplier` | number | No | 1.0 | Slope multiplier (>= 0) |
| `only_minima` | boolean | No | false | Only support minima |
| `raft_type` | string | No | "FULL_RAFT" | FULL_RAFT, MINI_RAFT, MINI_RAFTS_ON_BP |
| `raft_label_enabled` | boolean | No | true | Enable raft label |
| `breakaway_structure_enabled` | boolean | No | true | Enable breakaway supports |
| `touchpoint_size_mm` | number | No | 0.5 | Touchpoint size (>= 0) |
| `internal_supports_enabled` | boolean | No | false | Enable internal supports |
| `raft_thickness_mm` | number | No | 0 | Raft thickness (>= 0) |
| `height_above_raft_mm` | number | No | 0 | Height above raft (>= 0) |
| `z_compression_correction_mm` | number | No | 0 | Z compression correction (>= 0) |
| `early_layer_merge_mm` | number | No | 0 | Early layer merge (>= 0) |

**Response (202):** Operation ID

#### POST /scene/{scene_id}/auto-layout/
Automatically arrange models on build platform (SLA only).

**Query Parameters:** `async` (boolean, optional)

**Request Body:**
```json
{
  "models": "ALL",
  "model_spacing_mm": 1,
  "allow_overlapping_supports": false,
  "lock_rotation": false,
  "build_platform_2_optimized": false,
  "mode": "DENTAL",
  "custom_bounds": {}
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `models` | string/array | No | "ALL" | Target models |
| `model_spacing_mm` | number | No | 1 | Spacing between models (>= 0) |
| `allow_overlapping_supports` | boolean | No | false | Allow support overlap |
| `lock_rotation` | boolean | No | false | Lock model rotation |
| `build_platform_2_optimized` | boolean | No | false | BP2 optimization |
| `mode` | string | No | - | "DENTAL" or unset |
| `custom_bounds` | object | No | - | Custom bounds |

**Response (200/202):** Scene object

#### POST /scene/{scene_id}/auto-pack/
Automatically arrange models in build volume (SLS only).

**Query Parameters:** `async` (boolean, optional)

**Request Body:**
```json
{
  "model_spacing_mm": 5
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `model_spacing_mm` | number | No | 5 | Minimum spacing (>= 0) |

**Response (200/202):** Scene object

#### POST /scene/pack-and-cage/
Arrange models and create cage around them (SLS).

**Request Body:**
```json
{
  "models": "ALL",
  "packing_type": {"packing_type": "PACK_NORMAL"},
  "cage_label": "string",
  "generate_mesh_label": true,
  "model_spacing_mm": 0,
  "bar_spacing_mm": 0,
  "bar_thickness_mm": 1,
  "bar_width_mm": 1,
  "distance_to_cage_mm": 0,
  "enable_round_edges": false,
  "enable_square_bars": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `models` | string/array | Yes | "ALL" | Target models |
| `packing_type` | object | No | - | Packing method |
| `cage_label` | string | No | - | Label on cage |
| `generate_mesh_label` | boolean | No | - | Emboss label on mesh |
| `model_spacing_mm` | number | No | 0 | Model spacing (>= 0) |
| `bar_spacing_mm` | number | No | 0 | Bar spacing (>= 0) |
| `bar_thickness_mm` | number | No | 1 | Bar thickness (>= 1) |
| `bar_width_mm` | number | No | 1 | Bar width (>= 1) |
| `distance_to_cage_mm` | number | No | 0 | Distance to cage (>= 0) |
| `enable_round_edges` | boolean | No | false | Round cage edges |
| `enable_square_bars` | boolean | No | true | Square bars |

**Response (200):** Scene object

---

### Dental Operations

#### POST /scene/{scene_id}/scan-to-model/
Convert STL scan to solid printable model (dental).

**Path Parameters:** `scene_id` (string, required)

**Query Parameters:** `async` (boolean, optional)

**Request Body:**
```json
{
  "file": "string",
  "files": ["string"],
  "units": "DETECTED",
  "cutoff_height_mm": 0,
  "extrude_distance_mm": 0,
  "hollow": true,
  "enable_honeycomb_infill": true,
  "cutoff_below_gumline_mm": 0,
  "shell_thickness_mm": 0,
  "wall_thickness_mm": 0,
  "drain_hole_radius_mm": 1.5,
  "drain_hole_height_ratio": 1,
  "drain_hole_suppression_distance_mm": 2,
  "drain_hole_max_count": 2,
  "enable_smooth_contour_extended_sides": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | string | No | - | Single file path |
| `files` | array | No | - | Multiple file paths |
| `units` | string | No | "DETECTED" | Unit system |
| `cutoff_height_mm` | number | Yes | - | Remove below this height |
| `extrude_distance_mm` | number | No | - | Extrude distance |
| `hollow` | boolean | No | - | Hollow the model |
| `enable_honeycomb_infill` | boolean | No | true | Honeycomb infill |
| `cutoff_below_gumline_mm` | number | No | - | Cut below gumline |
| `shell_thickness_mm` | number | No | - | Shell thickness |
| `wall_thickness_mm` | number | No | - | Wall thickness |
| `drain_hole_radius_mm` | number | No | 1.5 | Drain hole radius |
| `drain_hole_height_ratio` | number | No | 1 | Drain hole height ratio |
| `drain_hole_suppression_distance_mm` | number | No | 2 | Drain hole suppression dist |
| `drain_hole_max_count` | number | No | 2 | Max drain holes |
| `enable_smooth_contour_extended_sides` | boolean | No | true | Smooth contour sides |

**Response (200/202):** Scene object with warnings/infos arrays

---

### Scene Information

#### POST /scene/{scene_id}/estimate-print-time/
Estimate print time for scene.

**Response (200):** Print time estimate

#### POST /scene/{scene_id}/get-interferences/
Get scene interference data.

**Response (200):** Interference report

#### GET /scene/{scene_id}/validation/
Get print validation.

**Response (200):** Validation results

---

### Export

#### POST /save-form/
Save scene as .form file.

**Request Body:**
```json
{
  "file_path": "string",
  "scene_id": "string"
}
```

#### POST /save-screenshot/
Save screenshot of scene.

**Request Body:**
```json
{
  "file_path": "string",
  "scene_id": "string"
}
```

#### POST /save-fps/
Save FPS (print-ready) file.

**Request Body:**
```json
{
  "file_path": "string",
  "scene_id": "string"
}
```

---

### Printing

#### POST /print/
Send scene to printer.

**Request Body:**
```json
{
  "printer": "string",
  "scene_id": "string"
}
```

---

### Authentication

#### POST /login/
Login to Formlabs services.

**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```

#### POST /logout/
Logout from services.

#### GET /user/
Get logged-in user information.

---

### Materials

#### GET /list-materials/
List available materials and print settings.

**Response (200):**
```json
{
  "materials": [
    {
      "material_code": "string",
      "product_name": "string",
      "print_settings": ["string"]
    }
  ]
}
```

---

### Operations (Async Polling)

#### GET /operations/{operation_id}/
Get operation status and progress.

**Path Parameters:**
| Name | Type | Required |
|------|------|----------|
| `operation_id` | string | Yes |

**Response (200):**
```json
{
  "operation_id": "string",
  "status": "PENDING|IN_PROGRESS|COMPLETED|FAILED",
  "progress_percent": 50
}
```

#### GET /operations/
List all operations.

**Response (200):** Array of operation objects

---

### API Info

#### GET /api-version/
Get API version.

**Response (200):**
```json
{
  "version": "0.9.12"
}
```
