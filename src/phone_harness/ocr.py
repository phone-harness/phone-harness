"""Text recognition over window captures via Apple's Vision framework.

This is the mirror backend's element tree: OCR gives every visible string a
bounding box, converted here into global screen points ready for tap().
"""
import functools

import Quartz
import Vision
from Foundation import NSURL, NSLocale

# Vision has no automatic default worth relying on: with no languages set
# it reads English only, so a Korean Home Screen came back as its clock and
# little else ("KB국민은행" read as "KBA028"). Read in the Mac's own
# languages first, then English, which every phone UI mixes in.
_FALLBACK_LANGUAGE = "en-US"


def pick_languages(supported, preferred):
    """Vision language codes for `preferred` (the Mac's language list, most
    wanted first), each mapped to the first `supported` code it fits, then
    English. "ko-KR" fits "ko-KR"; "en-KR" fits "en-US"; "zh-Hans-KR" fits
    "zh-Hans". Chinese and Cantonese match by script, never by language
    alone, so a Traditional reader is not handed Simplified."""
    supported = [s for s in supported if s]
    out = []
    for p in preferred:
        p = (p or "").replace("_", "-")
        base = p.split("-")[0]
        match = None
        for s in supported:
            if p == s or p.startswith(s + "-"):
                match = s
                break
        if match is None and base not in ("zh", "yue"):
            match = next((s for s in supported
                          if s.split("-")[0] == base), None)
        if match and match not in out:
            out.append(match)
    if _FALLBACK_LANGUAGE in supported and _FALLBACK_LANGUAGE not in out:
        out.append(_FALLBACK_LANGUAGE)
    return out


@functools.lru_cache(maxsize=None)
def _languages():
    """The Mac's preferred languages as Vision codes, plus English. None when
    they cannot be read, which leaves Vision on its default."""
    try:
        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        supported, _err = request.supportedRecognitionLanguagesAndReturnError_(None)
        langs = pick_languages(list(supported or []),
                               [str(p) for p in NSLocale.preferredLanguages()])
        return tuple(langs) or None
    except Exception:
        return None


def thumbnail(path, w=24, h=48):
    """The image as a w*h list of 0-255 luminance values, or None. Cheap
    enough to compare two captures for change."""
    src = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(path), None)
    if src is None:
        return None
    img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    if img is None:
        return None
    ctx = Quartz.CGBitmapContextCreate(
        None, w, h, 8, w * 4, Quartz.CGColorSpaceCreateDeviceRGB(),
        Quartz.kCGImageAlphaPremultipliedLast)
    Quartz.CGContextDrawImage(ctx, Quartz.CGRectMake(0, 0, w, h), img)
    data = bytes(Quartz.CGBitmapContextGetData(ctx).as_buffer(w * h * 4))
    return [(data[i] * 299 + data[i + 1] * 587 + data[i + 2] * 114) // 1000
            for i in range(0, len(data), 4)]


def image_size(path):
    src = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(path), None)
    if src is None:
        raise RuntimeError(f"cannot read image {path}")
    props = Quartz.CGImageSourceCopyPropertiesAtIndex(src, 0, None)
    return int(props["PixelWidth"]), int(props["PixelHeight"])


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
    langs = _languages()
    if langs:
        request.setRecognitionLanguages_(list(langs))
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
