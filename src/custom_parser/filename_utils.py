import re
import unicodedata


def sanitize_filename(name: str) -> str:
    name = str(name)
    name = name.replace("/", " _ ")
    name = re.sub(r'[\\:*?"<>|]', "_", name)
    name = name.strip()
    return name
