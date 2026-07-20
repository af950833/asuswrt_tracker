from __future__ import annotations

from typing import override

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AsusWrtTrackerConfigEntry
from .router import AsusWrtTrackerRouter, TrackedDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AsusWrtTrackerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up tracked IP device_tracker entities."""
    router = entry.runtime_data
    async_add_entities(
        AsusWrtTrackedIp(router, ip_address, device)
        for ip_address, device in router.devices.items()
    )


class AsusWrtTrackedIp(ScannerEntity):
    """Device tracker for one configured IP."""

    _attr_should_poll = False
    _attr_source_type = SourceType.ROUTER

    def __init__(
        self, router: AsusWrtTrackerRouter, ip_address: str, device: TrackedDevice
    ) -> None:
        self._router = router
        self._ip_address = ip_address
        self._device = device
        self._attr_name = ip_address
        self._attr_unique_id = router.entity_unique_id(ip_address)

    @property
    @override
    def unique_id(self) -> str:
        """Return the unique id."""
        return self._attr_unique_id

    @property
    @override
    def is_connected(self) -> bool:
        """Return true when the configured IP is connected."""
        return self._device.connected

    @property
    @override
    def ip_address(self) -> str:
        """Return tracked IP address."""
        return self._ip_address

    @property
    @override
    def hostname(self) -> str | None:
        """Return no hostname."""
        return None

    @property
    @override
    def mac_address(self) -> None:
        """MAC is intentionally not used by this integration."""
        return None

    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._router.signal_update, self._async_update_state
            )
        )

    @callback
    def _async_update_state(self) -> None:
        """Update state from router data."""
        self._device = self._router.devices[self._ip_address]
        self.async_write_ha_state()
