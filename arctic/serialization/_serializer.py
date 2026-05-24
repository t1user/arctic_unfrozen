from typing import Any


class Serializer(object):
    def serialize(self, data: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def deserialize(self, data: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def combine(self, a: Any, b: Any) -> Any:
        raise NotImplementedError
