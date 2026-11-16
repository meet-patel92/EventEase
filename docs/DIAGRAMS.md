# EventEase Diagrams

The diagrams use Mermaid and are intended to remain editable alongside the source. Database relationships shown are based on model foreign keys and uniqueness constraints.

## System architecture

```mermaid
flowchart LR
  Browser[User browser / React SPA]
  API[Django REST Framework API]
  Auth[SimpleJWT authentication and role/ownership permissions]
  ORM[Django ORM]
  DB[(MySQL application database)]
  QR[QR generation and PDF ticket response]
  RP[Razorpay test-mode API integration]
  Schema[drf-spectacular OpenAPI / Swagger / Redoc]
  Browser -->|HTTP JSON / bearer token| API
  API --> Auth
  API --> ORM --> DB
  API --> QR
  API -->|test-mode order/signature flow| RP
  Schema --> API
  Browser -->|OpenAPI docs in development| Schema
```

## ER diagram

```mermaid
erDiagram
  USER ||--o{ EVENT : organizes
  EVENT_CATEGORY o|--o{ EVENT : categorizes
  USER ||--o{ BOOKING : places
  EVENT ||--o{ BOOKING : receives
  BOOKING ||--o{ PAYMENT : has
  USER ||--o{ PAYMENT : customer
  BOOKING o|--o{ TICKET : issues
  PAYMENT o|--o{ TICKET : relates_to
  USER o|--o{ TICKET : attendee
  EVENT o|--o{ TICKET : for_event
  USER ||--o{ REVIEW : writes
  EVENT ||--o{ REVIEW : receives
  USER ||--o{ NOTIFICATION : receives

  USER {
    int id PK
    string email UK
    string role
  }
  EVENT_CATEGORY {
    int id PK
    string name UK
  }
  EVENT {
    int id PK
    int organizer_id FK
    int category_id FK "nullable"
    string slug UK
    string status
    int total_tickets
    int available_tickets
  }
  BOOKING {
    int id PK
    int customer_id FK
    int event_id FK
    string reference UK
    int quantity
    string status
  }
  PAYMENT {
    int id PK
    int booking_id FK
    int customer_id FK
    string status
    string razorpay_order_id
  }
  TICKET {
    int id PK
    int booking_id FK "nullable"
    int payment_id FK "nullable"
    int customer_id FK "nullable"
    int event_id FK "nullable"
    string ticket_number UK
    string token UK
    string status
  }
  REVIEW {
    int id PK
    int user_id FK
    int event_id FK
    int rating
    string user_event_unique
  }
  NOTIFICATION {
    int id PK
    int user_id FK
    string delivery_type
    string delivery_status
    boolean is_read
  }
  DASHBOARD_STAT {
    int id PK
    string name
    decimal value
    date date
  }
```

DashboardStat is standalone and intentionally has no relationship line. The database enforces unique review per user/event. Ticket foreign keys are nullable in the model. Payment-to-booking is one-to-many at the schema level.

## DFD Level 0 (context)

```mermaid
flowchart LR
  Customer[Customer]
  Organizer[Organizer]
  Admin[Administrator]
  Provider[Razorpay test provider]
  System((EventEase system))
  Store[(Application database)]
  Customer -->|registration, event queries, booking, payment proof, review| System
  System -->|event details, booking status, QR/PDF ticket, notifications| Customer
  Organizer -->|event management, scanner verification| System
  System -->|event/dashboard results, ticket validation result| Organizer
  Admin -->|event approval/rejection, administration| System
  System -->|system summaries and records| Admin
  System -->|test order request / signature verification| Provider
  Provider -->|test order data| System
  System <--> Store
```

## DFD Level 1

```mermaid
flowchart LR
  C[Customer] --> P1((1. Accounts and authentication))
  O[Organizer] --> P1
  A[Admin] --> P1
  P1 <--> D1[(Users)]
  C --> P2((2. Browse and manage events))
  O --> P2
  A --> P2
  P2 <--> D2[(Categories and events)]
  C --> P3((3. Booking and cancellation))
  P3 <--> D3[(Bookings)]
  P3 --> P4((4. Payment order and verification))
  P4 <--> D4[(Payments)]
  P4 <--> RP[Razorpay test mode]
  P4 --> P5((5. Ticket issue and verification))
  P5 <--> D5[(Tickets)]
  P5 -->|QR/PDF or check-in result| C
  O -->|scan ticket| P5
  C --> P6((6. Reviews and notifications))
  P6 <--> D6[(Reviews and notifications)]
  C --> P7((7. Dashboards))
  O --> P7
  A --> P7
  P7 --> D2
  P7 --> D3
  P7 --> D4
  P7 --> D5
```

## Use case diagram

```mermaid
flowchart LR
  Customer[Customer]
  Organizer[Organizer]
  Admin[Administrator]
  subgraph EE[EventEase]
    Browse([Browse events and details])
    Register([Register / sign in])
    Book([Book or cancel seats])
    Pay([Create/verify test payment])
    Ticket([View/download ticket])
    Review([Submit event review])
    Notify([View notifications])
    Dash([View role dashboard])
    Manage([Manage organizer events via API])
    Scan([Scan and verify ticket])
    Approve([Approve/reject events])
  end
  Customer --> Browse
  Customer --> Register
  Customer --> Book
  Customer --> Pay
  Customer --> Ticket
  Customer --> Review
  Customer --> Notify
  Customer --> Dash
  Organizer --> Register
  Organizer --> Dash
  Organizer --> Manage
  Organizer --> Scan
  Admin --> Register
  Admin --> Dash
  Admin --> Approve
  Admin --> Scan
```

Event creation/approval are represented as backend/API/admin workflows; a dedicated React authoring/approval interface is not currently implemented.
