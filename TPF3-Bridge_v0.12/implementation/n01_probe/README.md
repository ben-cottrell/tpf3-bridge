# Development native adapter

prepared_mod/ is the reusable TPF3 development mod. Its stable package identity is
`tpf3_bridge_n01_c04_20261001`; the current implementation supports native inspection,
fitting, explicit construction and readback, including basic station/operating workflows.
See [live interface usage](../live_python_interface/README.md).

Use normal user staging and save/load activation in a healthy running game. Do not
edit base-game resources, assume hot reload or repair the host environment. No proprietary
game source is included. Generated request modules and reconciliation state are temporary
functional data, not shipped source or permanent audit history. Remove completed diagnostic
material after use; preserve pending-operation state until uncertain effects are resolved.
