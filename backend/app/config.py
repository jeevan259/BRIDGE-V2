"""Re-export settings from core.config for backward compatibility."""
from app.core.config import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
