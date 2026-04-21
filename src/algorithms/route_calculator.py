import heapq
import math
import osmnx as ox
import networkx as nx
from src.algorithms.lane_splitting import calculate_motorcycle_travel_time, is_lane_splitting_feasible


def haversine_heuristic(G, node, goal):
    node_data = G.nodes[node]
    goal_data = G.nodes[goal]

    lat1, lon1 = math.radians(node_data["y"]), math.radians(node_data["x"])
    lat2, lon2 = math.radians(goal_data["y"]), math.radians(goal_data["x"])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance_m = 6371000 * c

    return distance_m / 25.0


def get_edge_weight(G, u, v, traffic_speeds=None):
    edges = G.get_edge_data(u, v)
    if not edges:
        return float('inf'), False

    best_time = float('inf')
    best_ls = False

    for key, edge_data in edges.items():
        traffic_speed = None
        if traffic_speeds:
            edge_key = f"{u}_{v}_{key}"
            traffic_speed = traffic_speeds.get(edge_key, None)

        travel_time, ls_used = calculate_motorcycle_travel_time(edge_data, traffic_speed)

        if travel_time < best_time:
            best_time = travel_time
            best_ls = ls_used

    return best_time, best_ls


def astar_motorcycle(G, origin, destination, traffic_speeds=None):
    open_set = [(0, 0, origin, [origin], 0)]
    visited = {}

    while open_set:
        f, g, current, path, ls_count = heapq.heappop(open_set)

        if current in visited and visited[current] <= g:
            continue
        visited[current] = g

        if current == destination:
            total_distance = _path_distance(G, path)
            return {
                "path": path,
                "total_time_sec": g,
                "total_distance_m": total_distance,
                "lane_split_segments": ls_count,
                "total_segments": len(path) - 1,
                "algorithm": "A*"
            }

        for neighbor in G.successors(current):
            travel_time, ls_used = get_edge_weight(G, current, neighbor, traffic_speeds)

            if travel_time == float('inf'):
                continue

            new_g = g + travel_time
            new_ls = ls_count + (1 if ls_used else 0)
            h = haversine_heuristic(G, neighbor, destination)
            new_f = new_g + h

            if neighbor not in visited or visited.get(neighbor, float('inf')) > new_g:
                heapq.heappush(open_set, (new_f, new_g, neighbor, path + [neighbor], new_ls))

    raise nx.NetworkXNoPath(f"No path found from {origin} to {destination}")


def dijkstra_motorcycle(G, origin, destination, traffic_speeds=None):
    open_set = [(0, origin, [origin], 0)]
    visited = {}

    while open_set:
        g, current, path, ls_count = heapq.heappop(open_set)

        if current in visited:
            continue
        visited[current] = g

        if current == destination:
            total_distance = _path_distance(G, path)
            return {
                "path": path,
                "total_time_sec": g,
                "total_distance_m": total_distance,
                "lane_split_segments": ls_count,
                "total_segments": len(path) - 1,
                "algorithm": "Dijkstra"
            }

        for neighbor in G.successors(current):
            if neighbor in visited:
                continue

            travel_time, ls_used = get_edge_weight(G, current, neighbor, traffic_speeds)
            if travel_time == float('inf'):
                continue

            new_g = g + travel_time
            new_ls = ls_count + (1 if ls_used else 0)
            heapq.heappush(open_set, (new_g, neighbor, path + [neighbor], new_ls))

    raise nx.NetworkXNoPath(f"No path found from {origin} to {destination}")


def _path_distance(G, path):
    total = 0.0
    for i in range(len(path) - 1):
        edges = G.get_edge_data(path[i], path[i+1])
        if edges:
            lengths = [d.get("length", 0) for d in edges.values()]
            total += min(lengths)
    return total


def path_to_coordinates(G, path):
    """
    Convert path nodes to lat/lon coordinates using actual road geometry.
    Uses edge geometry (Shapely LineString) when available.
    Falls back to straight node-to-node lines when geometry is missing.
    """
    coords = []

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edges = G.get_edge_data(u, v)
        if not edges:
            continue

        edge_data = list(edges.values())[0]

        if 'geometry' in edge_data:
            geom_coords = list(edge_data['geometry'].coords)

            u_data = G.nodes[u]
            first_pt = geom_coords[0]
            last_pt = geom_coords[-1]

            dist_first_to_u = abs(first_pt[0] - u_data['x']) + abs(first_pt[1] - u_data['y'])
            dist_last_to_u = abs(last_pt[0] - u_data['x']) + abs(last_pt[1] - u_data['y'])

            if dist_last_to_u < dist_first_to_u:
                geom_coords = geom_coords[::-1]

            for lon, lat in geom_coords[:-1]:
                coords.append([lat, lon])
        else:
            u_data = G.nodes[u]
            coords.append([u_data['y'], u_data['x']])

    last = G.nodes[path[-1]]
    coords.append([last['y'], last['x']])

    return coords


def get_lane_split_segments(G, path, traffic_speeds=None):
    """
    Returns segments where lane-splitting is feasible,
    using actual road geometry for accurate highlighting.
    """
    segments = []

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edges = G.get_edge_data(u, v)
        if not edges:
            continue

        for key, edge_data in edges.items():
            traffic_speed = None
            if traffic_speeds:
                edge_key = f"{u}_{v}_{key}"
                traffic_speed = traffic_speeds.get(edge_key)

            feasible, _ = is_lane_splitting_feasible(edge_data, traffic_speed)
            if feasible:
                if 'geometry' in edge_data:
                    geom_coords = list(edge_data['geometry'].coords)
                    u_data = G.nodes[u]
                    first_pt = geom_coords[0]
                    last_pt = geom_coords[-1]
                    dist_first = abs(first_pt[0] - u_data['x']) + abs(first_pt[1] - u_data['y'])
                    dist_last = abs(last_pt[0] - u_data['x']) + abs(last_pt[1] - u_data['y'])
                    if dist_last < dist_first:
                        geom_coords = geom_coords[::-1]
                    points = [[lat, lon] for lon, lat in geom_coords]
                    segments.append({
                        "from": points[0],
                        "to": points[-1],
                        "points": points
                    })
                else:
                    u_data = G.nodes[u]
                    v_data = G.nodes[v]
                    segments.append({
                        "from": [u_data["y"], u_data["x"]],
                        "to": [v_data["y"], v_data["x"]],
                        "points": None
                    })
            break

    return segments