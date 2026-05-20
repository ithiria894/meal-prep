"""BFS unit conversion graph.

Based on Tandoor's unit_conversion_helper.py pattern.
Finds conversion paths between units using breadth-first search.
"""

import json
import logging
from collections import defaultdict, deque
from pathlib import Path

log = logging.getLogger(__name__)

UNITS_FILE = Path(__file__).parent.parent.parent / "data" / "units.json"

ConversionGraph = dict[str, list[tuple[str, float]]]


def load_conversion_graph() -> ConversionGraph:
    graph: ConversionGraph = defaultdict(list)

    if UNITS_FILE.exists():
        data = json.loads(UNITS_FILE.read_text())
        for conv in data.get("conversions", []):
            from_unit = conv["from"]
            to_unit = conv["to"]
            factor = conv["factor"]
            graph[from_unit].append((to_unit, factor))
            graph[to_unit].append((from_unit, 1.0 / factor))
    else:
        _add_builtin_conversions(graph)

    return graph


def _add_builtin_conversions(graph: ConversionGraph) -> None:
    conversions = [
        ("g", "kg", 0.001),
        ("g", "oz", 0.035274),
        ("kg", "lb", 2.20462),
        ("ml", "l", 0.001),
        ("ml", "tsp", 0.202884),
        ("ml", "tbsp", 0.067628),
        ("ml", "cup", 0.004227),
        ("ml", "fl_oz", 0.033814),
        ("tsp", "tbsp", 1 / 3),
        ("tbsp", "cup", 1 / 16),
    ]
    for from_u, to_u, factor in conversions:
        graph[from_u].append((to_u, factor))
        graph[to_u].append((from_u, 1.0 / factor))


def convert(
    amount: float,
    from_unit: str,
    to_unit: str,
    graph: ConversionGraph | None = None,
) -> float | None:
    if from_unit == to_unit:
        return amount

    if graph is None:
        graph = load_conversion_graph()

    factor = _bfs_find_factor(graph, from_unit, to_unit)
    if factor is None:
        log.warning("No conversion path: %s → %s", from_unit, to_unit)
        return None

    return amount * factor


def _bfs_find_factor(graph: ConversionGraph, start: str, target: str) -> float | None:
    if start not in graph:
        return None

    visited = {start}
    queue: deque[tuple[str, float]] = deque([(start, 1.0)])

    while queue:
        current, cumulative_factor = queue.popleft()

        for neighbor, factor in graph.get(current, []):
            if neighbor == target:
                return cumulative_factor * factor

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, cumulative_factor * factor))

    return None
