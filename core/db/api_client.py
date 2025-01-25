import httpx
import os
import asyncio
from typing import Optional, Dict, Any, Callable
from loguru import logger
from dotenv import load_dotenv
from functools import wraps
import time

load_dotenv()

default_value = {"code": 500, "msg": "Can not access Database...", "data": {}}


def retry_with_fallback(
    max_retries: int = 3,
    delay: float = 1.0,
    default_value: Any = default_value,
    try_fallback: bool = True,
):
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            self = args[0]
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except httpx.HTTPError as e:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                    elif try_fallback and self.fallback_url:
                        original_base_url = self.base_url
                        try:
                            self.base_url = self.fallback_url
                            logger.info(f"Trying fallback URL: {self.base_url}")
                            return await func(*args, **kwargs)
                        except httpx.HTTPError as fallback_e:
                            logger.error(f"Fallback URL request failed: {fallback_e}")
                            return default_value
                        finally:
                            self.base_url = original_base_url
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed, returning default value"
                        )
                        return default_value

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            self = args[0]
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except httpx.HTTPError as e:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                    elif try_fallback and self.fallback_url:
                        original_base_url = self.base_url
                        try:
                            self.base_url = self.fallback_url
                            logger.info(f"Trying fallback URL: {self.base_url}")
                            return func(*args, **kwargs)
                        except httpx.HTTPError as fallback_e:
                            logger.error(f"Fallback URL request failed: {fallback_e}")
                            return default_value
                        finally:
                            self.base_url = original_base_url
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed, returning default value"
                        )
                        return default_value

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


class APIClient:
    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
        fallback_url: Optional[str] = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.fallback_url = fallback_url

    @retry_with_fallback()
    async def request_async(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        return_data: bool = True,
    ) -> Dict:
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=data,
                    timeout=self.timeout,
                )

                response.raise_for_status()
                return response.json().get("data") if return_data else response.json()
        except httpx.HTTPError as e:
            logger.error(f"API request to {url} failed: {e}")
            raise

    @retry_with_fallback()
    def request_sync(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        return_data: bool = True,
    ) -> Dict:
        url = f"{self.base_url}{endpoint}"
        try:
            with httpx.Client() as client:
                response = client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=data,
                    timeout=self.timeout,
                )

            response.raise_for_status()
            return response.json().get("data") if return_data else response.json()
        except httpx.HTTPError as e:
            logger.error(f"API request to {url} failed: {e}")
            raise


game_api = APIClient(base_url=os.getenv("GAME_BACKEND_URL"))
agent_api = APIClient(base_url=os.getenv("AGENT_BACKEND_URL"))

if __name__ == "__main__":
    response = agent_api.request_sync(method="GET", endpoint="/production_path/432543")
    print(response)
