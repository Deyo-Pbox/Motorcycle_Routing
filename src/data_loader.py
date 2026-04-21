import os
import osmnx as ox
import networkx as nx
from config import STUDY_AREA, NETWORK_FILE, ROAD_SPEEDS, MULTIPLE_STUDY_AREAS, MULTIPLE_NETWORK_FILE


def download_network(force_reload=False, multiple=False):
    """Download and cache network. Set multiple=True to merge Ocampo, Tigaon, Goa."""
    
    if multiple:
        return download_multiple_areas(force_reload)
    
    if os.path.exists(NETWORK_FILE) and not force_reload:
        print(f"[DataLoader] Loading cached network from {NETWORK_FILE}")
        G = ox.load_graphml(NETWORK_FILE)
        print(f"[DataLoader] Loaded: {len(G.nodes)} nodes, {len(G.edges)} edges")
        return G

    print(f"[DataLoader] Downloading network for: {STUDY_AREA}")
    print("[DataLoader] This may take 2-5 minutes...")

    # simplify=True keeps the graph clean but retains geometry on edges
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

    # Check geometry coverage
    has_geom = sum(1 for _, _, d in G.edges(data=True) if 'geometry' in d)
    total = G.number_of_edges()
    print(f"[DataLoader] Geometry coverage: {has_geom}/{total} edges ({round(has_geom/total*100)}%)")

    return G


def download_multiple_areas(force_reload=False):
    """Download and merge multiple study areas using bounding boxes (Ocampo, Tigaon, Goa)."""
    
    if os.path.exists(MULTIPLE_NETWORK_FILE) and not force_reload:
        print(f"[DataLoader] Loading cached combined network from {MULTIPLE_NETWORK_FILE}")
        G = ox.load_graphml(MULTIPLE_NETWORK_FILE)
        print(f"[DataLoader] Loaded: {len(G.nodes)} nodes, {len(G.edges)} edges")
        return G

    print("\n[DataLoader] Downloading combined network for: Ocampo, Tigaon, Goa")
    print("[DataLoader] Using bounding boxes (may take 5-10 minutes, 3 municipalities)...")

    graphs = []
    for area_name, bbox in MULTIPLE_STUDY_AREAS:
        print(f"\n[DataLoader] Downloading: {area_name}...")
        print(f"[DataLoader] Bounding box: N={bbox[0]}, S={bbox[1]}, E={bbox[2]}, W={bbox[3]}")
        try:
            # bbox format: (north, south, east, west) - pass as single tuple
            G = ox.graph_from_bbox(
                bbox,
                network_type="drive",
                simplify=True,
                retain_all=False
            )
            print(f"[DataLoader] ✓ {area_name}: {len(G.nodes)} nodes, {len(G.edges)} edges")
            graphs.append((area_name, G))
        except Exception as e:
            print(f"[DataLoader] ✗ Failed to download {area_name}: {str(e)}")
            continue

    if not graphs:
        raise Exception("Failed to download any networks. Check bounding box coordinates.")

    # Merge all graphs
    print("\n[DataLoader] Merging networks...")
    G_merged = nx.MultiDiGraph()
    
    for idx, (area_name, G) in enumerate(graphs):
        G_merged = nx.compose(G_merged, G)
        print(f"[DataLoader] After merging {area_name}: {len(G_merged.nodes)} nodes, {len(G_merged.edges)} edges")

    # Assign speeds to all edges
    print("[DataLoader] Assigning speeds to all edges...")
    for u, v, k, data in G_merged.edges(data=True, keys=True):
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

    os.makedirs(os.path.dirname(MULTIPLE_NETWORK_FILE), exist_ok=True)
    ox.save_graphml(G_merged, MULTIPLE_NETWORK_FILE)
    print(f"\n[DataLoader] Saved merged network to {MULTIPLE_NETWORK_FILE}")
    print(f"[DataLoader] Final: {len(G_merged.nodes)} nodes, {len(G_merged.edges)} edges")

    # Check geometry coverage
    has_geom = sum(1 for _, _, d in G_merged.edges(data=True) if 'geometry' in d)
    total = G_merged.number_of_edges()
    print(f"[DataLoader] Geometry coverage: {has_geom}/{total} edges ({round(has_geom/total*100)}%)")

    return G_merged


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
