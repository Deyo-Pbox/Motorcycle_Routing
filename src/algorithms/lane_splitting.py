from config import (
    MIN_LANE_WIDTH,
    MIN_LANE_COUNT,
    ROAD_SPEEDS,
    LANE_SPLIT_SPEED_MULTIPLIER
)


def get_lane_count(edge_data):
    lanes = edge_data.get("lanes", None)
    if lanes is None:
        return 1
    try:
        if isinstance(lanes, list):
            return int(lanes[0])
        return int(lanes)
    except (ValueError, TypeError):
        return 1


def get_lane_width(edge_data):
    width = edge_data.get("width", None)
    if width is not None:
        try:
            if isinstance(width, list):
                width = width[0]
            return float(str(width).replace("m", "").strip())
        except (ValueError, TypeError):
            pass

    highway = edge_data.get("highway", "residential")
    if isinstance(highway, list):
        highway = highway[0]

    lane_count = get_lane_count(edge_data)

    width_per_lane = {
        "motorway":      3.75,
        "trunk":         3.65,
        "primary":       3.5,
        "secondary":     3.3,
        "tertiary":      3.0,
        "unclassified":  2.8,
        "residential":   2.5,
        "living_street": 2.5,
        "service":       2.5,
        "default":       3.0,
    }

    per_lane = width_per_lane.get(highway, width_per_lane["default"])
    return per_lane * max(lane_count, 1)


def get_road_speed(edge_data):
    maxspeed = edge_data.get("maxspeed", None)
    if maxspeed is not None:
        try:
            if isinstance(maxspeed, list):
                maxspeed = maxspeed[0]
            speed_str = str(maxspeed).lower().replace("mph", "").replace("kph", "").strip()
            speed = float(speed_str)
            if "mph" in str(maxspeed).lower():
                speed *= 1.60934
            return speed
        except (ValueError, TypeError):
            pass

    highway = edge_data.get("highway", "residential")
    if isinstance(highway, list):
        highway = highway[0]

    return ROAD_SPEEDS.get(highway, ROAD_SPEEDS["default"])


def is_lane_splitting_feasible(edge_data, traffic_speed=None):
    """
    Lane-splitting is feasible purely based on road geometry.
    If the road has enough lanes and width, go for it.
    """
    lanes = get_lane_count(edge_data)
    lane_width = get_lane_width(edge_data)
    road_speed = get_road_speed(edge_data)
    current_speed = traffic_speed if traffic_speed is not None else road_speed

    check_lanes = lanes >= MIN_LANE_COUNT
    check_width = lane_width >= MIN_LANE_WIDTH

    feasible = check_lanes and check_width

    details = {
        "lanes": lanes,
        "lane_width": round(lane_width, 2),
        "road_speed_limit": road_speed,
        "current_traffic_speed": current_speed,
        "checks": {
            "lanes_ok": check_lanes,
            "width_ok": check_width,
        },
        "feasible": feasible
    }

    return feasible, details


def calculate_motorcycle_travel_time(edge_data, traffic_speed=None):
    length = edge_data.get("length", 0)
    if length <= 0:
        return 0.0, False

    road_speed = get_road_speed(edge_data)
    current_speed = traffic_speed if traffic_speed is not None else road_speed

    if current_speed <= 0:
        current_speed = ROAD_SPEEDS["default"]

    feasible, _ = is_lane_splitting_feasible(edge_data, traffic_speed)

    if feasible:
        effective_speed = current_speed * LANE_SPLIT_SPEED_MULTIPLIER
        effective_speed = min(effective_speed, road_speed)
    else:
        effective_speed = current_speed

    effective_speed = max(effective_speed, 5)

    travel_time = (length / 1000) / effective_speed * 3600

    return travel_time, feasible