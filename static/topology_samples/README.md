# Course topology samples

These diagrams belong to this project. They are **not** from the GeNet ICDCS dataset.

| File | Use in viva |
| --- | --- |
| `lab-ospf.svg` | Enterprise campus: Internet/CE edge, **R1-R2-R3 OSPF triangle**, Building A switches/WLAN, Building B SW1 + PCs. Suggest `Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0`. |
| `bgp-edge-peering.svg` | HQ AS 65001 (R1 core, R2 dist, access switches) + branch AS 65002 (R3, SW1). Suggest BGP neighbor `10.1.2.2` on R1. |
| `firewall-dmz-out-of-scope.svg` | HA firewall, DMZ services, inside LAN. **No OSPF/BGP IOS.** |

Copies are served from `static/topology_samples/` for the Topology tab.
