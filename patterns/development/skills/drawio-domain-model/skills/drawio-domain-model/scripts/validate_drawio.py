#!/usr/bin/env python3
"""Validate the PNG container and every embedded draw.io page; no files are changed."""

import argparse
import base64
import binascii
import math
from pathlib import Path
import struct
import sys
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import zlib

MAX_FILE = 32 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ValidationError(ValueError):
    """Invalid or unsupported diagram."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


class ExpansionBudget:
    """Share one decoded-byte allowance across the image, metadata and pages."""

    def __init__(self):
        self.remaining = MAX_EXPANDED

    def consume(self, size):
        require(size <= self.remaining, "展開データの合計が64MiBを超えます")
        self.remaining -= size


def inflate(data, budget, window=zlib.MAX_WBITS):
    decoder = zlib.decompressobj(window)
    result = decoder.decompress(data, budget.remaining + 1)
    require(len(result) <= budget.remaining and not decoder.unconsumed_tail,
            "展開データの合計が64MiBを超えます")
    require(decoder.eof and not decoder.unused_data, "圧縮データが破損しています")
    budget.consume(len(result))
    return result


def text_chunk(kind, data, budget):
    keyword, separator, rest = data.partition(b"\0")
    require(bool(separator), "PNGテキストチャンクの区切りがありません")
    if keyword != b"mxGraphModel":
        return None
    if kind == b"zTXt":
        require(rest[:1] == b"\0", "未対応のPNGテキスト圧縮方式です")
        return inflate(rest[1:], budget).decode("latin-1")
    if kind == b"iTXt":
        require(len(rest) >= 2 and rest[0] in (0, 1) and rest[1] == 0,
                "不正なiTXt圧縮指定です")
        compressed = rest[0]
        fields = rest[2:].split(b"\0", 2)
        require(len(fields) == 3, "不正なiTXtフィールドです")
        if compressed:
            return inflate(fields[2], budget).decode("utf-8")
        budget.consume(len(fields[2]))
        return fields[2].decode("utf-8")
    budget.consume(len(rest))
    return rest.decode("latin-1")


def read_png(data, budget=None):
    """Return (width, height, embedded XML text), after PNG structural checks."""
    if budget is None:
        budget = ExpansionBudget()
    require(len(data) <= MAX_FILE, "入力が32MiBを超えます")
    require(data.startswith(PNG_SIGNATURE), "PNGシグネチャがありません")
    offset, chunks, image_data, embedded = 8, [], bytearray(), []
    width = height = depth = color = 0
    palette_size = 0
    while offset < len(data):
        require(offset + 12 <= len(data), "PNGチャンクが途中で切れています")
        length, = struct.unpack_from(">I", data, offset)
        require(offset + 12 + length <= len(data), "PNGチャンク長が不正です")
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        checksum, = struct.unpack_from(">I", data, offset + 8 + length)
        require(zlib.crc32(kind + payload) & 0xFFFFFFFF == checksum,
                f"PNG CRCが一致しません: {kind.decode('ascii', errors='replace')}")
        require(all(65 <= c <= 90 or 97 <= c <= 122 for c in kind), "PNGチャンク名が不正です")
        require(chunks or kind == b"IHDR", "先頭チャンクがIHDRではありません")
        if kind == b"IHDR":
            require(not chunks and length == 13, "IHDRが重複または破損しています")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            valid_depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            require(width > 0 and height > 0 and depth in valid_depths.get(color, ()), "PNGの画像形式が不正です")
            require(compression == filtering == 0 and interlace == 0,
                    "通常の非インターレースPNGを指定してください")
        elif kind == b"PLTE":
            require(not palette_size and b"IDAT" not in chunks and length > 0 and length % 3 == 0 and length <= 768,
                    "PNGパレットが不正です")
            palette_size = length // 3
        elif kind == b"IDAT":
            require(b"IDAT" not in chunks or chunks[-1] == b"IDAT", "IDATチャンクが連続していません")
            image_data.extend(payload)
        elif kind == b"IEND":
            require(length == 0 and offset + 12 == len(data), "IENDまたは末尾が不正です")
        elif kind in (b"tEXt", b"zTXt", b"iTXt"):
            require(not embedded or not payload.startswith(b"mxGraphModel\0"),
                    "draw.io図データが複数埋め込まれています")
            value = text_chunk(kind, payload, budget)
            if value is not None:
                embedded.append(value)
        else:
            require(kind != b"acTL", "アニメーションPNGは対象外です")
            require(kind[0] & 32, "未対応の必須PNGチャンクです")
        chunks.append(kind)
        offset += 12 + length
    require(chunks and chunks[-1] == b"IEND" and b"IDAT" in chunks, "必須PNGチャンクが不足しています")
    require(color != 3 or 0 < palette_size <= 2 ** depth, "PNGのパレットがありません")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    row_bytes = (width * channels * depth + 7) // 8
    expected = (row_bytes + 1) * height
    require(expected <= budget.remaining, "展開データの合計が64MiBを超えます")
    pixels = inflate(image_data, budget)
    require(len(pixels) == expected, "PNG画像データの行サイズが一致しません")
    require(all(pixels[row * (row_bytes + 1)] <= 4 for row in range(height)),
            "PNG画像データのフィルター番号が不正です")
    require(len(embedded) == 1, "draw.io図データがないか、複数埋め込まれています")
    return width, height, unquote(embedded[0], errors="strict")


def parse_xml(text):
    require(len(text.encode("utf-8")) <= MAX_EXPANDED, "XMLが64MiBを超えます")
    require("<!DOCTYPE" not in text.upper() and "<!ENTITY" not in text.upper(), "DTD・実体宣言は対象外です")
    return ET.fromstring(text)


def page_models(xml, budget=None):
    if budget is None:
        budget = ExpansionBudget()
        budget.consume(len(xml.encode("utf-8")))
    document = parse_xml(xml)
    if document.tag == "mxGraphModel":
        return [("ページ1", document)]
    require(document.tag == "mxfile", "図データがmxfileではありません")
    pages = document.findall("diagram")
    require(bool(pages), "図のページがありません")
    require(len({p.get("id") for p in pages}) == len(pages) and all(p.get("id") for p in pages),
            "ページIDがないか重複しています")
    models = []
    for number, page in enumerate(pages, 1):
        model = page.find("mxGraphModel")
        if model is None:
            compressed = base64.b64decode((page.text or "").strip(), validate=True)
            model = parse_xml(unquote(inflate(compressed, budget, -15).decode("utf-8"), errors="strict"))
        require(model.tag == "mxGraphModel", "ページの図構造が不正です")
        models.append((page.get("name") or f"ページ{number}", model))
    return models


def validate_model(name, model):
    root = model.find("root")
    require(root is not None, f"{name}: rootがありません")
    cells = list(root.iter("mxCell"))
    ids = {cell.get("id") for cell in cells}
    require(all(cell.get("id") for cell in cells) and len(ids) == len(cells), f"{name}: セルIDがないか重複しています")
    require({"0", "1"} <= ids, f"{name}: 基本セル0・1がありません")
    by_id = {cell.get("id"): cell for cell in cells}
    for cell in cells:
        cid = cell.get("id")
        if cid != "0":
            require(cell.get("parent") in ids, f"{name}/{cid}: 親の参照先がありません")
            visited, cursor = set(), cell
            while cursor.get("id") != "0":
                require(cursor.get("id") not in visited, f"{name}/{cid}: 親参照が循環しています")
                visited.add(cursor.get("id"))
                require(cursor.get("parent") in ids, f"{name}/{cid}: 親の参照先がありません")
                cursor = by_id[cursor.get("parent")]
        if cell.get("edge") == "1":
            require(all(cell.get(key) in ids for key in ("source", "target")),
                    f"{name}/{cid}: 接続先の参照がありません")
        if cell.get("vertex") == "1" or cell.get("edge") == "1":
            geometry = cell.find("mxGeometry[@as='geometry']")
            require(geometry is not None, f"{name}/{cid}: ジオメトリがありません")
            require(all(math.isfinite(float(value)) for key, value in geometry.attrib.items()
                        if key in ("x", "y", "width", "height")), f"{name}/{cid}: 座標値が不正です")
            if cell.get("vertex") == "1" and geometry.get("relative") != "1":
                require(float(geometry.get("width", "0")) > 0 and float(geometry.get("height", "0")) > 0,
                        f"{name}/{cid}: 図形の幅・高さが不正です")


def validate(path):
    with Path(path).open("rb") as source:
        data = source.read(MAX_FILE + 1)
    budget = ExpansionBudget()
    width, height, xml = read_png(data, budget)
    models = page_models(xml, budget)
    for name, model in models:
        validate_model(name, model)
    return width, height, [name for name, _ in models]


def main():
    parser = argparse.ArgumentParser(description="図データ入り.drawio.pngの画像と全ページの構造を検査する")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        width, height, names = validate(args.path)
    except (OSError, ValueError, ET.ParseError, zlib.error, binascii.Error, struct.error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: PNG {width}x{height}; {len(names)} pages: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
