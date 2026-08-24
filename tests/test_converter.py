import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from labelme_json_converter.converter import (  # noqa: E402
    STATUS_COMPATIBLE,
    STATUS_CONVERTED,
    STATUS_FAILED,
    STATUS_SKIPPED,
    convert_document,
    convert_path,
)


def labelme_document(image_path="..\\images\\示例 (2).jpg", image_data="a" * 10000):
    return {
        "version": "5.6.0",
        "flags": {"checked": True},
        "shapes": [
            {
                "label": "下颌骨",
                "points": [[1.25, 2.5], [3.75, 4.0]],
                "group_id": None,
                "description": "保持原样",
                "shape_type": "polygon",
                "flags": {"reviewed": False},
                "mask": None,
                "futureField": {"keep": [1, 2, 3]},
            }
        ],
        "imagePath": image_path,
        "imageData": image_data,
        "imageHeight": 2250,
        "imageWidth": 2000,
        "unknownTopLevel": {"owner": "测试"},
    }


class ConvertDocumentTests(unittest.TestCase):
    def test_changes_only_target_fields_without_mutating_input(self):
        original = labelme_document()
        snapshot = copy.deepcopy(original)

        converted, compatible = convert_document(original)

        self.assertFalse(compatible)
        self.assertEqual(converted["version"], "6.3.0")
        self.assertIsNone(converted["imageData"])
        self.assertEqual(converted["imagePath"], "示例 (2).jpg")
        self.assertEqual(original, snapshot)
        for key in original:
            if key not in {"version", "imageData", "imagePath"}:
                self.assertEqual(converted[key], original[key])

    def test_supports_windows_and_posix_paths(self):
        windows, _ = convert_document(labelme_document(r"C:\data\a b.jpg"))
        posix, _ = convert_document(labelme_document("../images/a b.png"))
        self.assertEqual(windows["imagePath"], "a b.jpg")
        self.assertEqual(posix["imagePath"], "a b.png")

    def test_detects_already_compatible_document(self):
        document = labelme_document("image.jpg", None)
        document["version"] = "6.3.0"
        converted, compatible = convert_document(document)
        self.assertTrue(compatible)
        self.assertEqual(converted, document)


class BatchConversionTests(unittest.TestCase):
    def test_single_file_reduces_size_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "旧版 标注.json"
            output = root / "output"
            source.write_text(
                json.dumps(labelme_document(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            original_bytes = source.read_bytes()

            summary = convert_path(source, output)

            destination = output / source.name
            converted = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(summary.converted, 1)
            self.assertEqual(summary.results[0].status, STATUS_CONVERTED)
            self.assertEqual(source.read_bytes(), original_bytes)
            self.assertLess(destination.stat().st_size, source.stat().st_size)
            self.assertNotIn("a" * 1000, destination.read_text(encoding="utf-8"))
            self.assertEqual(converted["shapes"], labelme_document()["shapes"])
            self.assertTrue(summary.report_path.is_file())

    def test_recursive_batch_continues_after_bad_json_and_excludes_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "输入"
            nested = source / "子目录"
            output = source / "转换结果"
            nested.mkdir(parents=True)
            output.mkdir(parents=True)
            (source / "第一份.JSON").write_text(
                json.dumps(labelme_document("../images/one.jpg")), encoding="utf-8"
            )
            (nested / "第二份.json").write_text(
                json.dumps(labelme_document(r"..\images\two.jpg")), encoding="utf-8"
            )
            (nested / "损坏.json").write_text("{bad json", encoding="utf-8")
            (source / "忽略.txt").write_text("not json", encoding="utf-8")
            (output / "上次结果.json").write_text("{}", encoding="utf-8")

            summary = convert_path(source, output)

            self.assertEqual(summary.total, 3)
            self.assertEqual(summary.converted, 2)
            self.assertEqual(summary.failed, 1)
            self.assertTrue((output / "第一份.JSON").exists())
            self.assertTrue((output / "子目录" / "第二份.json").exists())
            self.assertEqual(
                [result.source.name for result in summary.results if result.status == STATUS_FAILED],
                ["损坏.json"],
            )

    def test_existing_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.json"
            output = root / "output"
            output.mkdir()
            source.write_text(json.dumps(labelme_document()), encoding="utf-8")
            destination = output / source.name
            destination.write_text("do not replace", encoding="utf-8")

            summary = convert_path(source, output)

            self.assertEqual(summary.skipped, 1)
            self.assertEqual(summary.results[0].status, STATUS_SKIPPED)
            self.assertEqual(destination.read_text(encoding="utf-8"), "do not replace")

    def test_compatible_input_is_copied_and_classified(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "compatible.json"
            output = root / "output"
            document = labelme_document("same.jpg", None)
            document["version"] = "6.3.0"
            source.write_text(json.dumps(document), encoding="utf-8")

            summary = convert_path(source, output)

            self.assertEqual(summary.compatible, 1)
            self.assertEqual(summary.results[0].status, STATUS_COMPATIBLE)
            self.assertEqual(
                json.loads((output / source.name).read_text(encoding="utf-8")), document
            )

    def test_non_labelme_json_is_reported_as_failure(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "not-labelme.json"
            source.write_text('{"hello": "world"}', encoding="utf-8")

            summary = convert_path(source, root / "output")

            self.assertEqual(summary.failed, 1)
            self.assertIn("shapes", summary.results[0].message)


if __name__ == "__main__":
    unittest.main()

