from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up tracked IP binary_sensor entities."""
    router = entry.runtime_data
    async_add_entities(
        AsusWrtTrackedIpBinarySensor(router, ip_address, router.devices[ip_address])
        for ip_address in router.binary_sensor_ips
    )


class AsusWrtTrackedIpBinarySensor(BinarySensorEntity):
    """Binary sensor for one configured IP."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_should_poll = False

    def __init__(
        self, router: AsusWrtTrackerRouter, ip_address: str, device: TrackedDevice
    ) -> None:
        self._router = router
        self._ip_address = ip_address
        self._device = device
        self._attr_name = ip_address
        self._attr_unique_id = router.binary_sensor_unique_id(ip_address)

    @property
    def is_on(self) -> bool:
        """Return true when the configured IP is connected."""
        return self._device.connected

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return extra state attributes."""
        return {"ip": self._ip_address}

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
