from __future__ import annotations

import ipaddress

from src.models import DeviceConfig, Intent


def generate_config(intent: Intent) -> DeviceConfig:
    if intent.protocol == "ospf":
        return _generate_ospf(intent)
    if intent.protocol == "bgp":
        return _generate_bgp(intent)
    return DeviceConfig({})


def _generate_ospf(intent: Intent) -> DeviceConfig:
    network = ipaddress.ip_network(intent.network or "0.0.0.0/32", strict=False)
    wildcard = _wildcard_mask(network.netmask)
    prefix = "no " if intent.mode == "remove" else ""
    line = f"{prefix}network {network.network_address} {wildcard} area {intent.area or '0'}"
    return DeviceConfig(
        {
            device: [
                f"router ospf {intent.process_id}",
                f" {line}",
            ]
            for device in intent.devices
        }
    )


def _generate_bgp(intent: Intent) -> DeviceConfig:
    prefix = "no " if intent.mode == "remove" else ""
    remote = f" remote-as {intent.remote_asn}" if intent.mode != "remove" else ""
    line = f"{prefix}neighbor {intent.neighbor_ip}{remote}"
    return DeviceConfig(
        {
            device: [
                f"router bgp {intent.local_asn}",
                f" {line}",
            ]
            for device in intent.devices
        }
    )


def _wildcard_mask(netmask: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    octets = str(netmask).split(".")
    return ".".join(str(255 - int(octet)) for octet in octets)

