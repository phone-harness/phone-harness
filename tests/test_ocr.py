"""Tests for Vision OCR text recognition.

    python -m unittest tests.test_ocr
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


VISION_LANGUAGES = ["en-US", "fr-FR", "pt-BR", "zh-Hans", "zh-Hant", "yue-Hans",
                    "ko-KR", "ja-JP", "ru-RU", "no-NO", "nb-NO"]


@unittest.skipUnless(sys.platform == "darwin", "ocr imports Vision, which is macOS only")
class TestRecognitionLanguages(unittest.TestCase):
    """Vision accepts an identifier it does not support without an error and
    then reads English only (#91), so tags are resolved before they reach it."""

    def setUp(self):
        from phone_harness import ocr
        self.match = ocr.match_languages

    def test_supported_tags_pass_through_in_order(self):
        self.assertEqual(self.match(["ko-KR", "en-US"], VISION_LANGUAGES), (["ko-KR", "en-US"], []))
        self.assertEqual(self.match(["en-US", "ko-KR"], VISION_LANGUAGES), (["en-US", "ko-KR"], []))

    def test_host_style_tags_resolve_to_a_supported_one(self):
        self.assertEqual(self.match(["zh-Hans-CN"], VISION_LANGUAGES)[0], ["zh-Hans"])
        self.assertEqual(self.match(["zh-Hant-TW"], VISION_LANGUAGES)[0], ["zh-Hant"])
        self.assertEqual(self.match(["zh-TW"], VISION_LANGUAGES)[0], ["zh-Hant"])
        self.assertEqual(self.match(["zh-CN"], VISION_LANGUAGES)[0], ["zh-Hans"])
        self.assertEqual(self.match(["en-GB"], VISION_LANGUAGES)[0], ["en-US"])
        self.assertEqual(self.match(["en_US"], VISION_LANGUAGES)[0], ["en-US"])
        self.assertEqual(self.match(["ja"], VISION_LANGUAGES)[0], ["ja-JP"])

    def test_an_exact_tag_wins_over_a_language_match(self):
        self.assertEqual(self.match(["nb-NO"], VISION_LANGUAGES)[0], ["nb-NO"])

    def test_unsupported_tags_are_reported_not_passed_on(self):
        self.assertEqual(self.match(["xx-XX", "en-US"], VISION_LANGUAGES), (["en-US"], ["xx-XX"]))
        self.assertEqual(self.match(["hi-IN"], VISION_LANGUAGES), ([], ["hi-IN"]))

    def test_duplicates_collapse(self):
        self.assertEqual(self.match(["en-US", "en-GB", "en"], VISION_LANGUAGES)[0], ["en-US"])


@unittest.skipUnless(sys.platform == "darwin", "Real Vision OCR requires macOS")
class TestRealVisionLanguages(unittest.TestCase):
    """`ocr.languages` reaches Vision: a Korean label reads as Korean."""

    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        self.env = patch.dict("os.environ", {"PHONE_HARNESS_HOME": self.home.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.path = str(Path(self.home.name) / "korean.png")
        self._render("설정  검색  알림", self.path)

    @staticmethod
    def _render(text, path):
        import AppKit
        rep = AppKit.NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
            None, 800, 120, 8, 4, True, False, AppKit.NSDeviceRGBColorSpace, 0, 0)
        AppKit.NSGraphicsContext.saveGraphicsState()
        AppKit.NSGraphicsContext.setCurrentContext_(
            AppKit.NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep))
        AppKit.NSColor.whiteColor().set()
        AppKit.NSRectFill(((0, 0), (800, 120)))
        attrs = {AppKit.NSFontAttributeName: AppKit.NSFont.systemFontOfSize_(48),
                 AppKit.NSForegroundColorAttributeName: AppKit.NSColor.blackColor()}
        AppKit.NSAttributedString.alloc().initWithString_attributes_(text, attrs).drawAtPoint_((20, 30))
        AppKit.NSGraphicsContext.restoreGraphicsState()
        rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, {}).writeToFile_atomically_(path, True)

    def test_configured_language_is_used(self):
        from phone_harness import ocr
        with patch.dict("os.environ", {"PHONE_HARNESS_OCR_LANGUAGES": "ko-KR,en-US"}):
            text = " ".join(b["text"] for b in ocr.recognize(self.path, {"x": 0, "y": 0, "w": 800, "h": 120}))
        for word in ("설정", "검색", "알림"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
