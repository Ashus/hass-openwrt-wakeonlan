from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.persistent_notification import async_create
from homeassistant.const import CONF_NAME
from .const import *
import paramiko
import logging
import functools

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    devices = [
        {
            CONF_NAME: entry.data.get(CONF_NAME),
            CONF_MAC: entry.data[CONF_MAC],
            CONF_INTERFACE: entry.data[CONF_INTERFACE],
        }
    ]

    buttons = [
        OpenWRTWakeButton(entry.data, device, hass) for device in devices
    ]
    async_add_entities(buttons)


class OpenWRTWakeButton(ButtonEntity):
    def __init__(self, config, device, hass: HomeAssistant):
        name = device.get(CONF_NAME)
        mac = device[CONF_MAC]
        identifier = mac.replace(":", "")

        self._attr_name = name or mac
        self._attr_unique_id = f"openwrt_wakeonlan_{identifier}"
        self.entity_id = f"button.openwrt_wakeonlan_{identifier}"
        self.icon = "mdi:desktop-classic"
        self.device = device
        self.config = config
        self.hass = hass

    def _load_ssh_key(self, path):
        try:
            return paramiko.Ed25519Key.from_private_key_file(path)
        except Exception:
            return paramiko.RSAKey.from_private_key_file(path)

    async def async_press(self) -> None:
        ssh_host = self.config[CONF_SSH_HOST]
        ssh_user = self.config[CONF_SSH_USER]
        ssh_key = self.config[CONF_SSH_KEY]

        command = f"etherwake -D -i {self.device[CONF_INTERFACE]} {self.device[CONF_MAC]}"

        key = await self.hass.async_add_executor_job(self._load_ssh_key, ssh_key)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            connect_func = functools.partial(
                ssh.connect,
                hostname=ssh_host,
                username=ssh_user,
                pkey=key
            )
            await self.hass.async_add_executor_job(connect_func)

            exec_func = functools.partial(ssh.exec_command, command)
            stdin, stdout, stderr = await self.hass.async_add_executor_job(exec_func)

            output = await self.hass.async_add_executor_job(stdout.read)
            error_output = await self.hass.async_add_executor_job(stderr.read)
            exit_code = await self.hass.async_add_executor_job(stdout.channel.recv_exit_status)

            if exit_code != 0:
                error_text = error_output.decode().strip()
                if "not found" in error_text:
                    raise HomeAssistantError("etherwake command not found on remote host. Please install it (e.g., opkg install etherwake).")
                raise HomeAssistantError(f"etherwake failed: {error_text or 'unknown error'}")

            success_output = output.decode().strip()
            if "Sendto worked" in success_output:
                _LOGGER.info(f"Wake-on-LAN succeeded for {self.device.get(CONF_NAME)}")

        except Exception as e:
            _LOGGER.error("Failed to execute etherwake command: %s", e)
            raise HomeAssistantError(f"Failed to wake device: {e}")
        finally:
            try:
                ssh.close()
            except Exception:
                pass