from pathlib import Path

DOCS_FILE = Path(__file__).parent.parent / "docs" / "telegram-setup.md"


def test_telegram_setup_doc_exists():
    assert DOCS_FILE.exists(), "docs/telegram-setup.md must exist"


def test_telegram_setup_doc_has_required_sections():
    content = DOCS_FILE.read_text(encoding="utf-8")
    required = [
        "BotFather",        # section: create bot via @BotFather
        "chat_id",          # section: how to get chat_id
        "TELEGRAM_TOKEN",   # section: where to put the token in .env
        "TELEGRAM_CHAT_ID", # section: where to put the chat_id in .env
        ".env",             # section: .env file configuration
    ]
    for keyword in required:
        assert keyword in content, f"docs/telegram-setup.md must mention '{keyword}'"


def test_telegram_setup_doc_has_validation_step():
    content = DOCS_FILE.read_text(encoding="utf-8")
    # Must include how to verify the setup works (smoke test / curl / bot message check)
    has_validation = any(kw in content for kw in ["verify", "test", "curl", "smoke"])
    assert has_validation, "Guide must include a validation / smoke-test step"
