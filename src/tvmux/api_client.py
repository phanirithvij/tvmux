"""Simple API client function for tvmux server."""
import logging
from typing import Optional, Type, TypeVar, Union
from urllib.parse import urljoin

import requests
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class APIError(Exception):
    """API request failed."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


def api_call(base_url: str, method: str, path: str,
             data: Optional[BaseModel] = None,
             response_model: Optional[Type[T]] = None) -> Union[T, dict]:
    """Make an API call with Pydantic support.

    Args:
        base_url: Server base URL
        method: HTTP method
        path: API endpoint path
        data: Request body as Pydantic model
        response_model: Expected response model class

    Returns:
        Instance of response_model or dict

    Raises:
        APIError: If the request fails
    """
    # Build URL
    if not path.startswith('/'):
        path = '/' + path
    url = urljoin(base_url.rstrip('/') + '/', path.lstrip('/'))

    # Prepare request
    kwargs = {}
    if data:
        kwargs['json'] = data.model_dump()

    logger.debug(f"{method} {url}")

    try:
        # Use requests session for redirect handling
        session = requests.Session()
        session.max_redirects = 10

        response = session.request(method, url, **kwargs)

        # Handle errors
        if response.status_code >= 400:
            detail = "Unknown error"
            try:
                error_data = response.json()
                detail = error_data.get('detail', response.text)
            except:
                detail = response.text or f"HTTP {response.status_code}"

            raise APIError(response.status_code, detail)

        # Parse response
        if not response.content:
            return {}

        if response_model:
            return response_model.model_validate_json(response.content)
        else:
            return response.json()

    except requests.RequestException as e:
        logger.exception(f"Request to {url} failed: {e}")
        raise APIError(0, str(e))
