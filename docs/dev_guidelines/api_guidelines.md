# API Response Standards

## Data Naming Conventions
- Use **explicit names** for clarity.
- **Example**: `listener_host` instead of `host`.

---

## Response Structure

All responses should follow this format:

```json
{
  "status": 200,
  "message": "Success",
  "data": Data, or the empty form of that data (ex, a list, empty would be [])
}
````

### Fields:

* **status** *(integer)*: HTTP status code (`200`, `400`, `500`, etc.)
* **message** *(string)*: A short description of the result (`"Success"`, `"Error"`).
* **data** *(object | array)*: The actual response content . If no data, it should be the empty form of that content.

---

## Example Responses:

### Success (List of Items)

```json
{
  "status": 200,
  "message": "Items retrieved successfully",
  "data": [
    { "implant_uuid": "1", "implant_name": "Item 1" },
    { "implant_uuid": "2", "implant_name": "Item 2" }
  ]
}
```

### Success (Single Item)

```json
{
  "status": 200,
  "message": "Item created successfully",
  "data": { "implant_uuid": "1", "implant_name": "Item 1" }
}
```

### Client Error (Bad Request)

```json
{
  "status": 400,
  "message": "Invalid input",
  "data": null
}
```

### Server Error (Internal)

```json
{
  "status": 500,
  "message": "Internal server error",
  "data": null
}
```
