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

def process_logo_pro(uploaded_file, threshold: int, mode: str = "white"):
    """
    Process a logo into either:
      - white-on-transparent ("white" mode), or
      - original colors on transparent ("color" mode),

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

    # Light blur to smooth edges without flooding the background
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.3))

    # Apply user-controlled threshold
    mask = mask.point(lambda p: 0 if p < threshold else 255)

    # Keep a copy for debugging/preview
    mask_preview = mask.copy()

    # 5. Combine with any existing alpha
    r, g, b, a = img.split()
    combined_alpha = ImageChops.multiply(a, mask)

    # 6. Build final logo depending on mode
    if mode == "color":
        # Preserve original RGB, only tighten alpha
        logo = img.copy()
        logo.putalpha(combined_alpha)
    else:
        # Default: pure white logo
        logo = Image.new("RGBA", img.size, (255, 255, 255, 0))
        logo.putalpha(combined_alpha)

    # 7. Trim empty space based on alpha
    bbox = combined_alpha.getbbox()
    if bbox:
        logo = logo.crop(bbox)
        mask_preview = mask_preview.crop(bbox)

    return logo, mask_preview

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
    comp2 = st.text_input("Right Company", value="Company Name")

# --- STEP 2: UPLOADS ---
st.subheader("2. Upload Logos")
u1, u2 = st.columns(2)
with u1:
    file1 = st.file_uploader(
        "Upload Left Logo", type=["png", "jpg", "jpeg"], key="l"
    )
with u2:
    file2 = st.file_uploader(
        "Upload Right Logo", type=["png", "jpg", "jpeg"], key="r"
    )

    # --- STEP 6 (moved): RIGHT LOGO COLOR MODE, directly under Upload Right Logo ---
    st.subheader("6. Right Logo Color Mode")
    right_color_mode = st.radio(
        "Right logo color treatment",
        ("Convert to white", "Maintain original image colors"),
        index=0,
        help=(
            "Use 'Maintain original image colors' for brands that must stay in color "
            "(for example, the Microsoft logo)."
        ),
    )

# --- STEP 4: BACKGROUND SELECTION (stays where it is) ---
st.subheader("4. Background")

bg_choice = st.radio(
    "Background color",
    (
        "Black (#061621)",
        "Green (#023430)",
        "Transparent (#00000000)",
    ),
    index=0,
    help=(
        "Choose the background. Logos remain pure white or in original color; "
        "the background fills only where there is no logo."
    ),
)

# Map radio choice to RGBA color AND label for filename/preview
if bg_choice.startswith("Black"):
    canvas_bg = (0x06, 0x16, 0x21, 255)  # #061621, fully opaque
    bg_label = "black"
elif bg_choice.startswith("Green"):
    canvas_bg = (0x02, 0x34, 0x30, 255)  # #023430, fully opaque
    bg_label = "green"
else:
    canvas_bg = (0x00, 0x00, 0x00, 0x00)  # #00000000, fully transparent
    bg_label = "transparent"

# --- STEP 5: FOREGROUND SENSITIVITY (stays where it is) ---
st.subheader("5. Extraction Sensitivity")
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

# Optional: mask debug view toggle
show_masks = st.checkbox(
    "Show extraction masks (debug view)",
    value=False,
    help=(
        "When enabled, shows the binary masks used to cut the logos out of their "
        "original backgrounds."
    ),
)

# --- PROCESSING HELPERS ---
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
    pad_bottom = pad_total - pad_top
    new_img = Image.new("RGBA", (w, target_height), pad_color)
    new_img.paste(img, (0, pad_top), img)
    return new_img

# --- STEP 3 (moved): LAYOUT CONTROLS, now just above Final Preview ---
st.subheader("3. Layout Controls")

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
            # Left logo: always converted to white
            logo_a, mask_a = process_logo_pro(file1, fg_threshold, mode="white")

            # Right logo: mode based on user selection
            right_mode = "white" if right_color_mode.startswith("Convert") else "color"
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

        # Preview header reflects chosen background
        st.markdown(f"### Final Preview – {bg_label.capitalize()} background")
        st.container(border=True).image(canvas)

        # Optional: show mask debug view
        if show_masks:
            st.subheader("Mask Debug View")
            m1, m2 = st.columns(2)
            with m1:
                st.image(mask_a, caption="Left logo mask", use_column_width=True)
            with m2:
                st.image(mask_b, caption="Right logo mask", use_column_width=True)

        # Filename: include background and right-logo mode
        n1 = comp1.lower().replace(" ", "_")
        n2 = comp2.lower().replace(" ", "_")
        mode_suffix = "color" if right_mode == "color" else "white"
        fname = f"{n1}_{n2}_{mode_suffix}_{bg_label}_logo_lockup.png"

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
