"""
In-memory store — acts as the shared data layer.
Replace with MongoDB (Motor) or PostgreSQL (asyncpg) for production.
"""

store: dict = {
    "users": {},       # user_id -> user dict
    "alerts": {},      # alert_id -> alert dict
    "incidents": {},   # incident_id -> incident dict
    "safe_routes": {}, # route_id -> route dict
    "contacts": {},    # user_id -> list of contacts
    "sessions": {},    # user_id -> latest location
}
