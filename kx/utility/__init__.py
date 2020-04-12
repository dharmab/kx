#!/usr/bin/env python3

import __main__  # type: ignore
import pathlib


def project_directory() -> pathlib.Path:
    return pathlib.Path(__main__.__file__).parent.parent


def merge_complex_dictionaries(*args) -> dict:
    result: dict = {}

    def merge(left: dict, right: dict) -> None:
        for key in right:
            if key in left:
                if isinstance(left[key], dict) and isinstance(right[key], dict):
                    merge(left[key], right[key])
                elif isinstance(left[key], list) and isinstance(right[key], list):
                    left[key].extend(right[key])
                else:
                    left[key] = right[key]
            else:
                left[key] = right[key]

    for d in args:
        assert isinstance(d, dict)
        merge(result, d)

    return result
