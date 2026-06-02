import logging
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from pymongo.errors import CollectionInvalid, OperationFailure

logger = logging.getLogger(__name__)

CACHE_COLL = "cache"
CACHE_DB = "meta_db"
CACHE_SETTINGS = "settings"
CACHE_SETTINGS_KEY = "cache"
"""
Sample cache_settings collection entry:
meta_db.cache_settings.insertOne({"type": "cache", "enabled": true, "cache_expiry": 600})
meta_db.cache_settings.find(): { "_id" : ObjectId("5cd5388b9fddfbe6e968f11b"), "type": "cache", "enabled" : false, "cache_expiry" : 600 }
"""
DEFAULT_CACHE_EXPIRY = 3600


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Cache:
    def __init__(
        self,
        client: Any,
        cache_expiry: int = DEFAULT_CACHE_EXPIRY,
        cache_db: str = CACHE_DB,
        cache_col: str = CACHE_COLL,
    ) -> None:
        self._client = client
        self._cachedb = client[cache_db]
        self._cachecol: Any = None
        try:
            if cache_col not in self._cachedb.list_collection_names():
                self._cachedb.create_collection(cache_col).create_index(
                    "date", expireAfterSeconds=cache_expiry
                )
        except CollectionInvalid as op:
            logging.debug("Cache collection was created concurrently: %s", op)
        except OperationFailure as op:
            logging.debug(
                "This is fine if you are not admin. The collection should already be created for you: %s",
                op,
            )

        self._cachecol = self._cachedb[cache_col]

    def _get_cache_settings(self) -> dict[str, Any] | None:
        try:
            return cast(
                dict[str, Any] | None,
                self._cachedb[CACHE_SETTINGS].find_one({"type": CACHE_SETTINGS_KEY}),
            )
        except OperationFailure as op:
            logging.debug(
                "Cannot access %s in db: %s. Error: %s" % (CACHE_SETTINGS, CACHE_DB, op)
            )
        return None

    def set_caching_state(self, enabled: bool) -> None:
        """
        Used to enable or disable the caching globally
        :return:
        """
        if not isinstance(enabled, bool):
            logging.error("Enabled should be a boolean type.")
            return

        if CACHE_SETTINGS not in self._cachedb.list_collection_names():
            logging.info("Creating %s collection for cache settings" % CACHE_SETTINGS)
            self._cachedb[CACHE_SETTINGS].insert_one(
                {
                    "type": CACHE_SETTINGS_KEY,
                    "enabled": enabled,
                    "cache_expiry": DEFAULT_CACHE_EXPIRY,
                }
            )
        else:
            self._cachedb[CACHE_SETTINGS].update_one(
                {"type": CACHE_SETTINGS_KEY}, {"$set": {"enabled": enabled}}
            )
            logging.info("Caching set to: %s" % enabled)

    def _is_not_expired(
        self, cached_data: dict[str, Any], newer_than_secs: int | None
    ) -> bool:
        # Use the expiry period in the settings (or the default) if not overriden by the function argument.
        if newer_than_secs:
            expiry_period = newer_than_secs
        else:
            cache_settings = self._get_cache_settings()
            expiry_period = (
                cache_settings["cache_expiry"]
                if cache_settings
                else DEFAULT_CACHE_EXPIRY
            )

        return cast(
            bool, _utcnow() < cached_data["date"] + timedelta(seconds=expiry_period)
        )

    def get(self, key: str, newer_than_secs: int | None = None) -> Any:
        """

        :param key: Key for the dataset. eg. list_libraries.
        :param newer_than_secs: None to indicate use cache if available. Used to indicate what level of staleness
        in seconds is tolerable.
        :return: None unless if there is non stale data present in the cache.
        """
        try:
            if self._cachecol is None:
                # Collection not created or no permissions to read from it.
                return None
            cached_data = self._cachecol.find_one({"type": key})
            # Check that there is data in cache and it's not stale.
            if cached_data and self._is_not_expired(cached_data, newer_than_secs):
                return cached_data["data"]
        except OperationFailure as op:
            # Fallback to uncached version without spamming.
            logging.debug(
                "Could not read from cache due to: %s. Ask your admin to give read permissions on %s:%s",
                op,
                CACHE_DB,
                CACHE_COLL,
            )

        return None

    def set(self, key: str, data: Any) -> None:
        try:
            self._cachecol.update_one(
                {"type": key},
                {"$set": {"type": key, "date": _utcnow(), "data": data}},
                upsert=True,
            )
        except OperationFailure as op:
            logging.debug(
                "This operation is to be run with admin permissions. Should be fine: %s",
                op,
            )

    def append(self, key: str, append_data: Any) -> None:
        try:
            self._cachecol.update_one(
                {"type": key},
                {
                    # Add to set will not add the same library again to the list unlike set.
                    "$addToSet": {"data": append_data},
                    "$setOnInsert": {"type": key, "date": _utcnow()},
                },
                upsert=True,
            )
        except OperationFailure as op:
            logging.debug("Admin is required to append to the cache: %s", op)

    def delete_item_from_key(self, key: str, item: Any) -> None:
        try:
            self._cachecol.update_one({"type": key}, {"$pull": {"data": item}})
        except OperationFailure as op:
            logging.debug("Admin is required to remove from cache: %s", op)

    def update_item_for_key(self, key: str, old: Any, new: Any) -> None:
        # This op is not atomic, but given the rarity of renaming a lib, it should not cause issues.
        self.delete_item_from_key(key, old)
        self.append(key, new)

    def is_caching_enabled(self, cache_enabled_in_env: bool) -> bool:
        cache_settings = self._get_cache_settings()
        # Caching is enabled unless explicitly disabled. Can be disabled either by an env variable or config in mongo.
        if cache_settings and not cache_settings["enabled"]:
            return False
        # Disabling from Mongo Setting take precedence over this env variable
        if not cache_enabled_in_env:
            return False
        return True
