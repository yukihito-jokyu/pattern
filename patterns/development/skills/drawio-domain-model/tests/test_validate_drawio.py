"""Exercise accepted exports and representative broken deliverables in temporary files."""

import base64
import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote
import zlib

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/drawio-domain-model/scripts/validate_drawio.py"
spec = importlib.util.spec_from_file_location("validate_drawio", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

MODEL = '''<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="a" value="顧客 &amp; 注文 &lt;確認&gt;" vertex="1" parent="1"><mxGeometry x="0" y="0" width="100" height="80" as="geometry"/></mxCell>
<mxCell id="b" vertex="1" parent="1"><mxGeometry x="200" y="0" width="100" height="80" as="geometry"/></mxCell>
<mxCell id="e" edge="1" parent="1" source="a" target="b"><mxGeometry relative="1" as="geometry"/></mxCell>
</root></mxGraphModel>'''
XML = '<mxfile><diagram id="p1" name="概念">' + MODEL + '</diagram></mxfile>'


def chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def png(xml=XML, kind=b"zTXt", pixels=b"\0\xff\xff\xff", image=None):
    parts = [validator.PNG_SIGNATURE, chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))]
    if xml is not None:
        encoded = quote(xml).encode("ascii")
        payload = {b"tEXt": b"mxGraphModel\0" + encoded,
                   b"zTXt": b"mxGraphModel\0\0" + zlib.compress(encoded),
                   b"iTXt": b"mxGraphModel\0\1\0\0\0" + zlib.compress(encoded)}[kind]
        parts.append(chunk(kind, payload))
    parts.extend([chunk(b"IDAT", zlib.compress(pixels) if image is None else image), chunk(b"IEND", b"")])
    return b"".join(parts)


class DiagramValidationTests(unittest.TestCase):
    def invoke(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "diagram.drawio.png"
            path.write_bytes(data)
            result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(path.read_bytes(), data, "検査が入力ファイルを書き換えてはいけない")
            return result

    def assert_rejected(self, data, message):
        result = self.invoke(data)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(message, result.stderr)

    def test_native_example_preserves_all_three_pages(self):
        width, height, names = validator.validate(ROOT / "examples/order-cancellation.drawio.png")
        self.assertGreater(width, 100)
        self.assertGreater(height, 100)
        self.assertEqual(names, ["概念モデル", "設計候補", "注文状態遷移"])

    def test_text_variants_and_special_characters(self):
        for kind in (b"tEXt", b"zTXt", b"iTXt"):
            with self.subTest(kind=kind):
                result = self.invoke(png(kind=kind))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("1 pages: 概念", result.stdout)

    def test_all_pages_are_checked_including_compressed_pages(self):
        compressor = zlib.compressobj(wbits=-15)
        compressed = base64.b64encode(compressor.compress(quote(MODEL).encode()) + compressor.flush()).decode()
        xml = XML.replace('</mxfile>', '<diagram id="p2" name="設計">' + compressed + '</diagram></mxfile>')
        self.assertEqual(self.invoke(png(xml)).returncode, 0)
        broken = xml.replace(compressed, compressed[:-2] + '!?')
        self.assert_rejected(png(broken), "ERROR:")
        bad_model = MODEL.replace('target="b"', 'target="missing"')
        self.assert_rejected(png(XML.replace('</mxfile>', '<diagram id="p2">' + bad_model + '</diagram></mxfile>')), "接続先")

    def test_invalid_pngs_and_broken_image_payload(self):
        cases = [
            (b"not a png", "シグネチャ"),
            (png()[:-3], "途中"),
            (png()[:-12], "必須"),
            (png(None), "図データ"),
            (png(image=b"not zlib"), "ERROR:"),
            (png(pixels=b"\0\xff"), "行サイズ"),
            (png(pixels=b"\5\xff\xff\xff"), "フィルター"),
        ]
        for data, message in cases:
            with self.subTest(message=message):
                self.assert_rejected(data, message)
        damaged = bytearray(png())
        damaged[29] ^= 1
        self.assert_rejected(bytes(damaged), "CRC")

    def test_broken_embedded_xml_and_graph(self):
        cases = [
            ("<mxfile>", "ERROR:"),
            ("<mxfile/>", "ページ"),
            (XML.replace('id="b"', 'id="a"'), "セルID"),
            (XML.replace('parent="1"', 'parent="missing"', 1), "親"),
            (XML.replace('source="a"', 'source="missing"'), "接続先"),
            (XML.replace(' target="b"', ''), "接続先"),
            (XML.replace('<mxGeometry relative="1" as="geometry"/>', ''), "ジオメトリ"),
            (XML.replace('width="100"', 'width="0"', 1), "幅"),
            (XML.replace('x="200"', 'x="nan"'), "座標"),
            (XML.replace('id="1" parent="0"', 'id="1" parent="b"'), "循環"),
            ('<!DOCTYPE mxfile [<!ENTITY test "value">]>' + XML, "実体"),
        ]
        for xml, message in cases:
            with self.subTest(message=message):
                self.assert_rejected(png(xml), message)

    def test_duplicate_metadata_is_not_accepted(self):
        duplicate = chunk(b"tEXt", b"mxGraphModel\0" + quote(XML).encode())
        data = png()
        self.assert_rejected(data[:-12] + duplicate + data[-12:], "複数")
        plain = png(None)
        broken = chunk(b"zTXt", b"mxGraphModel\0\0not compressed XML")
        self.assert_rejected(plain[:-12] + broken + plain[-12:], "ERROR:")

    def test_compressed_pages_share_the_expansion_limit(self):
        model = ('<mxGraphModel note="' + 'x' * (24 * 1024 * 1024) +
                 '"><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>')
        compressor = zlib.compressobj(wbits=-15)
        compressed = base64.b64encode(compressor.compress(quote(model).encode()) + compressor.flush()).decode()
        xml = '<mxfile>' + ''.join(f'<diagram id="p{i}">{compressed}</diagram>' for i in range(3)) + '</mxfile>'
        self.assert_rejected(png(xml), "合計")

    def test_duplicate_metadata_is_rejected_before_decompression(self):
        data = png()
        duplicate = chunk(b"zTXt", b"mxGraphModel\0\0invalid compressed data")
        self.assert_rejected(data[:-12] + duplicate + data[-12:], "複数")

    def test_image_and_metadata_share_the_same_limit(self):
        metadata_size = len(quote(XML).encode("ascii"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "diagram.drawio.png"
            path.write_bytes(png())
            with patch.object(validator, "MAX_EXPANDED", metadata_size + 4):
                self.assertEqual(validator.validate(path)[2], ["概念"])
            with patch.object(validator, "MAX_EXPANDED", metadata_size + 3):
                with self.assertRaisesRegex(validator.ValidationError, "合計"):
                    validator.validate(path)

    def test_missing_input_reports_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(SCRIPT), str(Path(directory) / "missing.png")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR:", result.stderr)


if __name__ == "__main__":
    unittest.main()
