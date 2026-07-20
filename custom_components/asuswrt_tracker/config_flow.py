from __future__ import annotations

import ipaddress
import socket
from typing import Any

from aiohttp import ClientSession
from asusrouter import AsusRouter, AsusRouterError
from asusrouter.tools.connection import get_cookie_jar
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.device_registry import format_mac

from .const import (
    CONF_POLLING_INTERVAL,
    CONF_TRACKING_IPS,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    MAX_POLLING_INTERVAL,
    MIN_POLLING_INTERVAL,
)

RESULT_CONN_ERROR = "cannot_connect"
RESULT_INVALID_IPS = "invalid_tracking_ips"
RESULT_INVALID_HOST = "invalid_host"
RESULT_UNKNOWN = "unknown"


def parse_tracking_ips(value: str) -> list[str]:
    """Parse newline separated IP addresses."""
    ips: list[str] = []
    seen: set[str] = set()
    for raw in value.splitlines():
        item = raw.strip()
        if not item:
            continue
        ip = str(ipaddress.ip_address(item))
        if ip not in seen:
            ips.append(ip)
            seen.add(ip)
    return ips


def validate_tracking_ips(value: str) -> list[str]:
    """Validate and return tracking IPs."""
    ips = parse_tracking_ips(value)
    if not ips:
        raise ValueError("at least one tracking IP is required")
    return ips


def _get_ip(host: str) -> str | None:
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None


async def _check_connection(
    session: ClientSession, user_input: dict[str, Any]
) -> tuple[str, str | None]:
    api = AsusRouter(
        hostname=user_input[CONF_HOST],
        username=user_input[CONF_USERNAME],
        password=user_input[CONF_PASSWORD],
        use_ssl=False,
        session=session,
    )

    try:
        await api.async_connect()
        identity = await api.async_get_identity()
    except (AsusRouterError, OSError):
        return RESULT_CONN_ERROR, None
    except Exception:
        return RESULT_UNKNOWN, None
    finally:
        try:
            await api.async_disconnect()
        except Exception:
            pass

    unique_id = format_mac(identity.mac) if identity.mac else user_input[CONF_HOST]
    return "success", unique_id


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ASUSWRT Tracker."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            if not await self.hass.async_add_executor_job(_get_ip, user_input[CONF_HOST]):
                errors[CONF_HOST] = RESULT_INVALID_HOST

            try:
                validate_tracking_ips(user_input[CONF_TRACKING_IPS])
            except ValueError:
                errors[CONF_TRACKING_IPS] = RESULT_INVALID_IPS

            if not errors:
                session = async_create_clientsession(self.hass, cookie_jar=get_cookie_jar())
                result, unique_id = await _check_connection(session, user_input)
                if result == "success":
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=user_input[CONF_HOST],
                        data=user_input,
                    )
                errors["base"] = result

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for ASUSWRT Tracker."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        current = {**self._entry.data, **self._entry.options}

        if user_input is not None:
            try:
                validate_tracking_ips(user_input[CONF_TRACKING_IPS])
            except ValueError:
                errors[CONF_TRACKING_IPS] = RESULT_INVALID_IPS

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current),
            errors=errors,
        )


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(
                CONF_TRACKING_IPS, default=defaults.get(CONF_TRACKING_IPS, "")
            ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            vol.Required(
                CONF_POLLING_INTERVAL,
                default=defaults.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_POLLING_INTERVAL,
                    max=MAX_POLLING_INTERVAL,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_TRACKING_IPS, default=defaults.get(CONF_TRACKING_IPS, "")
            ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            vol.Required(
                CONF_POLLING_INTERVAL,
                default=defaults.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_POLLING_INTERVAL,
                    max=MAX_POLLING_INTERVAL,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )
