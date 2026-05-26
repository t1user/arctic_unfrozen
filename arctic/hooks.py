from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from .auth import MongoCredentials

ResolveMongoHook: TypeAlias = Callable[[str], str]
LogExceptionHook: TypeAlias = Callable[..., None]
AuthHook: TypeAlias = Callable[[str, str, str | None], "MongoCredentials | None"]


_resolve_mongodb_hook: ResolveMongoHook = lambda env: env
_log_exception_hook: LogExceptionHook = lambda *args, **kwargs: None
_get_auth_hook: AuthHook = lambda host, app_name, database_name: None


def get_mongodb_uri(host: str) -> str:
    """
    Return the MongoDB URI for the passed in host-alias / environment.

    Allows an indirection point for mapping aliases to particular
    MongoDB instances.
    """
    return _resolve_mongodb_hook(host)


def register_resolve_mongodb_hook(hook: ResolveMongoHook) -> None:
    global _resolve_mongodb_hook
    _resolve_mongodb_hook = hook


def log_exception(fn_name: str, exception: BaseException, retry_count: int, **kwargs: Any) -> None:
    """
    External exception logging hook.
    """
    _log_exception_hook(fn_name, exception, retry_count, **kwargs)


def register_log_exception_hook(hook: LogExceptionHook) -> None:
    global _log_exception_hook
    _log_exception_hook = hook


def register_get_auth_hook(hook: AuthHook) -> None:
    global _get_auth_hook
    _get_auth_hook = hook
