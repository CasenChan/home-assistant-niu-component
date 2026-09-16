"""Remote control buttons for NIU scooters."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NiuConnectionError
from .const import COMMAND_CUSHION_LOCK_ON, CONF_SCOOTER_ID, DOMAIN
from .coordinator import NiuDataCoordinator

BUTTON_DESCRIPTION = ButtonEntityDescription(
    key="open_seat",
    translation_key="open_seat",
    icon="mdi:seat-outline",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NIU remote control buttons."""
    coordinator: NiuDataCoordinator = config_entry.runtime_data.coordinator

    if coordinator.is_feature_supported("cushion_lock_switch") is True:
        async_add_entities([NiuOpenSeatButton(coordinator, config_entry)])


class NiuOpenSeatButton(CoordinatorEntity[NiuDataCoordinator], ButtonEntity):
    """Open the scooter seat compartment."""

    entity_description = BUTTON_DESCRIPTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NiuDataCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the seat button."""
        super().__init__(coordinator)

        scooter_id = config_entry.data.get(CONF_SCOOTER_ID, 0)
        self._attr_unique_id = f"niu_scooter_{scooter_id}_open_seat"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"niu_scooter_{scooter_id}_{coordinator.sn}")},
            name=f"NIU Scooter {scooter_id}",
            manufacturer="NIU",
            model="Electric Scooter",
            configuration_url="https://account.niu.com",
        )

    @property
    def available(self) -> bool:
        """Return whether the seat control is available for this vehicle."""
        return (
            super().available
            and self.coordinator.is_feature_supported("cushion_lock_switch")
            is True
        )

    async def async_press(self) -> None:
        """Open the seat compartment once."""
        try:
            await self.coordinator.async_send_command(COMMAND_CUSHION_LOCK_ON)
        except NiuConnectionError as err:
            raise HomeAssistantError(str(err)) from err
