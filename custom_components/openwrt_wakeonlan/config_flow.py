import asyncio
import json
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import *
import paramiko
import re
from concurrent.futures import ThreadPoolExecutor

class SSHWOLConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self.known_devices = []
        self.interfaces = []
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _parse_leases(self, output):
        leases = {}
        for line in output.strip().splitlines():
            parts = line.split()
            if len(parts) >= 4:
                mac = parts[1].lower()
                hostname = parts[3]
                leases[mac] = hostname
        return leases

    def _parse_neigh(self, output):
        devices = {}
        for line in output.strip().splitlines():
            match = re.match(r'(\d+\.\d+\.\d+\.\d+).*lladdr ([0-9a-f:]{17})', line)
            if match:
                ip = match.group(1)
                mac = match.group(2).lower()
                devices[mac] = ip
        return devices

    def _parse_interfaces(self, output):
        interfaces = []
        try:
            data = json.loads(output)
            for iface in data.get("interface", []):
                name = iface.get("l3_device")
                if name and name not in ("lo", "loopback"):
                    interfaces.append(name)
        except Exception:
            pass
        return interfaces if interfaces else ["br-lan"]

    async def _connect_ssh(self, host, user, key_path):
        loop = asyncio.get_running_loop()
        try:
            def load_key():
                try:
                    return paramiko.Ed25519Key.from_private_key_file(key_path)
                except Exception:
                    return paramiko.RSAKey.from_private_key_file(key_path)

            key = await loop.run_in_executor(self._executor, load_key)

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            await loop.run_in_executor(self._executor, lambda: ssh.connect(host, username=user, pkey=key))
            return ssh
        except Exception as e:
            raise e

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            ssh_host = user_input[CONF_SSH_HOST]
            ssh_user = user_input[CONF_SSH_USER]
            ssh_key = user_input[CONF_SSH_KEY]

            try:
                ssh = await self._connect_ssh(ssh_host, ssh_user, ssh_key)

                def run_command(cmd):
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    return stdout.read().decode()

                leases_out = await asyncio.get_running_loop().run_in_executor(self._executor, lambda: run_command("cat /tmp/dhcp.leases"))
                neigh_out = await asyncio.get_running_loop().run_in_executor(self._executor, lambda: run_command("ip neigh show dev br-lan"))
                interfaces_out = await asyncio.get_running_loop().run_in_executor(self._executor, lambda: run_command("ubus call network.interface dump"))
                ssh.close()

                # Kontrola, že příkazy vrátily data
                if not leases_out.strip() or not neigh_out.strip() or not interfaces_out.strip():
                    errors["base"] = "no_data"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=vol.Schema({
                            vol.Required(CONF_SSH_HOST): str,
                            vol.Required(CONF_SSH_USER): str,
                            vol.Required(CONF_SSH_KEY): str,
                        }),
                        errors=errors
                    )

                leases = self._parse_leases(leases_out)
                neigh = self._parse_neigh(neigh_out)
                interfaces = self._parse_interfaces(interfaces_out)

                # Další kontrola, že máme nějaká data
                if not neigh or not interfaces:
                    errors["base"] = "no_data"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=vol.Schema({
                            vol.Required(CONF_SSH_HOST): str,
                            vol.Required(CONF_SSH_USER): str,
                            vol.Required(CONF_SSH_KEY): str,
                        }),
                        errors=errors
                    )

                devices_with_name = []
                devices_without_name = []

                for mac, ip in neigh.items():
                    name = leases.get(mac)
                    if name:
                        devices_with_name.append((mac, name))
                    else:
                        devices_without_name.append(mac)

                devices_with_name.sort(key=lambda x: x[1].lower())
                devices_without_name.sort()

                self.known_devices = []
                for mac, name in devices_with_name:
                    label = f"{mac} ({name})"
                    self.known_devices.append((label, {CONF_NAME: name, CONF_MAC: mac}))
                for mac in devices_without_name:
                    self.known_devices.append((mac, {CONF_NAME: mac, CONF_MAC: mac}))

                self.interfaces = interfaces or ["br-lan"]

                self.context["user_input"] = user_input
                return await self.async_step_select_device()
            except Exception:
                errors["base"] = "ssh_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_SSH_HOST): str,
                vol.Required(CONF_SSH_USER): str,
                vol.Required(CONF_SSH_KEY): str,
            }),
            errors=errors
        )

    async def async_step_select_device(self, user_input=None) -> FlowResult:
        if user_input is not None:
            selected = user_input["device"]
            interface = user_input["interface"]
            device_data = dict(self.known_devices)[selected]
            self.context["device_data"] = device_data
            return self.async_create_entry(
                title=f"OpenWrt Wake-on-LAN: {device_data.get(CONF_NAME, device_data.get(CONF_MAC))} ({interface})",
                data={
                    **self.context["user_input"],
                    CONF_NAME: device_data.get(CONF_NAME, device_data.get(CONF_MAC)),
                    CONF_MAC: device_data[CONF_MAC],
                    CONF_INTERFACE: interface,
                }
            )

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("device"): vol.In([label for label, _ in self.known_devices]),
                vol.Required("interface"): vol.In(self.interfaces),
            }),
            description_placeholders={"interfaces": ", ".join(self.interfaces)},
        )