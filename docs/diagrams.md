# Diagrams & export instructions

## System diagram (ASCII)

Frontend (Streamlit)  <--HTTPS-->  FastAPI Backend  <--SQLAlchemy-->  PostgreSQL
     |
     +--> Power Automate (webhooks)
     +--> Optional: LLM services (OpenAI)

## Mermaid example for create-order
Paste this at https://mermaid.live to export PNG/SVG:

```mermaid
sequenceDiagram
    participant U as User (Streamlit)
    participant S as Streamlit UI
    participant API as FastAPI
    participant DB as PostgreSQL
    U->>S: Click Submit
    S->>API: POST /api/v1/orders (payload)
    API->>DB: BEGIN TX
    API->>DB: SELECT FOR UPDATE product rows
    DB-->>API: product rows
    API->>DB: UPDATE product, INSERT order, INSERT order_items, INSERT inventory_log
    API->>DB: COMMIT
    API-->>S: 201 Created
    S-->>U: Show success
```
