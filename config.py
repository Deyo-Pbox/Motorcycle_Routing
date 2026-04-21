import os
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Flask Configuration
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = True

# Google Maps API Key
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Study Area and Network Configuration
STUDY_AREA = "Naga, Camarines Sur, Philippines"
NETWORK_FILE = "data/osm/naga_network.graphml"

# Multiple study areas using bounding boxes (north, south, east, west)
# Format: (name, (north, south, east, west)) or just name
# Coordinates approximately for Camarines Sur municipalities
MULTIPLE_STUDY_AREAS = [
    ("Ocampo", (13.75, 13.68, 123.35, 123.25)),  # bbox for Ocampo
    ("Tigaon", (13.58, 13.50, 123.28, 123.18)),  # bbox for Tigaon
    ("Goa", (13.82, 13.75, 123.38, 123.30))      # bbox for Goa
]
MULTIPLE_NETWORK_FILE = "data/osm/ocampo_tigaon_goa_network.graphml"

# Road Speed Configuration (km/h)
ROAD_SPEEDS = {
    "motorway": 100,
    "trunk": 90,
    "primary": 80,
    "secondary": 70,
    "tertiary": 60,
    "unclassified": 50,
    "residential": 40,
    "service": 30,
    "living_street": 30,  # Minimum speed on local streets
    "default": 30  # Fallback minimum speed
}

# Lane Splitting Configuration
MIN_LANE_WIDTH = 3.5  # meters
MIN_LANE_COUNT = 2  # minimum lanes for lane splitting to be feasible
LANE_SPLIT_SPEED_MULTIPLIER = 1.2  # motorcycles travel 20% faster when lane splitting


def download_network(force_reload=False):
    if os.path.exists(NETWORK_FILE) and not force_reload:
        print(f"[DataLoader] Loading cached network from {NETWORK_FILE}")
        G = ox.load_graphml(NETWORK_FILE)
        print(f"[DataLoader] Loaded: {len(G.nodes)} nodes, {len(G.edges)} edges")
        return G

    print(f"[DataLoader] Downloading network for: {STUDY_AREA}")
    print("[DataLoader] This may take 2-5 minutes...")

    G = ox.graph_from_place(
        STUDY_AREA,
        network_type="drive",
        simplify=True,
        retain_all=False
    )

    # Manually assign speeds - avoids OSMnx + Python 3.14 maxspeed float bug
    for u, v, k, data in G.edges(data=True, keys=True):
        highway = data.get("highway", "residential")
        if isinstance(highway, list):
            highway = highway[0]
        speed = ROAD_SPEEDS.get(highway, ROAD_SPEEDS["default"])
        data["speed_kph"] = speed
        length = data.get("length", 0)
        if speed > 0:
            data["travel_time"] = (length / 1000) / speed * 3600
        else:
            data["travel_time"] = 999

    os.makedirs(os.path.dirname(NETWORK_FILE), exist_ok=True)
    ox.save_graphml(G, NETWORK_FILE)
    print(f"[DataLoader] Saved to {NETWORK_FILE}")
    print(f"[DataLoader] {len(G.nodes)} nodes, {len(G.edges)} edges")

    has_geom = sum(1 for _, _, d in G.edges(data=True) if 'geometry' in d)
    total = G.number_of_edges()
    print(f"[DataLoader] Geometry coverage: {has_geom}/{total} edges ({round(has_geom/total*100)}%)")

    return G


def inspect_network(G):
    all_keys = set()
    for u, v, data in G.edges(data=True):
        all_keys.update(data.keys())
    print("\nAvailable edge attributes:")
    for key in sorted(all_keys):
        print(f"  - {key}")

    print("\nSample edges:")
    for i, (u, v, data) in enumerate(G.edges(data=True)):
        print(f"\nEdge {i}: {u} -> {v}")
        for k, val in data.items():
            print(f"  {k}: {val}")
        if i >= 2:
            break


if __name__ == "__main__":
    G = download_network()
    inspect_network(G)