"""Tests for Vision OCR text recognition.

    python -m unittest tests.test_ocr
"""
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))


class TestVisionOCRInitOptions(unittest.TestCase):
    def test_recognize_uses_none_options_in_source(self):
        """Ensure initWithURL_options_ passes None rather than {} (#178).

        On macOS 27 and pyobjc 13, passing {} raises:
        ValueError: NSInvalidArgumentException - key does not exist.
        Passing None (nil) is the documented Apple Vision way when no options are provided.
        """
        ocr_source = (SRC / "phone_harness" / "ocr.py").read_text(encoding="utf-8")
        self.assertIn("NSURL.fileURLWithPath_(path), None)", ocr_source)
        self.assertNotIn("NSURL.fileURLWithPath_(path), {})", ocr_source)


try:
    from phone_harness import ocr as _ocr
except ImportError:                      # no pyobjc
    _ocr = None

# What macOS 27's VNRecognizeTextRequest revision 3 lists as supported.
SUPPORTED = ["en-US", "fr-FR", "it-IT", "de-DE", "es-ES", "pt-BR", "zh-Hans",
             "zh-Hant", "yue-Hans", "yue-Hant", "ko-KR", "ja-JP", "ru-RU",
             "uk-UA", "th-TH", "vi-VT", "ar-SA", "ars-SA"]


@unittest.skipIf(_ocr is None, "pyobjc not installed")
class TestRecognitionLanguages(unittest.TestCase):
    """Vision reads English only unless told otherwise. On a Korean Mac the
    Home Screen came back as its clock, and "KB국민은행" as "KBA028"."""

    def pick(self, *preferred):
        return _ocr.pick_languages(SUPPORTED, list(preferred))

    def test_korean_mac_reads_korean_then_english(self):
        self.assertEqual(self.pick("ko-KR"), ["ko-KR", "en-US"])

    def test_english_in_another_region_is_english(self):
        self.assertEqual(self.pick("en-KR"), ["en-US"])

    def test_order_follows_the_mac(self):
        self.assertEqual(self.pick("ja-JP", "ko-KR", "en-GB"),
                         ["ja-JP", "ko-KR", "en-US"])

    def test_chinese_matches_by_script(self):
        self.assertEqual(self.pick("zh-Hant-TW"), ["zh-Hant", "en-US"])
        self.assertEqual(self.pick("zh-Hans-CN"), ["zh-Hans", "en-US"])
        # A bare "zh" names no script; guessing one would misread the other.
        self.assertEqual(self.pick("zh"), ["en-US"])

    def test_region_variants_fall_back_to_the_language(self):
        self.assertEqual(self.pick("pt-PT", "fr-CA"),
                         ["pt-BR", "fr-FR", "en-US"])

    def test_unsupported_languages_leave_english(self):
        self.assertEqual(self.pick("he-IL", "fi-FI"), ["en-US"])

    def test_underscores_and_duplicates(self):
        self.assertEqual(self.pick("ko_KR", "ko-KR", "en-US"),
                         ["ko-KR", "en-US"])

    def test_recognize_sets_the_languages(self):
        source = (SRC / "phone_harness" / "ocr.py").read_text(encoding="utf-8")
        self.assertIn("request.setRecognitionLanguages_(", source)


@unittest.skipUnless(sys.platform == "darwin", "Real Vision OCR requires macOS")
class TestRealVisionOCROnMacOS(unittest.TestCase):
    def test_real_vision_request_handler_init_with_none(self):
        """Runs against real Apple Vision and Foundation on macOS CI."""
        import tempfile
        from Foundation import NSURL
        import Vision
        import Quartz
        from phone_harness import ocr

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name

        try:
            # Generate a 100x100 blank bitmap image with Quartz
            color_space = Quartz.CGColorSpaceCreateDeviceRGB()
            ctx = Quartz.CGBitmapContextCreate(
                None, 100, 100, 8, 400, color_space,
                Quartz.kCGImageAlphaPremultipliedLast)
            Quartz.CGContextSetRGBFillColor(ctx, 1.0, 1.0, 1.0, 1.0)
            Quartz.CGContextFillRect(ctx, Quartz.CGRectMake(0, 0, 100, 100))
            img = Quartz.CGBitmapContextCreateImage(ctx)
            dest = Quartz.CGImageDestinationCreateWithURL(
                NSURL.fileURLWithPath_(tmp_path), "public.png", 1, None)
            Quartz.CGImageDestinationAddImage(dest, img, None)
            Quartz.CGImageDestinationFinalize(dest)

            # Test initWithURL_options_ with None (must not raise NSInvalidArgumentException)
            url = NSURL.fileURLWithPath_(tmp_path)
            handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
            self.assertIsNotNone(handler)

            # Test ocr.recognize end-to-end on real macOS
            window = {"x": 0, "y": 0, "w": 100, "h": 100}
            results = ocr.recognize(tmp_path, window)
            self.assertIsInstance(results, list)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
