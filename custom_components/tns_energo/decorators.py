"""TNS-Energo decorators."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
from random import randrange
from typing import TYPE_CHECKING
from typing import TypeVar, ParamSpec, Concatenate, Any

from aiotnse.exceptions import TNSEApiError, TNSEAuthError
from aiotnse.helpers import is_error_response
from async_timeout import timeout
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.json import json_dumps
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import API_TIMEOUT, API_MAX_TRIES, API_RETRY_DELAY

if TYPE_CHECKING:
    pass

_TNSECoordinatorT = TypeVar("_TNSECoordinatorT", bound="TNSECoordinator")
_R = TypeVar("_R")
_P = ParamSpec("_P")


def async_api_request_handler(
        method: Callable[Concatenate[_TNSECoordinatorT, _P], Awaitable[_R]]
) -> Callable[Concatenate[_TNSECoordinatorT, _P], Coroutine[Any, Any, _R]]:
    """Decorator to handle API errors."""

    @wraps(method)
    async def wrapper(
            self: _TNSECoordinatorT, *args: _P.args, **kwargs: _P.kwargs
    ) -> _R:
        """Wrap an API method."""
        try:
            tries = 0
            api_timeout = API_TIMEOUT
            api_retry_delay = API_RETRY_DELAY
            while True:
                tries += 1
                try:
                    async with timeout(api_timeout):
                        result = await method(self, *args, **kwargs)
                    if is_error_response(result):
                        self.logger.error(
                            "API error while execute function %s: %s",
                            method.__name__,
                            json_dumps(result),
                        )
                    else:
                        return result
                except asyncio.TimeoutError:
                    api_timeout = tries * API_TIMEOUT
                    self.logger.debug(
                        "Function %s: Timeout connecting to TNS-Energo", method.__name__
                    )

                if tries >= API_MAX_TRIES:
                    raise TNSEApiError(
                        f"API error while execute function {method.__name__}"
                    )

                self.logger.warning(
                    "Attempt %d/%d. Wait %d seconds and try again",
                    tries,
                    API_MAX_TRIES,
                    api_retry_delay,
                )
                await asyncio.sleep(api_retry_delay)
                api_retry_delay += API_RETRY_DELAY + randrange(API_RETRY_DELAY)

        except TNSEAuthError as exc:
            raise ConfigEntryAuthFailed("Auth error") from exc
        except TNSEApiError as exc:
            raise UpdateFailed(f"Invalid response from API: {exc}") from exc

    return wrapper
