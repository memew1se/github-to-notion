import json
import os
import re

PATTERN = r"GITHUB2NOTION_"
PREFIX_PATTERN = re.compile(PATTERN)


def parse_env_variables_to_properties():
    properties = [
        json.loads(value)
        for key, value in os.environ.items()
        if PREFIX_PATTERN.match(key)
    ]
    return {prop["name"]: prop["object"] for prop in properties}
