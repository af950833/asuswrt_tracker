from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from asusrouter import AsusRouter, AsusRouterError
from asusrouter.modules.client import AsusClient
from asusrouter.modules.connection import ConnectionState
from asusrouter.modules.data import AsusData
from asusrouter.tools.connection import get_cookie_jar

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get as async_get_entity_registry,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.device_registry import format_mac
from homeassistant.exceptions import ConfigEntryNotReady

from .config_flow import parse_tracking_ips
from .const import (
    CONF_BINARY_SENSOR_IPS,
    CONF_POLLING_INTERVAL,
    CONF_TRACKING_IPS,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TrackedDevice:
    """Tracked client state."""

    ip_address: str
    connected: bool = False


class AsusWrtTrackerRouter:
    """Minimal HTTP-only ASUSWRT presence tracker."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._api = AsusRouter(
            hostname=entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            use_ssl=False,
            session=async_create_clientsession(hass, cookie_jar=get_cookie_jar()),
        )
        self._devices: dict[str, TrackedDevice] = {}
        self._on_close: list[CALLBACK_TYPE] = []

    async def async_setup(self) -> None:
        """Connect and start polling."""
        try:
            await self._api.async_connect()
        except (AsusRouterError, OSError) as exc:
            raise ConfigEntryNotReady(f"Cannot connect to ASUSWRT router {self.host}") from exc
        if self.entry.unique_id is None:
            identity = await self._api.async_get_identity()
            if identity.mac:
                self.hass.config_entries.async_update_entry(
                    self.entry, unique_id=format_mac(identity.mac)
                )

        self._sync_configured_devices()
        await self.async_update()
        self.async_on_close(
            async_track_time_interval(
                self.hass,
                self.async_update,
                timedelta(seconds=self.polling_interval),
            )
        )

    async def async_close(self) -> None:
        """Close router resources."""
        for unsub in self._on_close:
            unsub()
        self._on_close.clear()
        await self._api.async_disconnect()

    async def async_update(self, now: datetime | None = None) -> None:
        """Update tracked devices."""
        configured_ips = set(self.configured_ips)

        try:
            clients: dict[str, AsusClient] = await self._api.async_get_data(
                AsusData.CLIENTS, force=True
            )
        except (AsusRouterError, OSError) as exc:
            _LOGGER.warning("Failed to update ASUSWRT Tracker %s: %s", self.host, exc)
            return

        seen_ips: set[str] = set()
        for client in clients.values():
            if (
                client.connection is None
                or client.connection.ip_address is None
                or client.state is not ConnectionState.CONNECTED
            ):
                continue
            ip_address = str(client.connection.ip_address)
            if ip_address in configured_ips:
                seen_ips.add(ip_address)

        _LOGGER.debug(
            "ASUSWRT Tracker %s configured=%s connected=%s",
            self.host,
            sorted(configured_ips),
            sorted(seen_ips),
        )

        changed_ips: list[str] = []
        for ip_address, device in self._devices.items():
            was_connected = device.connected
            device.connected = ip_address in seen_ips
            if was_connected != device.connected:
                changed_ips.append(ip_address)

        if changed_ips:
            _LOGGER.debug(
                "ASUSWRT Tracker %s changed=%s",
                self.host,
                {ip: self._devices[ip].connected for ip in changed_ips},
            )

        async_dispatcher_send(self.hass, self.signal_update)

    def _sync_configured_devices(self) -> None:
        """Create configured IP devices and remove entities for deleted IPs."""
        configured_ips = self.configured_ips

        self._devices = {
            ip_address: self._devices.get(ip_address) or TrackedDevice(ip_address)
            for ip_address in configured_ips
        }

        entity_registry = async_get_entity_registry(self.hass)
        expected_unique_ids = {
            self.entity_unique_id(ip_address) for ip_address in self.device_tracker_ips
        } | {
            self.binary_sensor_unique_id(ip_address) for ip_address in self.binary_sensor_ips
        }
        for entry in list(async_entries_for_config_entry(entity_registry, self.entry.entry_id)):
            if entry.domain not in {Platform.DEVICE_TRACKER, Platform.BINARY_SENSOR}:
                continue
            if entry.unique_id not in expected_unique_ids:
                entity_registry.async_remove(entry.entity_id)

    @callback
    def async_on_close(self, func: CALLBACK_TYPE) -> None:
        """Register a callback to run on unload."""
        self._on_close.append(func)

    def entity_unique_id(self, ip_address: str) -> str:
        """Return a stable device_tracker unique id for a tracked IP."""
        router_id = self.entry.unique_id or self.entry.entry_id
        return f"{router_id}_{ip_address}"

    def binary_sensor_unique_id(self, ip_address: str) -> str:
        """Return a stable binary_sensor unique id for a tracked IP."""
        router_id = self.entry.unique_id or self.entry.entry_id
        return f"{router_id}_binary_sensor_{ip_address}"

    @property
    def devices(self) -> dict[str, TrackedDevice]:
        """Return tracked devices."""
        return self._devices

    @property
    def host(self) -> str:
        """Return router host."""
        return self.entry.data[CONF_HOST]

    @property
    def polling_interval(self) -> int:
        """Return polling interval in seconds."""
        return int(
            self.entry.options.get(
                CONF_POLLING_INTERVAL,
                self.entry.data.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL),
            )
        )

    @property
    def signal_update(self) -> str:
        """Return dispatcher signal for updates."""
        return f"{DOMAIN}-{self.entry.entry_id}-update"

    @property
    def device_tracker_ips(self) -> list[str]:
        """Return configured device tracker IPs."""
        raw = self.entry.options.get(
            CONF_TRACKING_IPS, self.entry.data.get(CONF_TRACKING_IPS, "")
        )
        return parse_tracking_ips(raw)

    @property
    def binary_sensor_ips(self) -> list[str]:
        """Return configured binary sensor IPs."""
        raw = self.entry.options.get(
            CONF_BINARY_SENSOR_IPS, self.entry.data.get(CONF_BINARY_SENSOR_IPS, "")
        )
        return parse_tracking_ips(raw)

    @property
    def configured_ips(self) -> list[str]:
        """Return all configured IPs without duplicates."""
        ips: list[str] = []
        seen: set[str] = set()
        for ip_address in self.device_tracker_ips + self.binary_sensor_ips:
            if ip_address in seen:
                continue
            ips.append(ip_address)
            seen.add(ip_address)
        return ips
