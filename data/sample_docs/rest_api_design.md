# REST API Design Principles

REST (Representational State Transfer) is an architectural style for designing networked applications. RESTful APIs use HTTP requests to perform CRUD (Create, Read, Update, Delete) operations on resources.

## Core Principles

### Resource-Based

REST organizes data and functionality into resources, identified by URIs (Uniform Resource Identifiers). Resources are nouns, not verbs.

Good:
```
GET /users/123
GET /orders/456
POST /products
```

Bad:
```
GET /getUser?id=123
POST /createOrder
GET /fetchProducts
```

### HTTP Methods

Use appropriate HTTP methods for different operations:

**GET**: Retrieve a resource or collection
- Idempotent (same result on multiple calls)
- No side effects
- Cacheable

**POST**: Create a new resource
- Not idempotent
- Can have side effects
- Returns 201 Created with Location header

**PUT**: Update/replace an entire resource
- Idempotent
- Requires full resource representation

**PATCH**: Partially update a resource
- Not necessarily idempotent
- Only includes changed fields

**DELETE**: Remove a resource
- Idempotent
- Returns 204 No Content

**HEAD**: Get metadata without body
- Like GET but without response body

**OPTIONS**: Get supported methods
- Used for CORS preflight requests

## HTTP Status Codes

Status codes communicate the result of an API request.

### 2xx Success

- **200 OK**: Request succeeded (GET, PUT, PATCH)
- **201 Created**: Resource created (POST)
- **202 Accepted**: Request accepted for processing
- **204 No Content**: Success with no response body (DELETE)

### 3xx Redirection

- **301 Moved Permanently**: Resource permanently moved
- **302 Found**: Temporary redirect
- **304 Not Modified**: Cached version is still valid

### 4xx Client Errors

- **400 Bad Request**: Invalid request syntax
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Authenticated but not authorized
- **404 Not Found**: Resource doesn't exist
- **405 Method Not Allowed**: HTTP method not supported
- **409 Conflict**: Request conflicts with current state
- **422 Unprocessable Entity**: Validation failed
- **429 Too Many Requests**: Rate limit exceeded

### 5xx Server Errors

- **500 Internal Server Error**: Generic server error
- **502 Bad Gateway**: Invalid response from upstream
- **503 Service Unavailable**: Server temporarily unavailable
- **504 Gateway Timeout**: Upstream server timeout

## URL Design

### Collection and Resource Patterns

```
GET    /users          # List all users
POST   /users          # Create new user
GET    /users/123      # Get specific user
PUT    /users/123      # Update entire user
PATCH  /users/123      # Update user fields
DELETE /users/123      # Delete user
```

### Nested Resources

```
GET /users/123/orders        # User's orders
GET /users/123/orders/456    # Specific order
POST /users/123/orders       # Create order for user
```

### Filtering and Sorting

Use query parameters for filtering, sorting, and pagination:

```
GET /products?category=electronics
GET /products?sort=price_asc
GET /products?min_price=100&max_price=500
```

### Pagination

```
GET /users?page=2&limit=20
GET /users?offset=40&limit=20
```

Response should include pagination metadata:
```json
{
  "data": [...],
  "meta": {
    "total": 150,
    "page": 2,
    "limit": 20,
    "total_pages": 8
  }
}
```

## Versioning

### URL Versioning

Most common and explicit:
```
https://api.example.com/v1/users
https://api.example.com/v2/users
```

### Header Versioning

```
GET /users
Accept: application/vnd.myapi.v1+json
```

### Query Parameter Versioning

```
GET /users?version=1
```

## Request and Response Formats

### JSON is Standard

Use JSON for request and response bodies. Set appropriate Content-Type headers:

```
Content-Type: application/json
Accept: application/json
```

### Request Body Example

```json
POST /users
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "admin"
}
```

### Response Body Example

```json
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com",
  "role": "admin",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Error Response Format

Consistent error format helps clients handle errors:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": {
      "field": "email",
      "value": "invalid-email"
    }
  }
}
```

## Authentication

### API Keys

Simple but less secure:
```
GET /users
Authorization: ApiKey YOUR_API_KEY
```

### Bearer Tokens (JWT)

Most common for modern APIs:
```
GET /users
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### OAuth 2.0

For third-party access:
- Authorization Code Flow (web apps)
- Client Credentials Flow (service-to-service)
- Implicit Flow (deprecated)
- PKCE (mobile apps)

## CORS

Cross-Origin Resource Sharing allows browsers to make cross-domain requests.

Headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

## Rate Limiting

Protect your API from abuse with rate limiting.

Headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1629800000
```

Return 429 when limit exceeded:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after": 60
  }
}
```

## Caching

Use HTTP caching headers to improve performance.

### Cache-Control

```
Cache-Control: public, max-age=3600
Cache-Control: private, no-cache
Cache-Control: no-store
```

### ETags

```
Response:
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"

Next Request:
If-None-Match: "33a64df551425fcc55e4d42a148795d9f25f89d4"

Response:
304 Not Modified
```

### Last-Modified

```
Response:
Last-Modified: Wed, 15 Jan 2024 10:30:00 GMT

Next Request:
If-Modified-Since: Wed, 15 Jan 2024 10:30:00 GMT

Response:
304 Not Modified
```

## HATEOAS

Hypermedia as the Engine of Application State - include links to related resources in responses.

```json
{
  "id": 123,
  "name": "John Doe",
  "links": {
    "self": "/users/123",
    "orders": "/users/123/orders",
    "avatar": "/users/123/avatar"
  }
}
```

## Best Practices

1. **Use Nouns, Not Verbs**: Resources are nouns (users, orders), actions are HTTP methods
2. **Plural Names**: Use plural for collections (/users, not /user)
3. **Consistent Naming**: Use lowercase, hyphens for multi-word (kebab-case)
4. **Stateless**: Each request contains all necessary information
5. **Idempotency**: GET, PUT, DELETE should be idempotent
6. **Pagination**: Always paginate large collections
7. **Filtering**: Use query parameters for filtering
8. **Documentation**: Provide comprehensive API documentation (OpenAPI/Swagger)
9. **Versioning**: Version your API from the start
10. **Error Handling**: Return meaningful error messages with appropriate status codes

Following these REST API design principles ensures your API is intuitive, scalable, and easy to maintain.
