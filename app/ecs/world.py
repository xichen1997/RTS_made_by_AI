"""Minimal entity-component storage used by the RTS simulation."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Generator, Iterable, Tuple, Type, TypeVar


ComponentType = TypeVar("ComponentType")


class World:
    """Stores entities and their components."""

    def __init__(self) -> None:
        self._next_entity_id: int = 1
        self._components: Dict[Type[object], Dict[int, object]] = defaultdict(dict)

    # ------------------------------------------------------------------
    # Entity management
    # ------------------------------------------------------------------
    def create_entity(self) -> int:
        entity_id = self._next_entity_id
        self._next_entity_id += 1
        return entity_id

    def remove_entity(self, entity_id: int) -> None:
        for component_map in self._components.values():
            component_map.pop(entity_id, None)

    # ------------------------------------------------------------------
    # Component management
    # ------------------------------------------------------------------
    def add_component(self, entity_id: int, component: object) -> object:
        self._components[type(component)][entity_id] = component
        return component

    def get_component(self, entity_id: int, component_type: Type[ComponentType]) -> ComponentType | None:
        return self._components.get(component_type, {}).get(entity_id)  # type: ignore[return-value]

    def get_components(self, *component_types: Type[object]) -> Generator[Tuple[int, Tuple[object, ...]], None, None]:
        if not component_types:
            return
        smallest_type = min(component_types, key=lambda c: len(self._components.get(c, {})))
        for entity_id in list(self._components.get(smallest_type, {}).keys()):
            results = []
            for component_type in component_types:
                component = self._components.get(component_type, {}).get(entity_id)
                if component is None:
                    break
                results.append(component)
            else:
                yield entity_id, tuple(results)

    def remove_component(self, entity_id: int, component_type: Type[object]) -> None:
        self._components.get(component_type, {}).pop(entity_id, None)

    def entities_with(self, *component_types: Type[object]) -> Iterable[int]:
        for entity_id, _ in self.get_components(*component_types):
            yield entity_id
