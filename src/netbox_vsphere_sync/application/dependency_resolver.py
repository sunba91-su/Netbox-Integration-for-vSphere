DEPENDENCY_ORDER: list[str] = [
    "site",
    "cluster_type",
    "manufacturer",
    "device_role",
    "cluster",
    "device",
    "vlan",
    "interface",
    "ip_address",
    "inventory_item",
]


class DependencyResolver:
    def resolve(self, entity_types: set[str]) -> list[str]:
        ordered = [t for t in DEPENDENCY_ORDER if t in entity_types]
        return ordered

    def dependencies_for(self, entity_type: str) -> list[str]:
        if entity_type not in DEPENDENCY_ORDER:
            return []
        idx = DEPENDENCY_ORDER.index(entity_type)
        return DEPENDENCY_ORDER[:idx]

    def sort(self, entities: list[tuple[str, str]]) -> list[tuple[str, str]]:
        seen: set[str] = set()
        result: list[tuple[str, str]] = []

        for entity_type, _ in entities:
            seen.add(entity_type)

        for entity_type in DEPENDENCY_ORDER:
            if entity_type in seen:
                for item in entities:
                    if item[0] == entity_type:
                        result.append(item)

        for item in entities:
            if item not in result:
                result.append(item)

        return result
