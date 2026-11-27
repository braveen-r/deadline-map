from pathlib import Path
from app.inventory.models import Inventory, load_inventory_from_text


def load_inventory_file(path: Path) -> Inventory:
    return load_inventory_from_text(path.read_text(encoding="utf-8"))


__all__ = ["Inventory", "load_inventory_from_text", "load_inventory_file"]
