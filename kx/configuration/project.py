#!/usr/bin/env python3
#
# This module contains static configuration for the project. This provides an
# easy place to track values that aren't user-configurable but need to be
# synchronized across the project.

import dataclasses


@dataclasses.dataclass(frozen=True)
class ProjectConfiguration:
    "Struct that contains global non-configurable settings"
    # Version of Fedora CoreOS
    operating_system_version = "31.20200323.3.2"
    # Version of Kubernetes
    kubernetes_version = "1.18.1"
