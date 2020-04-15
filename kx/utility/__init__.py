#!/usr/bin/env python3
#
# Contains utility functions that don't fit anywhere else.

import __main__  # type: ignore
import hashlib
import json
import pathlib
import typing


def project_directory() -> pathlib.Path:
    "Returns the path to the project's top-level directory"
    return pathlib.Path(__main__.__file__).parent.parent


def merge_complex_dictionaries(*args) -> dict:
    """
    Given a list of dictionaries, merge the dictionaries from left to right:

    - dictionaries are merged recursively
    - lists with the same key are appended
    - conflicting keys are overwritten by the value on the right side

    Returns the resulting merged dictionary
    """
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


def sha512_hash(o: typing.Union[str, dict]) -> str:
    if isinstance(o, dict):
        string_data = json.dumps(o, sort_keys=True)
    else:
        string_data = str(o)
    return hashlib.sha512(string_data.encode()).hexdigest()
