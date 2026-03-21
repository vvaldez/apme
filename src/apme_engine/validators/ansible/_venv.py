"""Ansible version constants for the validator.

The Primary orchestrator owns all venv lifecycle (creation, collection
install, reaping via ``VenvSessionManager``).  This module only exports
the version constants that the validator and its rules need.
"""

SUPPORTED_VERSIONS = ["2.18", "2.19", "2.20"]
DEFAULT_VERSION = "2.20"
