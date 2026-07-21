from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .router import AsusWrtTrackerRouter

type AsusWrtTrackerConfigEntry = ConfigEntry[AsusWrtTrackerRouter]

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.BINARY_SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: AsusWrtTrackerConfigEntry
) -> bool:
    """Set up ASUSWRT Tracker from a config entry."""
    router = AsusWrtTrackerRouter(hass, entry)
    entry.runtime_data = router

    await router.async_setup()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: AsusWrtTrackerConfigEntry
) -> bool:
    """Unload ASUSWRT Tracker."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_close()
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: AsusWrtTrackerConfigEntry
) -> None:
    """Reload entry on options update."""
    await hass.config_entries.async_reload(entry.entry_id)
