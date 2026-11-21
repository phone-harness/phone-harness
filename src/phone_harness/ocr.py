"""Text recognition over window captures via Apple's Vision framework.

This is the mirror backend's element tree: OCR gives every visible string a
bounding box, converted here into global screen points ready for tap().
"""
import sys

import Quartz
import Vision
from Foundation import NSLocale, NSURL

from . import config

_warned = set()


def image_size(path):
    src = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(path), None)
    if src is None:
        raise RuntimeError(f"cannot read image {path}")
    props = Quartz.CGImageSourceCopyPropertiesAtIndex(src, 0, None)
    return int(props["PixelWidth"]), int(props["PixelHeight"])


def _subtags(tag):
    """'zh-Hans-CN' -> ('zh', 'Hans'); 'en_US' -> ('en', None)."""
    parts = tag.replace("_", "-").split("-")
    script = next((p for p in parts[1:] if len(p) == 4 and p.isalpha()), None)
    if script is None and parts[0].lower() == "zh" and any(p.upper() in ("TW", "HK", "MO") for p in parts[1:]):
        script = "Hant"   # zh-TW names its script only by region
    return parts[0].lower(), script.title() if script else None


def match_languages(wanted, supported):
    """Map each wanted tag onto one Vision supports, keeping order.

    Vision accepts an identifier it does not know without an error and then
    reads English only, so every tag is resolved against `supported` here:
    exact first, then the same language (and script, when the tag names one),
    e.g. 'zh-Hans-CN' -> 'zh-Hans', 'en-GB' -> 'en-US'. Returns (matched,
    unmatched)."""
    matched, unmatched = [], []
    for tag in wanted:
        lang, script = _subtags(tag)
        hit = next((s for s in supported if s.replace("_", "-").lower() == tag.replace("_", "-").lower()), None)
        if hit is None:
            hit = next((s for s in supported
                        if _subtags(s)[0] == lang and (script is None or _subtags(s)[1] in (script, None))), None)
        if hit is None:
            unmatched.append(tag)
        elif hit not in matched:
            matched.append(hit)
    return matched, unmatched


def recognition_languages(request):
    """The languages to read with: `ocr.languages` when set, else the Mac's
    preferred languages plus English. The phone's language can differ from
    the Mac's, so a phone in another language needs `ocr.languages` set to it."""
    configured, source = config.lookup("ocr.languages")
    wanted = [t for t in str(configured or "").replace(",", " ").split() if t]
    if not wanted:
        source = None
        wanted = [str(t) for t in NSLocale.preferredLanguages() or []] + ["en-US"]
    supported, _ = request.supportedRecognitionLanguagesAndReturnError_(None)
    matched, unmatched = match_languages(wanted, [str(s) for s in supported or []])
    if source and unmatched and tuple(unmatched) not in _warned:
        _warned.add(tuple(unmatched))
        print(f"phone-harness: Vision OCR cannot read {', '.join(unmatched)} ({source}); "
              f"supported: {', '.join(str(s) for s in supported or [])}", file=sys.stderr)
    return matched


def recognize(path, window):
    """OCR a capture of `window` ({x, y, w, h} screen points).

    Returns [{text, confidence, x, y, w, h}] where (x, y) is the box center in
    screen points — pass straight to tap(). Vision's normalized boxes have a
    bottom-left origin; screen points have a top-left origin, hence the flip.
    """
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(
        NSURL.fileURLWithPath_(path), None)
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    languages = recognition_languages(request)
    if languages:
        request.setRecognitionLanguages_(languages)
    ok, err = handler.performRequests_error_([request], None)
    if not ok:
        raise RuntimeError(f"Vision OCR failed: {err}")

    img_w, img_h = image_size(path)
    sx = window["w"] / img_w  # image px -> screen points
    sy = window["h"] / img_h

    out = []
    for obs in request.results() or []:
        cand = obs.topCandidates_(1)
        if not cand:
            continue
        bb = obs.boundingBox()
        px = bb.origin.x * img_w
        py_top = (1.0 - bb.origin.y - bb.size.height) * img_h
        pw = bb.size.width * img_w
        ph = bb.size.height * img_h
        out.append({
            "text": str(cand[0].string()),
            "confidence": round(float(cand[0].confidence()), 3),
            "x": round(window["x"] + (px + pw / 2) * sx, 1),
            "y": round(window["y"] + (py_top + ph / 2) * sy, 1),
            "w": round(pw * sx, 1),
            "h": round(ph * sy, 1),
        })
    return out
