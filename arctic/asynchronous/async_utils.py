import time
import uuid

from collections.abc import Callable
from enum import Enum
from concurrent.futures import Future
from typing import Any

from arctic.exceptions import RequestDurationException


class AsyncRequestType(Enum):
    MODIFIER = 'modifier'
    ACCESSOR = 'accessor'


class AsyncRequest(object):
    def __init__(
        self,
        kind: AsyncRequestType,
        library: str,
        fun: Callable[..., Any],
        callback: Callable[..., Any] | None,
        *args: Any,
        **kwargs: Any
    ) -> None:
        self.id = uuid.uuid4()

        # Request library call spec
        self.fun = fun
        self.args = args
        self.kwargs = kwargs

        # Request meta
        self.kind = kind
        self.library = library
        self.symbol = kwargs.get('symbol')

        # Request's state
        self.future: Future[Any] | None = None
        self.callback = callback
        self.data = None
        self.exception = None
        self.is_running = False
        self.is_completed = False

        # Timekeeping
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.create_time = time.time()

        self.mongo_retry = bool(kwargs.get('mongo_retry'))

    @property
    def execution_duration(self) -> float:
        if None in (self.start_time, self.end_time):
            raise RequestDurationException("{} can't provide an execution_duration {}.".format(
                self, (self.start_time, self.end_time)))
        assert self.start_time is not None and self.end_time is not None
        return self.end_time - self.start_time

    @property
    def schedule_delay(self) -> float:
        if None in (self.start_time, self.create_time):
            raise RequestDurationException("{} can't provide a schedule_delay {}.".format(
                self, (self.start_time, self.create_time)))
        assert self.start_time is not None
        return self.start_time - self.create_time

    @property
    def total_time(self) -> float:
        if None in (self.end_time, self.create_time):
            raise RequestDurationException("{} can't provide a total_time {}.".format(
                self, (self.end_time, self.create_time)))
        assert self.end_time is not None
        return self.end_time - self.create_time

    def __str__(self) -> str:
        return "Request id:{} library:{}, symbol:{} fun:{}, kind:{}".format(
            self.id, self.library, self.symbol, getattr(self.fun, '__name__', None), self.kind)
