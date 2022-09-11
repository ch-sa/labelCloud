import json
from pathlib import Path
from typing import Dict


def read_label_definition(label_definition_path: Path) -> Dict[str, int]:
    with open(label_definition_path, "r") as f:
        label_definition: Dict[str, int] = json.loads(f.read())
        assert len(label_definition) > 0
    return label_definition
