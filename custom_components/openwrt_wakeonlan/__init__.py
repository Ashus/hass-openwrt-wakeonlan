from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.config import ConfigType
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers import config_validation

from .const import DOMAIN

CONFIG_SCHEMA = config_validation.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    translations = await async_get_translations(hass, hass.config.language, DOMAIN)
    hass.data.setdefault(DOMAIN, {})["translations"] = translations
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, ["button"])
    return True