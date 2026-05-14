import time
import requests
from requests.exceptions import Timeout, RequestException
from django_redis import get_redis_connection


class BasalamAPIClient:

    BASE_URL = "https://openapi.basalam.com"
    MAX_RETRIES = 3
    TIMEOUT = 15

    RATE_LIMIT_KEY = "basalam:requests:per_minute"
    RATE_LIMIT_WINDOW = 60
    LOG_RATE_WARNING_THRESHOLD = 200

    def __init__(self, access_token: str):
        self.base_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    def _count_request(self) -> int:
        req = get_redis_connection("default")
        pipe = req.pipeline()
        pipe.incr(self.RATE_LIMIT_KEY)
        pipe.expire(self.RATE_LIMIT_KEY, self.RATE_LIMIT_WINDOW)
        current, _ = pipe.execute()

        return int(current)

    # -----------------------------
    # Internal request handler
    # -----------------------------
    def _request(self, method: str, url: str, **kwargs):
        headers = self.base_headers.copy()
        headers.update(kwargs.pop("headers", {}))

        for retry in range(self.MAX_RETRIES):
            try:
                current = self._count_request()

                if current >= self.LOG_RATE_WARNING_THRESHOLD:
                    print(
                        f"[Basalam RateLimit] {current} req / {self.RATE_LIMIT_WINDOW}s"
                    )

                return requests.request(
                    method,
                    self.BASE_URL + url,
                    headers=headers,
                    timeout=self.TIMEOUT,
                    **kwargs
                )

            except Timeout:
                time.sleep(2 ** retry)

            except RequestException:
                if retry == self.MAX_RETRIES - 1:
                    raise

    # -----------------------------
    # Public methods
    # -----------------------------
    def get(self, url: str, params=None):
        return self._request(
            "GET",
            url,
            params=params
        )

    def post(self, url: str, *, json=None, files=None, data=None):
        headers = {}
        if json is not None:
            headers["Content-Type"] = "application/json"

        return self._request(
            "POST",
            url,
            json=json,
            files=files,
            data=data,
            headers=headers
        )
