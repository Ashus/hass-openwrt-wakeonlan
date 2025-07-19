# OpenWrt Wake-on-LAN

Custom integration to wake devices over the network using Wake-on-LAN (WoL) via SSH on OpenWrt routers.

## Features

- Sends Wake-on-LAN magic packets remotely via SSH using the `etherwake` command on the OpenWrt device.
- Configurable SSH connection with private key authentication.
- Device and network interface discovery via SSH.
- Simple button entity to trigger WoL per configured device.
- User-friendly config flow with device and interface selection.
- Error handling with meaningful feedback in the UI.
