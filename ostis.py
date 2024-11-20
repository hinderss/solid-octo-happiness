from networkx import MultiDiGraph
from itertools import pairwise
from slugify import slugify

import sc_client.client as client
from sc_client.models import (
    ScAddr,
    ScEventParams,
    ScConstruction,
    ScIdtfResolveParams,
    ScLinkContent,
    ScLinkContentType,
    ScTemplate,
)
from sc_client.constants import sc_types
from dataclasses import dataclass
from typing import Optional, List, Tuple

from responce import get_coordinates, get_address_by_coordinates, generate_route


@dataclass
class Street:
    name: Optional[str]
    length: str
    maxspeed: str
    coords: Optional[List[Tuple[float, float]]]
    estimated_time: str


def get_streets(route: list, g: MultiDiGraph = None, start_coords: tuple = None, end_coords: tuple = None):
    streets = []
    total_distance = 0
    total_duration = 0

    for u, v in zip(route[:-1], route[1:]):
        edge_data = g.get_edge_data(u, v)[0]
        length = int(edge_data.get("length", 0))
        maxspeed = edge_data.get("maxspeed")
        maxspeed = int(maxspeed) if maxspeed else 60
        estimated_time = length / (maxspeed * 1000 / 3600)

        street = Street(
            name=str(edge_data.get("name")),
            length=str(length),
            maxspeed=str(maxspeed),
            coords=get_coordinates(u, v, g) if g else None,
            estimated_time=str(estimated_time),
        )
        streets.append(street)

    return streets


def distinct(iterable):
    seen = set()
    result = []
    for x in iterable:
        item = x[0] if isinstance(x, list) and x else x
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def create_node(name: str, node_type=sc_types.NODE_CONST):
    return client.resolve_keynodes(ScIdtfResolveParams(idtf=name, type=node_type))[0]


if __name__ == "__main__":
    start_point = (53.911613, 27.595701)  # БГУИР корпус 5
    end_point = (53.890696, 27.551166)  # ВОКЗАЛ

    start = str(get_address_by_coordinates(start_point[0], start_point[1]))
    end = str(get_address_by_coordinates(end_point[0], end_point[1]))

    client.connect("ws://localhost:8090/ws_json")

    R, G = generate_route(start_point, end_point)

    streets = get_streets(R, G, start_point, end_point)
    street_names = [street.name for street in streets]
    lengths = {}
    for street in streets:
        if street.name not in lengths:
            lengths[street.name] = 0
        lengths[street.name] += int(street.length)
    street_names = distinct(street_names)

    template = ScTemplate()
    nodes = []

    for street1, street2 in list(pairwise(street_names)):

        node1 = create_node(slugify(street1))
        if not nodes:
            nodes.append(node1)
        node2 = create_node(slugify(street2))
        nodes.append(node2)
        template.triple(
            node1,
            sc_types.EDGE_D_COMMON_VAR,
            node2,
        )
    for name, node in zip(street_names, nodes):
        template.triple(
            create_node(slugify(f"length_{str(lengths[name])}")),
            sc_types.EDGE_D_COMMON_VAR,
            node,
        )
    template.triple(
        create_node(slugify(start)),
        sc_types.EDGE_D_COMMON_VAR,
        nodes[0],
    )
    template.triple(
        nodes[-1],
        sc_types.EDGE_D_COMMON_VAR,
        create_node(slugify(end)),
    )

    client.template_generate(template)