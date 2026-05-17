from unittest.mock import MagicMock, patch

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


class TestSendAlert:
    def test_returns_true_on_200(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            result = send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        assert result is True
        mock_post.assert_called_once()

    def test_returns_false_on_http_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("400 Bad Request")
        with patch("httpx.post", return_value=mock_resp):
            result = send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        assert result is False

    def test_returns_false_on_network_exception(self):
        with patch("httpx.post", side_effect=OSError("network unreachable")):
            result = send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        assert result is False

    def test_no_exception_propagates_on_any_failure(self):
        with patch("httpx.post", side_effect=RuntimeError("unexpected boom")):
            result = send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        assert result is False

    def test_posts_to_telegram_send_message_url(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        call_url = mock_post.call_args[0][0]
        assert "api.telegram.org" in call_url
        assert "sendMessage" in call_url
        assert "fake-token" in call_url

    def test_sends_to_correct_chat_id(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        payload = mock_post.call_args[1]["json"]
        assert payload["chat_id"] == "999888"


class TestConfigErrorPropagation:
    def test_config_error_propagates_when_settings_is_none(self):
        with patch(
            "rentals_assistant.notifier.load_config",
            side_effect=ConfigError("missing TELEGRAM_TOKEN"),
        ), pytest.raises(ConfigError):
            send_alert(_listing(), _perfect_result(), settings=None)

    def test_no_config_error_when_settings_provided(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        with patch("httpx.post", return_value=mock_resp):
            result = send_alert(_listing(), _perfect_result(), settings=_fake_settings())
        assert result is True


@pytest.mark.integration
def test_integration_sends_real_telegram_message():
    """Sends a real Telegram message. Requires TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env."""
    from rentals_assistant.config import load_config

    try:
        settings = load_config()
    except ConfigError:
        pytest.skip("No Telegram credentials in .env — skipping integration test")

    listing = _listing()
    result = _perfect_result()
    assert send_alert(listing, result, settings=settings) is True
