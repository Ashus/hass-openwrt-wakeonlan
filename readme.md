# OpenWrt Wake-on-LAN Integration for Home Assistant

Custom integration to wake devices over the network using Wake-on-LAN (WoL) via SSH on OpenWrt routers.

---

## Features

- Sends Wake-on-LAN magic packets remotely via SSH using the `etherwake` command on the OpenWrt device.
- Configurable SSH connection with private key authentication.
- Device and network interface discovery via SSH.
- Simple button entity to trigger WoL per configured device.
- User-friendly config flow with device and interface selection.
- Error handling with meaningful feedback in the UI.

---

## Installation

1. Copy the `openwrt_wakeonlan` folder to your Home Assistant `custom_components` directory: `/config/custom_components/openwrt_wakeonlan/`

2. Restart Home Assistant.

3. Add integration via **Settings > Devices & Services > Add Integration > OpenWrt Wake-on-LAN**.

---

## Configuration

### SSH Credentials

- Hostname or IP of your OpenWrt router.
- SSH username (usually `root`).
- Path to your private SSH key file (must be accessible by Home Assistant, on some installation types the default is `/config/ssh_keys/id_ed25519`).

### Device Selection

- After a successful SSH connection, the integration will fetch known devices (from DHCP leases and ARP neighbors).
- Device names will be appended to the list automatically if possible.
- Select the device MAC address and desired network interface for WoL (usually `br-lan`).

---

## Usage

- After configuration, a button entity will be created for each device.
- Pressing the button sends the Wake-on-LAN magic packet to the device over SSH.
- Notifications inform about any failures.
- If you replace a network card (change MAC address), you will need to remove the old configuration with a button and add a new one.

---

## Requirements

- OpenWrt router with `etherwake` package installed.
- SSH server access is enabled and port properly forwarded on the router.
- Public SSH key is listed in trusted SSH keys on your router in **System > Administration > SSH-Keys**.
- Home Assistant with custom components support.

---

## Troubleshooting

- Without further effort you cannot know if the computer is properly configured to react to the magic packet. Computers need to be configured in BIOS/UEFI configuration, and also the OS must be ready to wake up when this packet comes from the network interface. This is out of the scope of this implementation.
- **SSH connection failed:** Verify SSH host, user, and key are correct, host is reachable, and a key file has proper permissions. Accepted key types are Ed25519 and RSA.
- **Failed to retrieve devices from the router:** Ensure your OpenWrt is on the latest release, 24.10 or newer.
- **Etherwake command not found on remote host:** Install `etherwake` on OpenWrt (`opkg install etherwake` or via UI: **System > Software**).

---

## Localization

Supports translation of UI strings for error messages and notifications. If new translations are needed, please open a pull request.

---

## Development & Contribution

Pull requests and issues are welcome!  
Please adhere to Home Assistant integration guidelines.

---

## License

MIT License

---

## Author

Ashus (with heavy assistance by ChatGPT)
