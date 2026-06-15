from dataclasses import fields

from netbox_vsphere_sync.domain.model.vsphere import (
    Cluster,
    Datastore,
    HostSystem,
    Interface,
    IpAddress,
    PortGroup,
    Site,
    Vlan,
)

DomainEntity = Site | Cluster | HostSystem | Interface | IpAddress | Vlan | Datastore | PortGroup

IGNORED_FIELDS: set[str] = {"custom_fields", "mor", "ip_addresses", "hardware"}


class DiffResult:
    def __init__(self) -> None:
        self.to_create: list[DomainEntity] = []
        self.to_update: list[tuple[DomainEntity, DomainEntity]] = []
        self.to_skip: list[tuple[DomainEntity, str]] = []
        self.to_prune: list[tuple[str, str, str]] = []

    @property
    def has_changes(self) -> bool:
        return bool(self.to_create or self.to_update or self.to_prune)


class DiffEngine:
    def compute(
        self,
        vsphere_entities: list[DomainEntity],
        netbox_entities: list[DomainEntity],
    ) -> DiffResult:
        result = DiffResult()
        nb_by_key = self._index_by_key(netbox_entities)

        for vs_entity in vsphere_entities:
            key = self.natural_key(vs_entity)
            nb_entity = nb_by_key.pop(key, None)
            if nb_entity is None:
                result.to_create.append(vs_entity)
            else:
                changes = self.compute_changes(vs_entity, nb_entity)
                if changes:
                    result.to_update.append((nb_entity, vs_entity))
                else:
                    result.to_skip.append((vs_entity, "No changes"))

        for nb_key, nb_entity in nb_by_key.items():
            result.to_prune.append((self.entity_type(nb_entity), nb_key, "offline"))

        return result

    def natural_key(self, entity: DomainEntity) -> str:
        match entity:
            case Site():
                return f"site:{entity.name}"
            case Cluster():
                return f"cluster:{entity.site}:{entity.name}"
            case HostSystem():
                return f"device:{entity.site}:{entity.name}"
            case Interface():
                return f"interface:{entity.device}:{entity.name}"
            case IpAddress():
                return f"ip:{entity.address}:{entity.device}:{entity.interface}"
            case Vlan():
                return f"vlan:{entity.site}:{entity.vid}"
            case Datastore():
                return f"inventory:{entity.device}:{entity.name}:{entity.role}"
            case PortGroup():
                return f"portgroup:{entity.name}"
        return ""

    def compute_changes(self, vs: DomainEntity, nb: DomainEntity) -> dict[str, object]:
        changes: dict[str, object] = {}
        for f in fields(vs):
            if f.name in IGNORED_FIELDS:
                continue
            vs_val = getattr(vs, f.name)
            nb_val = getattr(nb, f.name)
            if vs_val != nb_val:
                changes[f.name] = vs_val
        return changes

    def entity_type(self, entity: DomainEntity) -> str:
        return type(entity).__name__.lower()

    def _index_by_key(self, entities: list[DomainEntity]) -> dict[str, DomainEntity]:
        return {self.natural_key(e): e for e in entities}
