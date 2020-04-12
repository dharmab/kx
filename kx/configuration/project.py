#!/usr/bin/env python3

import dataclasses


@dataclasses.dataclass(frozen=True)
class ProjectConfiguration:
    operating_system_version = "31.20200323.3.2"
    kubernetes_version = "1.18.1"
