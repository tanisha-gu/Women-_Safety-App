"""
Incidents routes: /api/incidents — report & retrieve incidents
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_utils import get_current_user_id
from store import store

router = APIRouter()


class IncidentReportRequest(BaseModel):
    type: str = "GENERAL"           # HARASSMENT | ASSAULT | SUSPICIOUS | GENERAL
    description: str = ""
    lat: float
    lng: float
    severity: str = "MEDIUM"        # LOW | MEDIUM | HIGH | CRITICAL
    anonymous: bool = False


@router.post("/report", status_code=201)
async def report_incident(body: IncidentReportRequest, user_id: str = Depends(get_current_user_id)):
    incident_id = str(uuid.uuid4())
    incident = {
        "id": incident_id,
        "user_id": None if body.anonymous else user_id,
        "type": body.type,
        "description": body.description,
        "severity": body.severity,
        "location": {"lat": body.lat, "lng": body.lng},
        "status": "OPEN",
        "geotagged": True,
        "timestamped": True,
        "timestamp": datetime.utcnow().isoformat(),
        "anonymous": body.anonymous,
    }
    store["incidents"][incident_id] = incident
    return {"success": True, "incident_id": incident_id, "timestamp": incident["timestamp"]}


@router.get("/my")
async def get_my_incidents(user_id: str = Depends(get_current_user_id)):
    incidents = [
        i for i in store["incidents"].values()
        if i.get("user_id") == user_id
    ]
    return sorted(incidents, key=lambda i: i["timestamp"], reverse=True)


@router.get("/nearby")
async def get_nearby_incidents(lat: float, lng: float, radius_km: float = 5.0,
                                user_id: str = Depends(get_current_user_id)):
    import math

    def haversine(lat1, lng1, lat2, lng2):
        R = 6371
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lng2 - lng1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    nearby = []
    for i in store["incidents"].values():
        loc = i.get("location", {})
        dist = haversine(lat, lng, loc.get("lat", 0), loc.get("lng", 0))
        if dist <= radius_km:
            nearby.append({**i, "distance_km": round(dist, 3)})

    return sorted(nearby, key=lambda i: i["distance_km"])


@router.get("/{incident_id}")
async def get_incident(incident_id: str, user_id: str = Depends(get_current_user_id)):
    incident = store["incidents"].get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
