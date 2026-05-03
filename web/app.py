import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
import osmnx as ox
import networkx as nx

from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, GOOGLE_MAPS_API_KEY
from src.data_loader import download_network
from src.algorithms.route_calculator import (
    astar_motorcycle,
    dijkstra_motorcycle,
    path_to_coordinates,
    get_lane_split_segments
)

app = Flask(__name__, template_folder="templates", static_folder="static")

print("[App] Loading road network...")
G = download_network()
print("[App] Road network ready.")


def snap_to_nearest_node(G, lat, lon):
    """
    Snaps a coordinate to the nearest graph node.
    Uses nearest edge for better accuracy than nearest node alone.
    """
    try:
        nearest = ox.nearest_edges(G, X=lon, Y=lat)
        u, v, _ = nearest
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        dist_u = ((u_data['y'] - lat)**2 + (u_data['x'] - lon)**2)**0.5
        dist_v = ((v_data['y'] - lat)**2 + (v_data['x'] - lon)**2)**0.5
        return u if dist_u < dist_v else v
    except Exception:
        return ox.nearest_nodes(G, X=lon, Y=lat)


@app.route("/")
def index():
    return render_template("index.html", api_key=GOOGLE_MAPS_API_KEY)


@app.route("/api/route", methods=["POST"])
def calculate_route():
    data = request.get_json()

    try:
        origin_lat = float(data["origin_lat"])
        origin_lon = float(data["origin_lon"])
        dest_lat = float(data["dest_lat"])
        dest_lon = float(data["dest_lon"])
        algorithm = data.get("algorithm", "astar")
        waypoints = data.get("waypoints", [])
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400

    try:
        # Build complete route: origin -> waypoints -> destination
        all_points = [
            (origin_lat, origin_lon),
            *[(wp["lat"], wp["lon"]) for wp in waypoints],
            (dest_lat, dest_lon)
        ]
        
        # Snap all points to nearest nodes
        all_nodes = [snap_to_nearest_node(G, lat, lon) for lat, lon in all_points]
        
        # Check for duplicate consecutive points
        for i in range(len(all_nodes) - 1):
            if all_nodes[i] == all_nodes[i + 1]:
                return jsonify({"error": "Two consecutive points are too close. Please choose different locations."}), 400

        # Google Maps API: get real-time traffic speed
        from src.api.traffic_api import get_traffic_speed
        traffic_speed = get_traffic_speed(origin_lat, origin_lon, dest_lat, dest_lon)
        traffic_source = "Google Maps API (real-time)" if traffic_speed else "OSM road type estimate"
        if traffic_speed:
            print(f"[App] Traffic speed from Google Maps: {traffic_speed} kph")
        else:
            print("[App] Google Maps unavailable, using OSM speed estimates")

        # Apply traffic speed to all edges
        traffic_speeds = {}
        if traffic_speed:
            for u, v, k in G.edges(keys=True):
                traffic_speeds[f"{u}_{v}_{k}"] = traffic_speed

        # Calculate routes between consecutive points
        full_path = []
        all_coordinates = []
        all_lane_split_segs = []
        total_distance_m = 0
        total_time_sec = 0
        total_lane_split_segments = 0
        total_segments = 0

        for i in range(len(all_nodes) - 1):
            current_node = all_nodes[i]
            next_node = all_nodes[i + 1]
            
            # Run selected algorithm
            if algorithm == "dijkstra":
                result = dijkstra_motorcycle(G, current_node, next_node, traffic_speeds)
            else:
                result = astar_motorcycle(G, current_node, next_node, traffic_speeds)
            
            path = result["path"]
            
            # Avoid duplicate nodes at waypoint connections
            if i > 0 and full_path and full_path[-1] == path[0]:
                path = path[1:]
            
            full_path.extend(path)
            
            # Get coordinates for this segment
            segment_coords = path_to_coordinates(G, path)
            all_coordinates.extend(segment_coords)
            
            # Get lane split segments
            segment_lane_splits = get_lane_split_segments(G, path, traffic_speeds)
            all_lane_split_segs.extend(segment_lane_splits)
            
            # Accumulate stats
            total_distance_m += result["total_distance_m"]
            total_time_sec += result["total_time_sec"]
            total_lane_split_segments += result["lane_split_segments"]
            total_segments += result["total_segments"]

        distance_km = round(total_distance_m / 1000, 2)
        time_min = round(total_time_sec / 60, 1)
        ls_pct = 0
        if total_segments > 0:
            ls_pct = round(total_lane_split_segments / total_segments * 100, 1)

        # Check what OSM attributes are available
        osm_attributes = []
        sample_edges = list(G.edges(data=True))[:20]
        has_width = any("width" in d for _, _, d in sample_edges)
        has_lanes = any("lanes" in d for _, _, d in sample_edges)
        has_maxspeed = any("maxspeed" in d for _, _, d in sample_edges)
        if has_width:
            osm_attributes.append("Lane widths")
        if has_lanes:
            osm_attributes.append("Lane counts")
        if has_maxspeed:
            osm_attributes.append("Speed limits")
        osm_attributes.append("Road types")
        osm_attributes.append("Road geometry")

        # Get actual snapped coordinates
        origin_snapped = G.nodes[all_nodes[0]]
        dest_snapped = G.nodes[all_nodes[-1]]

        response = {
            "success": True,
            "algorithm": algorithm,
            "coordinates": all_coordinates,
            "lane_split_segments": all_lane_split_segs,
            "snapped": {
                "origin": [origin_snapped["y"], origin_snapped["x"]],
                "dest": [dest_snapped["y"], dest_snapped["x"]],
            },
            "stats": {
                "distance_km": distance_km,
                "time_min": time_min,
                "lane_split_count": total_lane_split_segments,
                "total_segments": total_segments,
                "lane_split_pct": ls_pct,
            },
            "data_sources": {
                "osm": {
                    "status": "active",
                    "nodes": len(G.nodes),
                    "edges": len(G.edges),
                    "attributes": osm_attributes,
                },
                "google_maps": {
                    "status": "active" if traffic_speed else "unavailable",
                    "used_for": "Real-time traffic speed for routing",
                    "traffic_speed_kph": traffic_speed,
                    "traffic_source": traffic_source
                }
            }
        }

        return jsonify(response)

    except nx.NetworkXNoPath:
        return jsonify({
            "error": "No route found. Try choosing points on connected roads."
        }), 404
    except Exception as e:
        print(f"[App] Route error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Routing failed: {str(e)}"}), 500


@app.route("/api/network-info")
def network_info():
    return jsonify({
        "nodes": len(G.nodes),
        "edges": len(G.edges),
        "study_area": "Naga, Camarines Sur, Philippines"
    })


@app.route("/api/traffic-congestion", methods=["GET"])
def get_traffic_congestion():
    """Get traffic congestion level for route (green/yellow/red)"""
    origin_lat = request.args.get("origin_lat", type=float)
    origin_lon = request.args.get("origin_lon", type=float)
    dest_lat = request.args.get("dest_lat", type=float)
    dest_lon = request.args.get("dest_lon", type=float)
    
    if not all([origin_lat, origin_lon, dest_lat, dest_lon]):
        return jsonify({"error": "Missing coordinates"}), 400
    
    try:
        from src.api.traffic_api import get_traffic_congestion
        congestion_level = get_traffic_congestion(origin_lat, origin_lon, dest_lat, dest_lon)
        return jsonify({
            "congestion": congestion_level,
            "color_map": {
                "green": "#22c55e",    # Green - free flowing
                "yellow": "#eab308",   # Yellow - moderate congestion
                "red": "#ef4444"       # Red - heavy congestion
            }
        })
    except Exception as e:
        print(f"[App] Congestion error: {e}")
        return jsonify({"congestion": "green"}), 200  # Default to green


@app.route("/api/roads")
def get_roads():
    features = []
    for u, v, data in G.edges(data=True):
        highway = data.get("highway", "unclassified")
        if isinstance(highway, list):
            highway = highway[0]
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        feature = {
            "type": "Feature",
            "properties": {"highway": highway},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [u_data["x"], u_data["y"]],
                    [v_data["x"], v_data["y"]],
                ]
            }
        }
        features.append(feature)
    return jsonify({"type": "FeatureCollection", "features": features})


@app.route("/api/bounds")
def get_bounds():
    """Get the geographic bounds of the road network"""
    if len(G.nodes) == 0:
        return jsonify({"error": "No network data"}), 404
    
    lats = [G.nodes[node]["y"] for node in G.nodes]
    lons = [G.nodes[node]["x"] for node in G.nodes]
    
    bounds = {
        "min_lat": min(lats),
        "max_lat": max(lats),
        "min_lon": min(lons),
        "max_lon": max(lons),
    }
    
    return jsonify(bounds)


@app.route("/api/search-places", methods=["GET"])
def search_places():
    """Search for places and establishments using Nominatim API"""
    query = request.args.get("q", "").strip()
    
    if not query or len(query) < 2:
        return jsonify({"error": "Query too short"}), 400
    
    try:
        import requests
        # Search using Nominatim (OpenStreetMap)
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "format": "json",
                "q": query,
                "limit": 10,
                "countrycodes": "ph"  # Focus on Philippines
            },
            headers={"User-Agent": "MotoRoute/1.0"}
        )
        
        if response.status_code == 200:
            results = response.json()
            return jsonify({
                "results": [
                    {
                        "name": r.get("display_name", "").split(",")[0],
                        "display_name": r.get("display_name", ""),
                        "lat": float(r["lat"]),
                        "lon": float(r["lon"]),
                        "type": r.get("type", "unknown"),
                        "class": r.get("class", "unknown")
                    }
                    for r in results
                ]
            })
        else:
            return jsonify({"error": "Search failed"}), 500
            
    except Exception as e:
        print(f"[App] Search error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)