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

def process_logo_pro(uploaded_file) -> Image.Image:
    # 1. Load image and ensure RGBA
    img = Image.open(uploaded_file).convert("RGBA")

    # 2. Estimate background color from corners
    bg_color = estimate_bg_color(img)

    # 3. Difference from background color
    bg_img = Image.new("RGBA", img.size, bg_color)
    diff = ImageChops.difference(img, bg_img)

    # 4. Build luminance mask
    mask = diff.convert("L")
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.0))
    threshold = 16
    mask = mask.point(lambda p: 0 if p < threshold else 255)

    # 5. Combine with any existing alpha
    r, g, b, a = img.split()
    combined_alpha = ImageChops.multiply(a, mask)

    # 6. Create pure white logo with combined alpha
    white_logo = Image.new("RGBA", img.size, (255, 255, 255, 0))
    white_logo.putalpha(combined_alpha)

    # 7. Trim empty space based on alpha
    bbox = combined_alpha.getbbox()
    if bbox:
        white_logo = white_logo.crop(bbox)

    return white_logo

# --- UI SETUP ---
st.set_page_config(page_title="Logo Lockup Tool", layout="centered")
st.title("🏗️ Professional Logo Lockup Generator")
st.write("This version uses **luminance masking + alpha blending** to keep logos solid and sharp.")

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
    file1 = st.file_uploader("Upload Left Logo", type=["png", "jpg", "jpeg"], key="l")
with u2:
    file2 = st.file_uploader("Upload Right Logo", type=["png", "jpg", "jpeg"], key="r")

# --- STEP 3: CONTROLS FOR SIZE & SPACING ---
st.subheader("3. Layout Controls")

col_c1, col_c2 = st.columns(2)
with col_c1:
    right_shrink_px = st.slider(
        "Shrink right logo height (pixels)",
        min_value=0,
        max_value=150,
        value=0,
        step=1,
        help="Use this to make the right logo visually smaller relative to the left, in 1-pixel increments.",
    )
with col_c2:
    spacing_px = st.slider(
        "Horizontal spacing between logos (pixels)",
        min_value=0,
        max_value=200,   # increased range
        value=50,        # new default
        step=1,
        help="Adjust the gap between the left and right logos.",
    )

# --- STEP 4: BACKGROUND SELECTION ---
st.subheader("4. Background")

bg_choice = st.radio(
    "Background color",
    (
        "Black (#061621)",
        "Green (#023430)",
        "Transparent (#00000000)",
    ),
    index=0,
    help="Choose the background. Logos remain pure white; the color fills only where there is no logo.",
)

# Map radio choice to RGBA color AND label for filename/preview
if bg_choice.startswith("Black"):
    canvas_bg = (0x06, 0x16, 0x21, 255)     # #061621, fully opaque
    bg_label = "black"
elif bg_choice.startswith("Green"):
    canvas_bg = (0x02, 0x34, 0x30, 255)     # #023430, fully opaque
    bg_label = "green"
else:
    canvas_bg = (0x00, 0x00, 0x00, 0x00)    # #00000000, fully transparent
    bg_label = "transparent"

# --- STEP 5: PROCESSING ---
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

if file1 and file2:
    try:
        with st.spinner("Processing logos and building lockup…"):
            logo_a = process_logo_pro(file1)
            logo_b = process_logo_pro(file2)

            # Base artwork height from original logos
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

            # Paste white logos using their alpha; background only shows where logos are transparent
            canvas.paste(l_final, (0, 0), l_final)
            canvas.paste(r_final, (l_final.width + spacing_px, 0), r_final)

        # Preview header reflects chosen background
        st.markdown(f"### Final Preview – {bg_label.capitalize()} background")
        st.container(border=True).image(canvas)

        # Filename: include background label
        n1 = comp1.lower().replace(" ", "_")
        n2 = comp2.lower().replace(" ", "_")
        fname = f"{n1}_{n2}_{bg_label}_logo_lockup.png"

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
