import streamlit as st
from PIL import Image, ImageChops, ImageFilter
import io

def estimate_bg_color(img: Image.Image) -> tuple:
    """Estimate background color by sampling the four corners."""
    img = img.convert("RGBA")
    w, h = img.size
    coords = [
        (0, 0),
        (w - 1, 0),
        (0, h - 1),
        (w - 1, h - 1),
    ]
    samples = [img.getpixel(c) for c in coords]
    r = sum(p[0] for p in samples) // len(samples)
    g = sum(p[1] for p in samples) // len(samples)
    b = sum(p[2] for p in samples) // len(samples)
    a = sum(p[3] for p in samples) // len(samples)
    return (r, g, b, a)

def process_logo_pro(uploaded_file, threshold: int):
    """
    Process a logo into a white-on-transparent image and return
    both the processed logo and the binary mask used for extraction.
    """
    # 1. Load image and ensure RGBA
    img = Image.open(uploaded_file).convert("RGBA")

    # 2. Estimate background color from corners
    bg_color = estimate_bg_color(img)

    # 3. Difference from background color
    bg_img = Image.new("RGBA", img.size, bg_color)
    diff = ImageChops.difference(img, bg_img)

    # 4. Build luminance mask
    mask = diff.convert("L")

    # Light blur to smooth edges without flooding the background
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.3))

    # Apply user-controlled threshold
    mask = mask.point(lambda p: 0 if p < threshold else 255)

    # Keep a copy for debugging/preview
    mask_preview = mask.copy()

    # 5. Combine with any existing alpha
    r, g, b, a = img.split()
    combined_alpha = ImageChops.multiply(a, mask)

    # 6. Create pure white logo with combined alpha
    white_logo = Image.new("RGBA", img.size, (255, 255, 255, 0))
    white_logo.putalpha(combined_alpha) 
