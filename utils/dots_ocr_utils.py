"""Utilities for OCR pre-processing and PDF rendering.

This module provides helpers used by Dots OCR flows:

- Render a single `fitz.Page` (PyMuPDF) to a `PIL.Image` at a target DPI,
  with an automatic fallback to PyMuPDF's default DPI for very large pages.
- Load all or a range of pages from a PDF file into `PIL.Image` objects.
- Resize images to satisfy model-friendly constraints via `smart_resize`:
  dimensions divisible by a factor (default 28), total pixels within a
  configurable range, while keeping the aspect ratio close to the original.
- Small math helpers to round/ceil/floor by a factor.
- Convert a `PIL.Image` to a `data:image/...;base64,` string for transport.

Key constants:
- MIN_PIXELS, MAX_PIXELS: Inclusive bounds for total pixels when resizing.
- IMAGE_FACTOR: Divisibility factor commonly required by vision models.

Dependencies: PyMuPDF (`fitz`) and Pillow (`PIL`).

Example:
    from utils.dots_ocr_utils import load_images_from_pdf, smart_resize

    images = load_images_from_pdf("document.pdf", dpi=200)
    for img in images:
        h, w = img.height, img.width
        new_h, new_w = smart_resize(h, w)
        resized = img.resize((new_w, new_h))
"""

import base64
import math
from io import BytesIO

import fitz  # type: ignore
from PIL import Image

MIN_PIXELS = 3136
MAX_PIXELS = 11289600
IMAGE_FACTOR = 28


def fitz_doc_to_image(doc, target_dpi=200, origin_dpi=None) -> Image.Image:
    """Render a `fitz.Page` to a `PIL.Image`.

    Args:
        doc: A PyMuPDF page (e.g., `fitz.Page`).
        target_dpi: Desired render DPI. Defaults to 200.
        origin_dpi: Unused. Kept for backward compatibility.

    Returns:
        PIL.Image: The rendered page as an RGB image.
    """
    mat = fitz.Matrix(target_dpi / 72, target_dpi / 72)
    pm = doc.get_pixmap(matrix=mat, alpha=False)

    if pm.width > 4500 or pm.height > 4500:
        mat = fitz.Matrix(72 / 72, 72 / 72)  # use fitz default dpi
        pm = doc.get_pixmap(matrix=mat, alpha=False)

    image = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
    return image


def load_images_from_pdf(
    pdf_file: str, dpi=200, start_page_id=0, end_page_id=None
) -> list:
    """Load pages from a PDF file and render them to images.

    Args:
        pdf_file: Path to the PDF file on disk.
        dpi: Target render DPI for each page. Defaults to 200.
        start_page_id: First page index (0-based) to include. Defaults to 0.
        end_page_id: Last page index (0-based) to include (inclusive). If None,
            defaults to the final page in the document.

    Returns:
        list[PIL.Image]: A list of rendered RGB images in document order.
    """
    images = []
    with fitz.open(pdf_file) as doc:
        pdf_page_num = doc.page_count
        end_page_id = (
            end_page_id
            if end_page_id is not None and end_page_id >= 0
            else pdf_page_num - 1
        )
        if end_page_id > pdf_page_num - 1:
            print("end_page_id is out of range, use images length")
            end_page_id = pdf_page_num - 1

        for index in range(0, doc.page_count):
            if start_page_id <= index <= end_page_id:
                page = doc[index]
                img = fitz_doc_to_image(page, target_dpi=dpi)
                images.append(img)
    return images


def round_by_factor(number: float, factor: int) -> int:
    """Returns the closest integer to 'number' that is divisible by 'factor'."""
    return round(number / factor) * factor


def ceil_by_factor(number: float, factor: int) -> int:
    """Returns the smallest integer greater than or equal to 'number' that is divisible by 'factor'."""
    return math.ceil(number / factor) * factor


def floor_by_factor(number: float, factor: int) -> int:
    """Returns the largest integer less than or equal to 'number' that is divisible by 'factor'."""
    return math.floor(number / factor) * factor


def smart_resize(
    height: int,
    width: int,
    factor: int = 28,
    min_pixels: int = 3136,
    max_pixels: int = 11289600,
):
    """Rescales the image so that the following conditions are met:

    1. Both dimensions (height and width) are divisible by 'factor'.

    2. The total number of pixels is within the range ['min_pixels', 'max_pixels'].

    3. The aspect ratio of the image is maintained as closely as possible.

    """
    if max(height, width) / min(height, width) > 200:
        raise ValueError(
            f"absolute aspect ratio must be smaller than 200, got {max(height, width) / min(height, width)}"
        )
    h_bar = max(factor, round_by_factor(height, factor))
    w_bar = max(factor, round_by_factor(width, factor))
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = max(factor, floor_by_factor(height / beta, factor))
        w_bar = max(factor, floor_by_factor(width / beta, factor))
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = ceil_by_factor(height * beta, factor)
        w_bar = ceil_by_factor(width * beta, factor)
        if h_bar * w_bar > max_pixels:  # max_pixels first to control the token length
            beta = math.sqrt((h_bar * w_bar) / max_pixels)
            h_bar = max(factor, floor_by_factor(h_bar / beta, factor))
            w_bar = max(factor, floor_by_factor(w_bar / beta, factor))
    return h_bar, w_bar


def pil_image_to_base64(image: Image.Image, format="PNG"):
    """Encode a PIL image as a data URL with Base64 content.

    Args:
        image: Input `PIL.Image` to encode.
        format: Image format for encoding (e.g., "PNG", "JPEG"). Defaults to
            "PNG".

    Returns:
        str: A `data:image/<format>;base64,<...>` string.
    """
    buffered = BytesIO()
    image.save(buffered, format=format)
    base64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/{format.lower()};base64,{base64_str}"
