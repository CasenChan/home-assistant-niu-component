"""HomeKit-friendly vehicle power lock for NIU scooters."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity, LockEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NiuConnectionError
from .const import COMMAND_ACC_OFF, COMMAND_ACC_ON, CONF_SCOOTER_ID, DOMAIN
from .coordinator import NiuDataCoordinator

LOCK_DESCRIPTION = LockEntityDescription(
    key="vehicle_power",
    translation_key="vehicle_power",
    icon="mdi:power",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the NIU vehicle power lock."""
    coordinator: NiuDataCoordinator = config_entry.runtime_data.coordinator

    if coordinator.is_feature_supported("acc_switch") is True:
        async_add_entities([NiuVehiclePowerLock(coordinator, config_entry)])


class NiuVehiclePowerLock(CoordinatorEntity[NiuDataCoordinator], LockEntity):
    """Represent vehicle power as a lock for HomeKit compatibility.

    Locked means the vehicle power is off; unlocked means it is on.
    """

    entity_description = LOCK_DESCRIPTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NiuDataCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the vehicle power lock."""
        super().__init__(coordinator)

        scooter_id = config_entry.data.get(CONF_SCOOTER_ID, 0)
        self._attr_unique_id = f"niu_scooter_{scooter_id}_vehicle_power"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"niu_scooter_{scooter_id}_{coordinator.sn}")},
            name=f"NIU Scooter {scooter_id}",
            manufacturer="NIU",
            model="Electric Scooter",
            configuration_url="https://account.niu.com",
        )

    @property
    def is_locked(self) -> bool | None:
        """Return locked while vehicle power is off."""
        value = self.coordinator.get_motor_data("isAccOn")
        if value is None or value == "":
            return None
        is_powered_on = str(value).lower() in ("1", "true", "on")
        return not is_powered_on

    @property
    def available(self) -> bool:
        """Return whether remote vehicle power is available."""
        return (
            super().available
            and self.coordinator.is_feature_supported("acc_switch") is True
        )

    async def async_lock(self, **kwargs: Any) -> None:
        """Turn vehicle power off."""
        await self._async_send_command(COMMAND_ACC_OFF)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Turn vehicle power on."""
        await self._async_send_command(COMMAND_ACC_ON)

    async def _async_send_command(self, command: str) -> None:
        """Send a power command and expose API failures as HA errors."""
        try:
            await self.coordinator.async_send_command(command)
        except NiuConnectionError as err:
            raise HomeAssistantError(str(err)) from err
