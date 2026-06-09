import io

import streamlit as st
from PIL import Image, ImageChops, ImageFilter


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


def process_logo_pro(uploaded_file, threshold: int, mode: str = "white"):
    """
    Process a logo into either:
      - white-on-transparent ("white" mode), or
      - original colors on opaque background trimmed to artwork ("color" mode),
    and return both the processed logo and the binary mask used for extraction.
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
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.3))
    mask = mask.point(lambda p: 0 if p < threshold else 255)

    # Keep a copy for debugging/preview
    mask_preview = mask.copy()

    # 5. Combine with any existing alpha to get a trim mask
    _, _, _, a = img.split()
    combined_alpha = ImageChops.multiply(a, mask)

    # 6. Find bounding box of non-transparent content
    bbox = combined_alpha.getbbox()

    if mode == "color":
        # COLOR MODE: use bbox only to trim; keep original colors, no holes
        if bbox:
            cropped = img.crop(bbox)
            logo = cropped.convert("RGBA")

            # Make entire cropped logo fully opaque
            full_alpha = Image.new("L", logo.size, 255)
            logo.putalpha(full_alpha)
            mask_preview = mask_preview.crop(bbox)
        else:
            logo = img
        return logo, mask_preview

    # 7. WHITE MODE: existing behavior, applied after bbox
    white_logo = Image.new("RGBA", img.size, (255, 255, 255, 0))
    white_logo.putalpha(combined_alpha)

    if bbox:
        white_logo = white_logo.crop(bbox)
        mask_preview = mask_preview.crop(bbox)

    return white_logo, mask_preview


def scale_to_height(img: Image.Image, h: int) -> Image.Image:
    aspect = img.width / img.height
    return img.resize((int(h * aspect), h), Image.Resampling.LANCZOS)


def pad_image(img: Image.Image, target_height: int, pad_color=(0, 0, 0, 0)) -> Image.Image:
    """Pad image vertically to target height, centering the content."""
    w, h = img.size
    if h >= target_height:
        return img

    pad_total = target_height - h
    pad_top = pad_total // 2
    new_img = Image.new("RGBA", (w, target_height), pad_color)
    new_img.paste(img, (0, pad_top), img)
    return new_img


# --- UI SETUP ---
st.set_page_config(page_title="Logo Lockup Tool", layout="centered")
st.title("🏗️ Professional Logo Lockup Generator")
st.write(
    "This version uses **luminance masking + alpha blending** to keep logos solid and sharp."
)

# --- STEP 1: NAMES ---
st.subheader("1. Company Names")
col_n1, col_n2 = st.columns(2)
with col_n1:
    comp1 = st.text_input("Left Company", value="MongoDB")
with col_n2:
    comp2 = st.text_input("Right Company", value="", placeholder="Company Name")

# --- STEP 2: UPLOADS ---
st.subheader("2. Upload Logos")
u1, u2 = st.columns(2)
with u1:
    file1 = st.file_uploader("Upload Left Logo", type=["png", "jpg", "jpeg"], key="l")
    st.subheader("3. Left Logo Color Mode")
    left_color_mode = st.radio(
        "Left logo color treatment",
        ("Convert to white", "Maintain original image colors"),
        index=0,
        help=(
            "Use 'Maintain original image colors' for brands that must stay in color."
        ),
        key="left_color_mode",
    )

with u2:
    file2 = st.file_uploader("Upload Right Logo", type=["png", "jpg", "jpeg"], key="r")
    st.subheader("4. Right Logo Color Mode")
    right_color_mode = st.radio(
        "Right logo color treatment",
        ("Convert to white", "Maintain original image colors"),
        index=0,
        help=(
            "Use 'Maintain original image colors' for brands that must stay in color "
            "(for example, the Microsoft logo)."
        ),
        key="right_color_mode",
    )

# --- STEP 5: BACKGROUND SELECTION ---
st.subheader("5. Background")
bg_choice = st.radio(
    "Background color",
    (
        "Transparent (#00000000)",
        "Black (#061621)",
        "Green (#023430)",
    ),
    index=0,
    help=(
        "Choose the background. Logos remain pure white or in original color; "
        "the background fills only where there is no logo."
    ),
)

# Map radio choice to RGBA color AND label for filename/preview
if bg_choice.startswith("Transparent"):
    canvas_bg = (0x00, 0x00, 0x00, 0x00)
    bg_label = "transparent"
elif bg_choice.startswith("Black"):
    canvas_bg = (0x06, 0x16, 0x21, 255)
    bg_label = "black"
else:
    canvas_bg = (0x02, 0x34, 0x30, 255)
    bg_label = "green"

# --- STEP 6: FOREGROUND SENSITIVITY ---
st.subheader("6. Extraction Sensitivity")
st.markdown(
    "Higher values keep fewer pixels (helps remove big white blocks); "
    "lower values keep more (helps preserve faint edges)."
)
fg_threshold = st.slider(
    "Foreground sensitivity (threshold)",
    min_value=10,
    max_value=80,
    value=40,
    step=1,
    help=(
        "Controls how different a pixel must be from the original background to be kept. "
        "Increase this if you see a big white box; decrease if fine logo details disappear."
    ),
)

show_masks = st.checkbox(
    "Show extraction masks (debug view)",
    value=False,
    help=(
        "When enabled, shows the binary masks used to cut the logos out of their "
        "original backgrounds."
    ),
)

# --- STEP 7: LAYOUT CONTROLS ---
st.subheader("7. Layout Controls")
col_c1, col_c2 = st.columns(2)
with col_c1:
    right_shrink_px = st.slider(
        "Shrink right logo height (pixels)",
        min_value=0,
        max_value=150,
        value=0,
        step=1,
        help=(
            "Use this to make the right logo visually smaller relative to the left, "
            "in 1-pixel increments."
        ),
    )
with col_c2:
    spacing_px = st.slider(
        "Horizontal spacing between logos (pixels)",
        min_value=0,
        max_value=200,
        value=50,
        step=1,
        help="Adjust the gap between the left and right logos.",
    )

# --- MAIN PIPELINE + FINAL PREVIEW ---
if file1 and file2:
    try:
        with st.spinner("Processing logos and building lockup…"):
            left_mode = (
                "white" if left_color_mode.startswith("Convert") else "color"
            )
            right_mode = (
                "white" if right_color_mode.startswith("Convert") else "color"
            )

            logo_a, mask_a = process_logo_pro(file1, fg_threshold, mode=left_mode)
            logo_b, mask_b = process_logo_pro(file2, fg_threshold, mode=right_mode)

            # Base artwork height from processed logos
            base_artwork_h = max(logo_a.height, logo_b.height)

            # Left logo stays at full base height
            l_scaled = scale_to_height(logo_a, base_artwork_h)

            # Right logo can be shrunk by N pixels (but never below 1px)
            r_target_h = max(1, base_artwork_h - right_shrink_px)
            r_scaled = scale_to_height(logo_b, r_target_h)

            # Final canvas height = max of scaled heights + padding
            PAD_PIXELS = 6
            final_height = max(l_scaled.height, r_scaled.height) + 2 * PAD_PIXELS
            l_final = pad_image(l_scaled, final_height)
            r_final = pad_image(r_scaled, final_height)

            # Canvas with chosen background color and adjustable horizontal spacing
            canvas_w = l_final.width + spacing_px + r_final.width
            canvas_h = final_height
            canvas = Image.new("RGBA", (canvas_w, canvas_h), canvas_bg)

            # Paste logos using their alpha; background only shows where logos are transparent
            canvas.paste(l_final, (0, 0), l_final)
            canvas.paste(r_final, (l_final.width + spacing_px, 0), r_final)

        st.markdown(f"### Final Preview – {bg_label.capitalize()} background")
        st.container(border=True).image(canvas)

        if show_masks:
            st.subheader("Mask Debug View")
            m1, m2 = st.columns(2)
            with m1:
                st.image(mask_a, caption="Left logo mask", use_column_width=True)
            with m2:
                st.image(mask_b, caption="Right logo mask", use_column_width=True)

        n1 = comp1.lower().replace(" ", "_")
        n2 = comp2.lower().replace(" ", "_")
        left_mode_suffix = "color" if left_mode == "color" else "white"
        right_mode_suffix = "color" if right_mode == "color" else "white"
        fname = (
            f"{n1}_{n2}_{left_mode_suffix}_{right_mode_suffix}_{bg_label}_logo_lockup.png"
        )

        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        buf.seek(0)

        st.download_button(
            label=f"Download {fname}",
            data=buf.getvalue(),
            file_name=fname,
            mime="image/png",
        )
    except Exception as e:
        st.error(f"Error: {e}")
