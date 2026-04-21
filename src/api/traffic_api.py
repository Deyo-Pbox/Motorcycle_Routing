import requests
from config import GOOGLE_MAPS_API_KEY


def get_traffic_speed(origin_lat, origin_lon, dest_lat, dest_lon):
    if not GOOGLE_MAPS_API_KEY:
        return None

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_lat},{origin_lon}",
        "destination": f"{dest_lat},{dest_lon}",
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": GOOGLE_MAPS_API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data.get("status") != "OK":
            return None

        route = data["routes"][0]["legs"][0]
        distance_m = route["distance"]["value"]
        duration_in_traffic_s = route.get("duration_in_traffic", {}).get("value")

        if duration_in_traffic_s and distance_m:
            speed_mps = distance_m / duration_in_traffic_s
            speed_kph = speed_mps * 3.6
            return round(speed_kph, 1)

    except Exception as e:
        print(f"[TrafficAPI] Error: {e}")

    return None


def get_google_maps_route_time(origin_lat, origin_lon, dest_lat, dest_lon):
    if not GOOGLE_MAPS_API_KEY:
        return None

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_lat},{origin_lon}",
        "destination": f"{dest_lat},{dest_lon}",
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": GOOGLE_MAPS_API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data.get("status") != "OK":
            return None

        leg = data["routes"][0]["legs"][0]
        duration_s = leg.get("duration_in_traffic", leg["duration"])["value"]
        distance_m = leg["distance"]["value"]

        return {
            "duration_min": round(duration_s / 60, 1),
            "distance_km": round(distance_m / 1000, 2),
        }

    except Exception as e:
        print(f"[TrafficAPI] Google Maps route error: {e}")

    return None