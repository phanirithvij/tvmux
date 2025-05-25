"""Proxy list field that serializes to URL paths."""
from typing import TypeVar, Generic, List, Any
from pydantic import Field
from pydantic_core import core_schema

T = TypeVar('T')


class ProxyList(list, Generic[T]):
    """A list that serializes to URL paths."""

    def __init__(self, path: str, items: List[T] = None):
        super().__init__(items or [])
        self.path = path


def proxy_list(path: str) -> Any:
    """Create a field that serializes as a list of paths."""

    def serializer(value: ProxyList[T]) -> List[str]:
        """Serialize to list of path strings."""
        return [f"./{value.path}/{i}" for i in range(len(value))]

    def validator(value: Any) -> ProxyList[T]:
        """Validate/construct ProxyList."""
        if isinstance(value, ProxyList):
            return value
        if isinstance(value, list):
            return ProxyList(path, value)
        raise ValueError(f"Expected list or ProxyList, got {type(value)}")

    return Field(
        default_factory=lambda: ProxyList(path),
        json_schema_extra={"format": "uri-reference"},
        serializer=serializer,
        validator=validator
    )
