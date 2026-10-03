# Development native adapter

prepared_mod/ contains the reusable live development mod. Historical N01 identity
and resource names remain stable; the current code supports native inspection,
fitting, explicit construction and readback, not just read-only activation.
See [live interface usage](../live_python_interface/README.md).

Local continuation records, legacy candidate scripts and three transport-test data
modules remain ignored in place to preserve evidence paths. They are not dependencies
of the current live callback and do not ship. No proprietary game source is included.
