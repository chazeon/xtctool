"""Container magic: "XTCH" for 2-bit XTH pages, "XTC\\0" for 1-bit XTG pages."""

import struct

import pytest

from xtctool.core.xtc import XTCReader, XTCWriter

XTG_FRAME = b"XTG\x00" + bytes(18) + bytes(8)
XTH_FRAME = b"XTH\x00" + bytes(18) + bytes(8)


@pytest.mark.parametrize(
    "page_format, frame, magic",
    [("xth", XTH_FRAME, b"XTCH"), ("xtg", XTG_FRAME, b"XTC\x00")],
)
def test_container_magic_follows_page_format(tmp_path, page_format, frame, magic):
    path = tmp_path / f"book.{page_format}.xtc"
    XTCWriter(page_format=page_format).write(str(path), [frame, frame])
    assert path.read_bytes()[:4] == magic


@pytest.mark.parametrize("page_format, frame", [("xth", XTH_FRAME), ("xtg", XTG_FRAME)])
def test_reader_accepts_both_containers(tmp_path, page_format, frame):
    path = tmp_path / "book.xtc"
    XTCWriter(page_format=page_format).write(str(path), [frame, frame, frame])
    frames = XTCReader().read(str(path))
    assert frames == [frame, frame, frame]


def test_reader_rejects_other_magic(tmp_path):
    path = tmp_path / "book.xtc"
    XTCWriter(page_format="xtg").write(str(path), [XTG_FRAME])
    data = bytearray(path.read_bytes())
    data[:4] = struct.pack("<I", 0x12345678)
    path.write_bytes(bytes(data))
    with pytest.raises(ValueError):
        XTCReader().read(str(path))
