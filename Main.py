"""
SHIELD Women Safety App — Python Backend
FastAPI + Socket.IO + In-Memory Store (MongoDB-ready)
"""

import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
import socketio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from store import store
from routes.auth import router as auth_router
from routes.sos import router as sos_router, set_sio
from routes.location import router as location_router
from routes.incidents import router as incidents_router
from routes.contacts import router as contacts_router
from routes.safe_routes import router as safe_routes_router
from routes.police import router as police_router
from routes.ai import router as ai_router

# ─── Socket.IO ────────────────────────────────────────────────────────────────
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# Pass sio to routes that need it
set_sio(sio)

# ─── FastAPI App ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed demo data
    store["users"]["demo-user-001"] = {
        "id": "demo-user-001",
        "name": "Priya Sharma",
        "email": "priya@shield.app",
        "phone": "+91-9876543210",
        "password_hash": "$2b$12$KIXa3V7LJp5VrY3G4k1OeOV3yVHPHoKK5xNtGHxfLFn3nJMRKk5zy",  # "demo123"
        "emergency_contacts": [
            {"name": "Mom", "phone": "+91-9876543211", "relation": "Mother"},
            {"name": "Rahul", "phone": "+91-9876543212", "relation": "Brother"},
        ],
        "safe_zones": [
            {"lat": 28.6139, "lng": 77.2090, "radius": 500, "label": "Home"},
            {"lat": 28.6304, "lng": 77.2177, "radius": 300, "label": "Office"},
        ],
        "created_at": datetime.utcnow().isoformat(),
    }
    print("\n🛡️  SHIELD Backend (Python) starting...")
    yield
    print("🛡️  SHIELD Backend shutting down.")


app = FastAPI(
    title="SHIELD Women Safety API",
    version="1.0.0",
    description="AI-powered women's safety backend with real-time alerts",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router,         prefix="/api/auth",      tags=["Auth"])
app.include_router(sos_router,          prefix="/api/sos",       tags=["SOS"])
app.include_router(location_router,     prefix="/api/location",  tags=["Location"])
app.include_router(incidents_router,    prefix="/api/incidents", tags=["Incidents"])
app.include_router(contacts_router,     prefix="/api/contacts",  tags=["Contacts"])
app.include_router(safe_routes_router,  prefix="/api/routes",    tags=["Safe Routes"])
app.include_router(police_router,       prefix="/api/police",    tags=["Police"])
app.include_router(ai_router,           prefix="/api/ai",        tags=["AI"])


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "operational",
        "version": "1.0.0",
        "app": "SHIELD Women Safety (Python)",
        "uptime_seconds": time.time(),
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "sos": True,
            "live_tracking": True,
            "ai_detection": True,
            "safe_routes": True,
            "offline_sms": True,
            "police_portal": True,
        },
    }


@app.get("/")
async def root():
    return {"message": "🛡️ SHIELD API Running", "docs": "/docs", "health": "/api/health"}


# ─── Socket.IO Events ─────────────────────────────────────────────────────────
@sio.event
async def connect(sid, environ):
    print(f"📡 Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"📡 Client disconnected: {sid}")


@sio.event
async def join_user_room(sid, user_id):
    await sio.enter_room(sid, f"user:{user_id}")
    print(f"User {user_id} joined their room")


@sio.event
async def join_police_room(sid, data=None):
    await sio.enter_room(sid, "police-control-room")
    print("Police joined control room")


@sio.event
async def location_update(sid, data):
    user_id = data.get("userId")
    lat = data.get("lat")
    lng = data.get("lng")
    if user_id:
        store["sessions"][user_id] = {
            "lat": lat, "lng": lng,
            "accuracy": data.get("accuracy"),
            "speed": data.get("speed"),
            "heading": data.get("heading"),
            "ts": int(time.time() * 1000),
        }
        payload = {
            "userId": user_id, "lat": lat, "lng": lng,
            "accuracy": data.get("accuracy"),
            "speed": data.get("speed"),
            "heading": data.get("heading"),
            "ts": int(time.time() * 1000),
        }
        await sio.emit("location-update", payload, room=f"user:{user_id}-watchers")
        await sio.emit("user-location", {"userId": user_id, "lat": lat, "lng": lng, "ts": int(time.time() * 1000)}, room="police-control-room")


@sio.event
async def sos_trigger(sid, data):
    alert_id = str(uuid.uuid4())
    alert = {**data, "id": alert_id, "ts": int(time.time() * 1000), "status": "ACTIVE"}
    store["alerts"][alert_id] = alert
    await sio.emit("sos-alert", alert, room="police-control-room")
    await sio.emit("sos-alert", alert, room=f"user:{data.get('userId')}-watchers")
    await sio.emit("sos-nearby", {"lat": data.get("lat"), "lng": data.get("lng"), "radius": 500}, skip_sid=sid)
    print(f"🚨 SOS triggered by user {data.get('userId')}")


@sio.event
async def audio_chunk(sid, data):
    await sio.emit("analyze-audio", data, room="ai-analysis")


# ─── Mount Socket.IO ──────────────────────────────────────────────────────────
socket_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="/socket.io")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🛡️  SHIELD Backend running on port {port}")
    print(f"📡 WebSocket enabled")
    print(f"📖 API Docs: http://localhost:{port}/docs\n")
    uvicorn.run("main:socket_app", host="0.0.0.0", port=port, reload=True)
