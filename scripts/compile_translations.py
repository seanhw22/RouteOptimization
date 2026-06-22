"""Compile the simple project gettext catalogs when GNU gettext is unavailable."""

from __future__ import annotations

import ast
import struct
from pathlib import Path


def compile_po(source: Path, destination: Path) -> None:
    entries: dict[str, str] = {}
    msgid = msgstr = None
    active = None
    for raw in source.read_text(encoding='utf-8').splitlines():
        if raw.startswith('msgid '):
            if msgid is not None:
                entries[msgid] = msgstr or ''
            msgid, msgstr, active = ast.literal_eval(raw[6:]), '', 'id'
        elif raw.startswith('msgstr '):
            msgstr, active = ast.literal_eval(raw[7:]), 'str'
        elif raw.startswith('"') and active == 'id':
            msgid += ast.literal_eval(raw)
        elif raw.startswith('"') and active == 'str':
            msgstr += ast.literal_eval(raw)
    if msgid is not None:
        entries[msgid] = msgstr or ''

    keys = sorted(entries)
    originals = b'\0'.join(key.encode('utf-8') for key in keys)
    translations = b'\0'.join(entries[key].encode('utf-8') for key in keys)
    count, header = len(keys), 7 * 4
    original_offset, translation_offset = header, header + count * 8
    original_data_offset = translation_offset + count * 8
    translation_data_offset = original_data_offset + len(originals) + (1 if originals else 0)
    original_table, translation_table = [], []
    offset = original_data_offset
    for key in keys:
        encoded = key.encode('utf-8')
        original_table.append((len(encoded), offset))
        offset += len(encoded) + 1
    offset = translation_data_offset
    for key in keys:
        encoded = entries[key].encode('utf-8')
        translation_table.append((len(encoded), offset))
        offset += len(encoded) + 1
    data = [struct.pack('<7I', 0x950412DE, 0, count, original_offset, translation_offset, 0, translation_data_offset)]
    data.extend(struct.pack('<2I', *item) for item in original_table)
    data.extend(struct.pack('<2I', *item) for item in translation_table)
    data.extend([originals + b'\0', translations + b'\0'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b''.join(data))


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    compile_po(root / 'locale' / 'id' / 'LC_MESSAGES' / 'django.po', root / 'locale' / 'id' / 'LC_MESSAGES' / 'django.mo')
