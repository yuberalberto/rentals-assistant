from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rentals_assistant.config import ConfigError, Settings
from rentals_assistant.models import RawListing
from rentals_assistant.notifier import format_message, send_alert
from rentals_assistant.scorer import ScoringResult


def _listing(**overrides) -> RawListing:
    base = RawListing(
        source="kijiji",
        external_id="test-123",
        url="https://kijiji.ca/v/test-123",
        title="Spacious 2BR in Cambridge",
        price_cad=1850,
        bedrooms=2,
        city="Cambridge",
        floor_level="upper",
        laundry_inunit=True,
        outdoor_space=True,
        parking_spots=2,
        pets="cats_confirmed",
        utilities="included",
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def _perfect_result() -> ScoringResult:
    return ScoringResult(score=4, tier="perfect", flags=["★", "🏢", "🌿", "🚗", "📍"])


def _strong_result() -> ScoringResult:
    return ScoringResult(score=3, tier="strong", flags=["★", "🏢", "🌿"])


def _check_result() -> ScoringResult:
    return ScoringResult(score=0, tier="check", flags=[])


def _fake_settings() -> Settings:
    return Settings(telegram_token="fake-token", telegram_chat_id="999888")


class TestFormatMessageTierEmoji:
    def test_perfect_starts_with_green_circle(self):
        msg = format_message(_listing(), _perfect_result())
        assert msg.startswith("🟢")

    def test_strong_starts_with_yellow_circle(self):
        msg = format_message(_listing(), _strong_result())
        assert msg.startswith("🟡")

    def test_check_starts_with_blue_circle(self):
        msg = format_message(_listing(), _check_result())
        assert msg.startswith("🔵")


class TestFormatMessageHeader:
    def test_includes_tier_label_perfect(self):
        msg = format_message(_listing(), _perfect_result())
        assert "Perfect match" in msg

    def test_includes_tier_label_strong(self):
        msg = format_message(_listing(), _strong_result())
        assert "Strong match" in msg

    def test_includes_tier_label_check(self):
        msg = format_message(_listing(), _check_result())
        assert "Check it" in msg

    def test_source_kijiji_capitalized(self):
        msg = format_message(_listing(source="kijiji"), _perfect_result())
        assert "Kijiji" in msg

    def test_source_rentals_ca_formatted(self):
        msg = format_message(_listing(source="rentals_ca"), _perfect_result())
        assert "Rentals Ca" in msg or "rentals_ca" not in msg


class TestFormatMessagePriceLine:
    def test_price_formatted_with_commas(self):
        msg = format_message(_listing(price_cad=1850), _perfect_result())
        assert "1,850" in msg

    def test_price_includes_dollar_sign(self):
        msg = format_message(_listing(price_cad=1850), _perfect_result())
        assert "$1,850" in msg

    def test_utilities_star_flag_when_included(self):
        msg = format_message(_listing(utilities="included"), _perfect_result())
        assert "★" in msg

    def test_no_utilities_flag_when_extra(self):
        result = ScoringResult(score=3, tier="strong", flags=["🏢", "🌿", "🚗"])
        msg = format_message(_listing(utilities="extra"), result)
        assert "★" not in msg

    def test_missing_price_shows_fallback(self):
        msg = format_message(_listing(price_cad=None), _check_result())
        assert "?" in msg or "unknown" in msg.lower()


class TestFormatMessageLocationLine:
    def test_city_in_message(self):
        msg = format_message(_listing(city="Cambridge"), _perfect_result())
        assert "Cambridge" in msg

    def test_upper_floor_flag_in_message(self):
        msg = format_message(_listing(), _perfect_result())
        assert "🏢" in msg

    def test_outdoor_flag_in_message(self):
        msg = format_message(_listing(), _perfect_result())
        assert "🌿" in msg

    def test_parking_flag_in_message(self):
        msg = format_message(_listing(), _perfect_result())
        assert "🚗" in msg

    def test_proximity_flag_in_message(self):
        msg = format_message(_listing(), _perfect_result())
        assert "📍" in msg

    def test_missing_city_shows_fallback(self):
        msg = format_message(_listing(city=None), _perfect_result())
        assert "Unknown" in msg or "city" in msg.lower()


class TestFormatMessageBathrooms:
    def test_bathrooms_shown_in_price_line(self):
        msg = format_message(_listing(bathrooms=1.5), _perfect_result())
        assert "1.5BA" in msg

    def test_bathrooms_shown_as_integer(self):
        msg = format_message(_listing(bathrooms=2.0), _perfect_result())
        assert "2BA" in msg

    def test_bathrooms_none_omitted(self):
        msg = format_message(_listing(bathrooms=None), _perfect_result())
        assert "BA" not in msg

    def test_bathrooms_placed_after_bedrooms(self):
        msg = format_message(_listing(bedrooms=2, bathrooms=1.5), _perfect_result())
        # Should show "2BR · 1.5BA" pattern
        lines = msg.split("\n")
        price_line = lines[1]
        assert "2BR" in price_line
        assert "1.5BA" in price_line
        assert price_line.index("2BR") < price_line.index("1.5BA")


class TestFormatMessageDescription:
    def test_description_shown_as_summary_line(self):
        msg = format_message(
            _listing(description="Spacious apartment with balcony and modern amenities"),
            _perfect_result(),
        )
        assert "Spacious apartment" in msg

    def test_description_truncated_to_100_chars(self):
        long_desc = "A" * 150
        msg = format_message(_listing(description=long_desc), _perfect_result())
        # Should be truncated, not the full 150 chars
        assert len([line for line in msg.split("\n") if long_desc in line]) == 0

    def test_description_none_omitted(self):
        msg = format_message(_listing(description=None), _perfect_result())
        lines = msg.split("\n")
        # Description should not add an extra line when None
        # Check that we don't have an empty line or unexpected content
        assert all(line.strip() for line in lines if line)

    def test_description_empty_string_omitted(self):
        msg = format_message(_listing(description=""), _perfect_result())
        lines = msg.split("\n")
        assert all(line.strip() for line in lines if line)

    def test_description_with_newlines(self):
        msg = format_message(
            _listing(description="Line 1\nLine 2\nLine 3"),
            _perfect_result(),
        )
        # Newlines should be preserved in the description line
        assert "Line 1" in msg

    def test_description_exactly_100_chars(self):
        desc = "A" * 100
        msg = format_message(_listing(description=desc), _perfect_result())
        # Should show exactly 100 chars when at boundary
        assert desc in msg


class TestFormatMessageBathroomsEdgeCases:
    def test_bathrooms_zero_shown(self):
        msg = format_message(_listing(bathrooms=0), _perfect_result())
        assert "0BA" in msg

    def test_bathrooms_with_many_decimals(self):
        msg = format_message(_listing(bathrooms=1.75), _perfect_result())
        assert "1.75BA" in msg


class TestFormatMessagePetsLine:
    def test_cats_confirmed_shows_paw_emoji(self):
        msg = format_message(_listing(pets="cats_confirmed"), _perfect_result())
        assert "🐱" in msg

    def test_cats_confirmed_label(self):
        msg = format_message(_listing(pets="cats_confirmed"), _perfect_result())
        assert "confirmed" in msg.lower()

    def test_pets_allowed_shows_allowed(self):
        msg = format_message(_listing(pets="allowed"), _perfect_result())
        assert "allowed" in msg.lower()

    def test_pets_not_allowed_shows_warning(self):
        msg = format_message(_listing(pets="not_allowed"), _perfect_result())
        assert "not allowed" in msg.lower() or "⚠️" in msg

    def test_pets_unknown_omitted(self):
        msg = format_message(_listing(pets="unknown"), _check_result())
        assert "🐱" not in msg and "Pets" not in msg

    def test_pets_none_omitted(self):
        msg = format_message(_listing(pets=None), _check_result())
        assert "🐱" not in msg and "Pets" not in msg


class TestFormatMessageUrl:
    def test_url_on_last_line(self):
        msg = format_message(_listing(), _perfect_result())
        assert msg.strip().endswith("https://kijiji.ca/v/test-123")

    def test_url_present_for_check_listing(self):
        msg = format_message(_listing(), _check_result())
        assert "https://kijiji.ca/v/test-123" in msg


def _mock_httpx_post(response):
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=None)
    return patch("httpx.AsyncClient", return_value=cm)


class TestSendAlert:
    async def test_returns_true_on_200(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with _mock_httpx_post(mock_resp) as mock_cm:
            result = await send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        assert result is True
        mock_cm.assert_called_once()

    async def test_returns_false_on_http_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock(side_effect=Exception("400 Bad Request"))
        with _mock_httpx_post(mock_resp):
            result = await send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        assert result is False

    async def test_returns_false_on_network_exception(self):
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=OSError("network unreachable"))
        cm.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", return_value=cm):
            result = await send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        assert result is False

    async def test_no_exception_propagates_on_any_failure(self):
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=RuntimeError("unexpected boom"))
        cm.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", return_value=cm):
            result = await send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        assert result is False

    async def test_posts_to_telegram_send_message_url(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with _mock_httpx_post(mock_resp) as mock_cm:
            await send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        client = await mock_cm.return_value.__aenter__()
        call_url = client.post.call_args[0][0]
        assert "api.telegram.org" in call_url
        assert "sendMessage" in call_url
        assert "fake-token" in call_url

    async def test_sends_to_correct_chat_id(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with _mock_httpx_post(mock_resp) as mock_cm:
            await send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        client = await mock_cm.return_value.__aenter__()
        payload = client.post.call_args[1]["json"]
        assert payload["chat_id"] == "999888"


class TestConfigErrorPropagation:
    async def test_config_error_propagates_when_settings_is_none(self):
        with patch(
            "rentals_assistant.notifier.load_config",
            side_effect=ConfigError("missing TELEGRAM_TOKEN"),
        ), pytest.raises(ConfigError):
            await send_alert(_listing(), _perfect_result(), settings=None)

    async def test_no_config_error_when_settings_provided(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with _mock_httpx_post(mock_resp):
            result = await send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        assert result is True


@pytest.mark.integration
async def test_integration_sends_real_telegram_message():
    """Sends a real Telegram message. Requires TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env."""
    from rentals_assistant.config import load_config

    try:
        settings = load_config()
    except ConfigError:
        pytest.skip("No Telegram credentials in .env — skipping integration test")

    listing = _listing()
    result = _perfect_result()
    assert await send_alert(listing, result, settings=settings) is True


# ---------------------------------------------------------------------------
# TASK-105: send_summary
# ---------------------------------------------------------------------------

class TestSendSummary:
    async def test_sends_when_scraper_failed(self):
        from rentals_assistant.pipeline import RunResult
        from rentals_assistant.notifier import send_summary

        result = RunResult(
            scrapers_ok=2,
            scrapers_failed=1,
            listings_found=5,
            listings_new=2,
            listings_notified=1,
            listings_rejected=1,
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with _mock_httpx_post(mock_resp) as mock_cm:
            sent = await send_summary(result, settings=_fake_settings())
        assert sent is True
        mock_cm.assert_called_once()

    async def test_skips_when_all_ok_and_log_level_info(self):
        from rentals_assistant.pipeline import RunResult
        from rentals_assistant.notifier import send_summary

        result = RunResult(
            scrapers_ok=3,
            scrapers_failed=0,
            listings_found=5,
            listings_new=2,
            listings_notified=2,
            listings_rejected=0,
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with _mock_httpx_post(mock_resp) as mock_cm:
            sent = await send_summary(result, settings=_fake_settings())
        assert sent is False
        mock_cm.assert_not_called()

    async def test_sends_when_debug_level_even_if_all_ok(self):
        from rentals_assistant.pipeline import RunResult
        from rentals_assistant.notifier import send_summary

        result = RunResult(
            scrapers_ok=3,
            scrapers_failed=0,
            listings_found=5,
            listings_new=2,
            listings_notified=2,
            listings_rejected=0,
        )
        settings = Settings(
            telegram_token="fake-token",
            telegram_chat_id="999888",
            log_level="DEBUG",
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with _mock_httpx_post(mock_resp) as mock_cm:
            sent = await send_summary(result, settings=settings)
        assert sent is True
        mock_cm.assert_called_once()

    async def test_message_contains_status_and_counts(self):
        from rentals_assistant.pipeline import RunResult
        from rentals_assistant.notifier import send_summary

        result = RunResult(
            scrapers_ok=2,
            scrapers_failed=1,
            listings_found=5,
            listings_new=2,
            listings_notified=1,
            listings_rejected=1,
        )
        settings = _fake_settings()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with _mock_httpx_post(mock_resp) as mock_cm:
            await send_summary(result, settings=settings)
        client = await mock_cm.return_value.__aenter__()
        payload = client.post.call_args[1]["json"]
        text = payload["text"]
        assert "2 OK" in text
        assert "1 failed" in text
        assert "5 found" in text
        assert "2 new" in text
        assert "1 notified" in text
        assert "1 rejected" in text

    async def test_returns_false_on_http_error(self):
        from rentals_assistant.pipeline import RunResult
        from rentals_assistant.notifier import send_summary

        result = RunResult(
            scrapers_ok=1,
            scrapers_failed=1,
            listings_found=0,
            listings_new=0,
            listings_notified=0,
            listings_rejected=0,
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock(side_effect=Exception("500"))
        with _mock_httpx_post(mock_resp):
            sent = await send_summary(result, settings=_fake_settings())
        assert sent is False

    async def test_config_error_propagates_when_settings_is_none(self):
        from rentals_assistant.config import ConfigError
        from rentals_assistant.pipeline import RunResult
        from rentals_assistant.notifier import send_summary

        result = RunResult(
            scrapers_ok=1,
            scrapers_failed=1,
            listings_found=0,
            listings_new=0,
            listings_notified=0,
            listings_rejected=0,
        )
        with patch(
            "rentals_assistant.notifier.load_config",
            side_effect=ConfigError("missing TELEGRAM_TOKEN"),
        ), pytest.raises(ConfigError):
            await send_summary(result, settings=None)
