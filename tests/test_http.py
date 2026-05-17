import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from rentals_assistant.http import create_client, fetch_with_delay, fetch_with_retry


class TestCreateClient:
    def test_returns_async_client(self):
        client = create_client()
        assert isinstance(client, httpx.AsyncClient)

    def test_default_user_agent_is_realistic_chrome(self):
        client = create_client()
        ua = client.headers.get("User-Agent")
        assert "Mozilla/5.0" in ua
        assert "Chrome" in ua

    def test_custom_headers_override_user_agent(self):
        client = create_client(headers={"User-Agent": "custom/1.0"})
        assert client.headers["User-Agent"] == "custom/1.0"

    def test_custom_headers_merge_with_defaults(self):
        client = create_client(headers={"Accept": "text/html"})
        assert client.headers["Accept"] == "text/html"
        assert "Chrome" in client.headers["User-Agent"]

    def test_stores_retry_config(self):
        client = create_client(max_retries=5, backoff_base=2.0)
        assert client._max_retries == 5
        assert client._backoff_base == 2.0

    def test_default_retry_config(self):
        client = create_client()
        assert client._max_retries == 3
        assert client._backoff_base == 1.0

    def test_default_timeout(self):
        client = create_client()
        assert client.timeout.read == 30.0

    def test_custom_timeout(self):
        client = create_client(timeout=60.0)
        assert client.timeout.read == 60.0


class TestFetchWithRetry:
    async def test_success_on_first_attempt(self):
        client = MagicMock()
        client._max_retries = 3
        client._backoff_base = 1.0
        mock_response = MagicMock()
        mock_response.status_code = 200
        client.request = AsyncMock(return_value=mock_response)

        response = await fetch_with_retry(client, "GET", "http://example.com")
        assert response.status_code == 200
        client.request.assert_awaited_once_with("GET", "http://example.com")

    async def test_retry_then_success(self):
        client = MagicMock()
        client._max_retries = 3
        client._backoff_base = 1.0
        responses = [
            MagicMock(status_code=503),
            MagicMock(status_code=200),
        ]
        client.request = AsyncMock(side_effect=responses)

        with patch("rentals_assistant.http.asyncio.sleep"):
            response = await fetch_with_retry(client, "GET", "http://example.com")

        assert response.status_code == 200
        assert client.request.await_count == 2

    async def test_retry_exhausted_raises(self):
        client = MagicMock()
        client._max_retries = 2
        client._backoff_base = 1.0
        client.request = AsyncMock(return_value=MagicMock(status_code=503))

        with patch("rentals_assistant.http.asyncio.sleep"), pytest.raises(httpx.HTTPStatusError):
            await fetch_with_retry(client, "GET", "http://example.com")

        assert client.request.await_count == 3  # initial + 2 retries

    async def test_403_no_retry(self, caplog):
        client = MagicMock()
        client._max_retries = 3
        client._backoff_base = 1.0
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=MagicMock(), response=mock_response
        )
        client.request = AsyncMock(return_value=mock_response)

        with caplog.at_level(logging.WARNING), pytest.raises(httpx.HTTPStatusError):
            await fetch_with_retry(client, "GET", "http://example.com")

        assert client.request.await_count == 1
        assert "403" in caplog.text
        assert "not retrying" in caplog.text.lower()

    async def test_404_no_retry(self, caplog):
        client = MagicMock()
        client._max_retries = 3
        client._backoff_base = 1.0
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=mock_response
        )
        client.request = AsyncMock(return_value=mock_response)

        with caplog.at_level(logging.WARNING), pytest.raises(httpx.HTTPStatusError):
            await fetch_with_retry(client, "GET", "http://example.com")

        assert client.request.await_count == 1
        assert "404" in caplog.text
        assert "not retrying" in caplog.text.lower()

    async def test_connect_timeout_retry_then_success(self):
        client = MagicMock()
        client._max_retries = 3
        client._backoff_base = 1.0
        client.request = AsyncMock(
            side_effect=[
                httpx.ConnectTimeout("timeout"),
                MagicMock(status_code=200),
            ]
        )

        with patch("rentals_assistant.http.asyncio.sleep"):
            response = await fetch_with_retry(client, "GET", "http://example.com")

        assert response.status_code == 200
        assert client.request.await_count == 2

    async def test_read_timeout_retry_then_success(self):
        client = MagicMock()
        client._max_retries = 3
        client._backoff_base = 1.0
        client.request = AsyncMock(
            side_effect=[
                httpx.ReadTimeout("timeout"),
                MagicMock(status_code=200),
            ]
        )

        with patch("rentals_assistant.http.asyncio.sleep"):
            response = await fetch_with_retry(client, "GET", "http://example.com")

        assert response.status_code == 200
        assert client.request.await_count == 2

    async def test_connect_timeout_exhausted_raises(self):
        client = MagicMock()
        client._max_retries = 1
        client._backoff_base = 1.0
        client.request = AsyncMock(side_effect=httpx.ConnectTimeout("timeout"))

        with patch("rentals_assistant.http.asyncio.sleep"), pytest.raises(httpx.ConnectTimeout):
            await fetch_with_retry(client, "GET", "http://example.com")

        assert client.request.await_count == 2  # initial + 1 retry

    async def test_backoff_jitter_increases(self):
        client = MagicMock()
        client._max_retries = 3
        client._backoff_base = 1.0
        client.request = AsyncMock(return_value=MagicMock(status_code=503))

        sleeps = []

        async def capture_sleep(duration):
            sleeps.append(duration)

        with patch("rentals_assistant.http.asyncio.sleep", side_effect=capture_sleep), pytest.raises(httpx.HTTPStatusError):
            await fetch_with_retry(client, "GET", "http://example.com")

        # 3 retries means 3 sleeps (after attempts 0, 1, 2; attempt 3 is last and raises)
        assert len(sleeps) == 3
        # Backoff should increase: base * 2^attempt + jitter
        assert sleeps[1] >= sleeps[0]  # 2nd delay >= 1st delay (roughly)
        # Jitter means values aren't exact powers of 2
        assert all(s != int(s) for s in sleeps)  # has fractional part from jitter


class TestFetchWithDelay:
    async def test_sleeps_before_request(self):
        client = MagicMock()
        client._max_retries = 3
        client._backoff_base = 1.0
        mock_response = MagicMock(status_code=200)
        client.request = AsyncMock(return_value=mock_response)

        with patch("rentals_assistant.http.asyncio.sleep") as mock_sleep, patch(
            "rentals_assistant.http.random.uniform", return_value=2.5
        ):
            response = await fetch_with_delay(
                client, "http://example.com", min_delay=1.0, max_delay=3.0
            )

        mock_sleep.assert_any_call(2.5)
        assert response.status_code == 200

    async def test_passes_method_and_kwargs(self):
        client = MagicMock()
        client._max_retries = 3
        client._backoff_base = 1.0
        mock_response = MagicMock(status_code=200)
        client.request = AsyncMock(return_value=mock_response)

        with patch("rentals_assistant.http.asyncio.sleep"), patch(
            "rentals_assistant.http.random.uniform", return_value=0.1
        ):
            response = await fetch_with_delay(
                client,
                "http://example.com",
                method="POST",
                json={"key": "value"},
            )

        assert response.status_code == 200
        client.request.assert_awaited_once_with(
            "POST", "http://example.com", json={"key": "value"}
        )
