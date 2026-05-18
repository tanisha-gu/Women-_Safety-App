"""
AI routes: /api/ai/analyze-audio, /analyze-movement, /safe-route, /risk-assessment
"""

import math
import random
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth_utils import get_current_user_id

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────
class AudioAnalysisRequest(BaseModel):
    audio_features: dict = {}
    duration: float = 0
    amplitude: float = 0
    frequency_data: list[float] = []


class MovementAnalysisRequest(BaseModel):
    accelerometer_data: list[dict] = []
    gyroscope_data: list[dict] = []
    location_history: list[dict] = []


class SafeRouteRequest(BaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    time_of_day: int | None = None


class RiskAssessmentRequest(BaseModel):
    lat: float
    lng: float
    time_of_day: int | None = None


# ─── Analysis Logic ───────────────────────────────────────────────────────────
def _analyze_audio(amplitude: float, duration: float, frequency_data: list) -> dict:
    """
    Simulated audio threat detection.
    Production: use a trained TensorFlow/PyTorch model for scream detection.
    """
    high_freq_count = sum(1 for f in frequency_data if f > 2000)
    high_freq_ratio = high_freq_count / max(len(frequency_data), 1)

    threat_detected = amplitude > 75 and high_freq_ratio > 0.4
    confidence = min(95.0, (amplitude / 100) * 60 + high_freq_ratio * 35)

    if threat_detected:
        threat_type = "SCREAM_DETECTED" if amplitude > 85 else "DISTRESS_SOUND"
        recommendation = "Immediate SOS recommended. Threat pattern detected in audio."
    elif amplitude > 60:
        threat_type = "ELEVATED_NOISE"
        recommendation = "Unusual sound level detected. Stay alert."
    else:
        threat_type = "NORMAL"
        recommendation = "No threat detected. Continue monitoring."

    return {
        "threat_detected": threat_detected,
        "confidence": round(confidence, 2),
        "threat_type": threat_type,
        "recommendation": recommendation,
    }


def _analyze_movement(accelerometer_data: list, gyroscope_data: list, location_history: list) -> dict:
    if len(accelerometer_data) < 3:
        return {
            "erratic_movement": False,
            "panic_indicator": False,
            "confidence": 0,
            "suggest_sos": False,
            "pattern": "INSUFFICIENT_DATA",
        }

    avg_magnitude = sum(
        abs(d.get("x", 0)) + abs(d.get("y", 0)) + abs(d.get("z", 0))
        for d in accelerometer_data
    ) / len(accelerometer_data)

    is_erratic = avg_magnitude > 15
    is_panic = avg_magnitude > 25

    return {
        "erratic_movement": is_erratic,
        "panic_indicator": is_panic,
        "confidence": round(min(avg_magnitude * 3, 95), 2),
        "suggest_sos": is_panic,
        "pattern": "PANIC_MOVEMENT" if is_panic else ("ERRATIC_MOVEMENT" if is_erratic else "NORMAL"),
    }


def _generate_safe_routes(start: dict, end: dict, time_of_day: int) -> list:
    is_night = time_of_day < 6 or time_of_day > 21
    mid_lat = (start["lat"] + end["lat"]) / 2
    mid_lng = (start["lng"] + end["lng"]) / 2

    routes = [
        {
            "id": "route-1",
            "name": "Safest Route",
            "distance": "2.3 km",
            "duration": "28 min",
            "safety_score": 72 if is_night else 91,
            "features": ["Well-lit streets", "CCTV coverage", "Populated areas", "Police beat"],
            "waypoints": [
                {"lat": start["lat"], "lng": start["lng"]},
                {"lat": mid_lat + 0.001, "lng": mid_lng},
                {"lat": end["lat"], "lng": end["lng"]},
            ],
            "warnings": ["Low visibility in sector 3"] if is_night else [],
        },
        {
            "id": "route-2",
            "name": "Fastest Route",
            "distance": "1.8 km",
            "duration": "22 min",
            "safety_score": 45 if is_night else 73,
            "features": ["Main road", "Some CCTV"],
            "waypoints": [
                {"lat": start["lat"], "lng": start["lng"]},
                {"lat": end["lat"], "lng": end["lng"]},
            ],
            "warnings": ["Poorly lit stretch near market"] if is_night else ["Less monitored"],
        },
        {
            "id": "route-3",
            "name": "Scenic Route",
            "distance": "2.8 km",
            "duration": "35 min",
            "safety_score": 60 if is_night else 82,
            "features": ["Shopping area", "High foot traffic"],
            "waypoints": [
                {"lat": start["lat"], "lng": start["lng"]},
                {"lat": start["lat"] + 0.005, "lng": start["lng"] + 0.003},
                {"lat": end["lat"], "lng": end["lng"]},
            ],
            "warnings": [],
        },
    ]
    return sorted(routes, key=lambda r: r["safety_score"], reverse=True)


def _calculate_risk(lat: float, lng: float, is_night: bool) -> dict:
    base_risk = 30
    night_bonus = 35 if is_night else 0
    variation = random.randint(-10, 10)
    risk_score = max(0, min(100, base_risk + night_bonus + variation))

    recommendations = []
    if risk_score > 70:
        recommendations += [
            "Share your live location with a trusted contact",
            "Stay in well-lit, crowded areas",
            "Consider alternative transport options",
        ]
    elif risk_score > 40:
        recommendations += [
            "Stay aware of your surroundings",
            "Keep your phone charged and accessible",
        ]
    if is_night:
        recommendations += [
            "Travel in groups if possible during night hours",
            "Inform someone about your route and ETA",
        ]
    recommendations.append("SHIELD is monitoring. Press SOS if you feel unsafe.")

    return {
        "risk_score": risk_score,
        "risk_level": "HIGH" if risk_score > 70 else ("MEDIUM" if risk_score > 40 else "LOW"),
        "is_night": is_night,
        "recommendations": recommendations,
    }


# ─── Routes ───────────────────────────────────────────────────────────────────
@router.post("/analyze-audio")
async def analyze_audio(body: AudioAnalysisRequest, user_id: str = Depends(get_current_user_id)):
    result = _analyze_audio(body.amplitude, body.duration, body.frequency_data)
    return {**result, "timestamp": datetime.utcnow().isoformat()}


@router.post("/analyze-movement")
async def analyze_movement(body: MovementAnalysisRequest, user_id: str = Depends(get_current_user_id)):
    result = _analyze_movement(body.accelerometer_data, body.gyroscope_data, body.location_history)
    return {**result, "timestamp": datetime.utcnow().isoformat()}


@router.post("/safe-route")
async def safe_route(body: SafeRouteRequest, user_id: str = Depends(get_current_user_id)):
    time_of_day = body.time_of_day if body.time_of_day is not None else datetime.utcnow().hour
    routes = _generate_safe_routes(
        {"lat": body.start_lat, "lng": body.start_lng},
        {"lat": body.end_lat, "lng": body.end_lng},
        time_of_day,
    )
    return {"routes": routes, "generated_at": datetime.utcnow().isoformat()}


@router.post("/risk-assessment")
async def risk_assessment(body: RiskAssessmentRequest, user_id: str = Depends(get_current_user_id)):
    time_of_day = body.time_of_day if body.time_of_day is not None else datetime.utcnow().hour
    is_night = time_of_day < 6 or time_of_day > 21
    result = _calculate_risk(body.lat, body.lng, is_night)
    return {**result, "location": {"lat": body.lat, "lng": body.lng},
            "timestamp": datetime.utcnow().isoformat()}
