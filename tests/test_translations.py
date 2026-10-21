"""Every language has every English string, with the same placeholders."""
import json
import re
from pathlib import Path

import pytest

FOLDER = Path(__file__).parent.parent / "custom_components" / "gramps_ha"


def flat(node, prefix=""):
    out = {}
    for key, value in node.items():
        out.update(flat(value, f"{prefix}{key}.") if isinstance(value, dict) else {prefix + key: value})
    return out


EN = flat(json.loads((FOLDER / "translations" / "en.json").read_text()))


def test_strings_json_is_english():
    assert flat(json.loads((FOLDER / "strings.json").read_text())) == EN


@pytest.mark.parametrize("lang", ["de", "fr", "it", "bs"])
def test_language_is_complete(lang):
    other = flat(json.loads((FOLDER / "translations" / f"{lang}.json").read_text()))
    assert set(other) == set(EN)
    for key, text in EN.items():
        assert set(re.findall(r"{\w+}", other[key])) == set(re.findall(r"{\w+}", text)), key
