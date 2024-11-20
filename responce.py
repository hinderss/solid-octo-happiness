import argparse

import osmnx as ox
import networkx as nx
import json
from geopy.geocoders import Nominatim
from matplotlib import pyplot as plt

from networkx import MultiDiGraph


def get_address_by_coordinates(latitude, longitude):
    geolocator = Nominatim(user_agent="osm")
    location = geolocator.reverse((latitude, longitude), language='en')
    return location.address if location else None


def get_coordinates(node1, node2, g):
    coord1 = {'lat': g.nodes[node1]['y'], 'lng': g.nodes[node1]['x']}
    coord2 = {'lat': g.nodes[node2]['y'], 'lng': g.nodes[node2]['x']}
    return [coord1, coord2]


def generate_route(start, end, dist=5000) -> (MultiDiGraph, list):
    graph = ox.graph_from_point(start, dist=dist, network_type="drive")

    start_node = ox.distance.nearest_nodes(graph, start[1], start[0])
    end_node = ox.distance.nearest_nodes(graph, end[1], end[0])

    route = nx.shortest_path(graph, start_node, end_node, weight="length")

    return route, graph


def generate_route_data(route: list, g: MultiDiGraph = None, start_coords: tuple = None, end_coords: tuple = None, ):
    streets = []
    total_distance = 0
    total_duration = 0

    for u, v in zip(route[:-1], route[1:]):
        edge_data = g.get_edge_data(u, v)[0]
        length = int(edge_data.get("length", 0))
        maxspeed = edge_data.get("maxspeed")
        maxspeed = int(maxspeed) if maxspeed else 60
        estimated_time = length / (maxspeed * 1000 / 3600)

        street = {
            "name": edge_data.get("name"),
            "length": length,
            "maxspeed": maxspeed,
            "coords": get_coordinates(u, v, g) if g else None,
            "estimated_time": estimated_time,
        }
        streets.append(street)

        total_distance += length
        total_duration += estimated_time

    return route_dict(total_distance, total_duration, streets, start_coords, end_coords)


def route_dict(distance: int, duration: int, streets: list, start: tuple = None, end: tuple = None):
    return {
        "status": "success",
        "route": {
            "total_distance": distance,
            "total_duration": duration,
            "legs": [
                {
                    "start_point": {
                        "lat": start[0],
                        "lng": start[1],
                        "address": get_address_by_coordinates(start[0], start[1])
                    } if start else None,
                    "end_point": {
                        "lat": end[0],
                        "lng": end[1],
                        "address": get_address_by_coordinates(end[0], end[1])
                    } if end else None,
                    "streets": streets,
                }
            ]
        },
    }


def visualize(route: list, g: MultiDiGraph = None):
    ox.plot_graph_route(g, route, route_linewidth=3, node_size=0)

    pos = nx.spring_layout(g)
    for (u, v, data) in g.edges(data=True):
        label = f"{data['weight']}"
        nx.draw_networkx_edges(g, pos, edgelist=[(u, v)], alpha=0.5, arrowstyle='-|>')
        nx.draw_networkx_edge_labels(g, pos, edge_labels={(u, v): label})

    plt.title("MultiDiGraph Visualization")
    plt.show()


def main(start_point, end_point, visualize_route, save_to_file):
    R, G = generate_route(start_point, end_point)
    route_data = generate_route_data(R, G, start_point, end_point)

    print(json.dumps(route_data, indent=4, ensure_ascii=False))

    if save_to_file:
        with open("route_data.json", "w", encoding="utf-8") as f:
            json.dump(route_data, f, ensure_ascii=False, indent=4)
        print("Данные маршрута сохранены в файл 'route_data.json'.")

    if visualize_route:
        visualize(R, G)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Приложение для генерации маршрута между двумя точками.")

    parser.add_argument("--start", "-s", type=str, required=True, help="Координаты начальной точки в формате 'lat,lon'")
    parser.add_argument("--end", "-e", type=str, required=True, help="Координаты конечной точки в формате 'lat,lon'")

    parser.add_argument("--visualize", "-v", action="store_true", help="Визуализировать маршрут")

    parser.add_argument("--save", "-S", action="store_true", help="Сохранить данные маршрута в файл JSON")

    args = parser.parse_args()

    try:
        start_point = tuple(map(float, args.start.split(',')))
        end_point = tuple(map(float, args.end.split(',')))
    except ValueError:
        print("Ошибка: Убедитесь, что координаты указаны в формате 'lat,lon'")
        exit(1)

    main(start_point, end_point, visualize_route=args.visualize, save_to_file=args.save)
