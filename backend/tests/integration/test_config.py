from app.core.config import get_settings


def test_settings_load() -> None:
    settings = get_settings()
    assert settings.app_name == "project-monitoring-ai"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.database_url.startswith("postgresql")
