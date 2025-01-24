import httpx
import os
from typing import Optional, Dict
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class APIClient:
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout

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
