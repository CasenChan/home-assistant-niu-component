"""Remote control switches for NIU scooters."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NiuConnectionError
from .const import (
    COMMAND_FORTIFICATION_OFF,
    COMMAND_FORTIFICATION_ON,
    CONF_SCOOTER_ID,
    DOMAIN,
)
from .coordinator import NiuDataCoordinator


@dataclass(frozen=True, kw_only=True)
class NiuSwitchEntityDescription(SwitchEntityDescription):
    """Describe a NIU control switch."""

    state_field: str
    command_on: str
    command_off: str
    required_feature: str


SWITCH_DESCRIPTIONS = (
    NiuSwitchEntityDescription(
        key="fortification",
        translation_key="fortification",
        icon="mdi:shield-lock",
        state_field="isFortificationOn",
        command_on=COMMAND_FORTIFICATION_ON,
        command_off=COMMAND_FORTIFICATION_OFF,
        required_feature="fortification_switch",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NIU control switches."""
    coordinator: NiuDataCoordinator = config_entry.runtime_data.coordinator

    async_add_entities(
        NiuControlSwitch(coordinator, description, config_entry)
        for description in SWITCH_DESCRIPTIONS
        if coordinator.is_feature_supported(description.required_feature) is True
    )


class NiuControlSwitch(CoordinatorEntity[NiuDataCoordinator], SwitchEntity):
    """Represent a stateful NIU remote control."""

    entity_description: NiuSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NiuDataCoordinator,
        description: NiuSwitchEntityDescription,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the control switch."""
        super().__init__(coordinator)
        self.entity_description = description

        scooter_id = config_entry.data.get(CONF_SCOOTER_ID, 0)
        self._attr_unique_id = f"niu_scooter_{scooter_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"niu_scooter_{scooter_id}_{coordinator.sn}")},
            name=f"NIU Scooter {scooter_id}",
            manufacturer="NIU",
            model="Electric Scooter",
            configuration_url="https://account.niu.com",
        )

    @property
    def is_on(self) -> bool | None:
        """Return the current switch state reported by the scooter."""
        value = self.coordinator.get_motor_data(self.entity_description.state_field)
        if value is None or value == "":
            return None
        return str(value).lower() in ("1", "true", "on")

    @property
    def available(self) -> bool:
        """Return whether the switch and required vehicle feature are available."""
        return (
            super().available
            and self.coordinator.is_feature_supported(
                self.entity_description.required_feature
            )
            is True
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the vehicle feature on."""
        await self._async_send_command(self.entity_description.command_on)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the vehicle feature off."""
        await self._async_send_command(self.entity_description.command_off)

    async def _async_send_command(self, command: str) -> None:
        """Send a command and expose API failures as Home Assistant errors."""
        try:
            await self.coordinator.async_send_command(command)
        except NiuConnectionError as err:
            raise HomeAssistantError(str(err)) from err
