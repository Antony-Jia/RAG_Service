from __future__ import annotations

from kb_core.models import MetadataFilter


def match_metadata(metadata: dict, filter_obj: MetadataFilter | None) -> bool:
    if filter_obj is None or not filter_obj.equals:
        return True

    for key, expected in filter_obj.equals.items():
        if metadata.get(key) != expected:
            return False
    return True
