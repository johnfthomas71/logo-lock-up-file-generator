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
    comp2 = st.text_input("Right Company", value="Verizon")

# --- STEP 2: UPLOADS ---
st.subheader("2. Upload Logos")
u1, u2 = st.columns(2)
with u1:
    file1 = st.file_uploader("Upload Left Logo", type=["png", "jpg", "jpeg"], key="l")
with u2:
    file2 = st.file_uploader("Upload Right Logo", type=["png", "jpg", "jpeg"], key="r")

# --- STEP 3: PROCESSING ---
if file1 and file2:
    try:
        with st.spinner("Processing logos and building lockup…"):
            logo_a = process_logo_pro(file1)
            logo_b = process_logo_pro(file2)

            # Match heights
            target_h = min(logo_a.height, logo_b.height)

            def scale(img: Image.Image, h: int) -> Image.Image:
                aspect = img.width / img.height
                return img.resize((int(h * aspect), h), Image.Resampling.LANCZOS)

            l_f = scale(logo_a, target_h)
            r_f = scale(logo_b, target_h)

            # Canvas (15px spacing, 2px vertical padding)
            canvas_w = l_f.width + 15 + r_f.width
            canvas_h = target_h + 4
            canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

            canvas.paste(l_f, (0, 2), l_f)
            canvas.paste(r_f, (l_f.width + 15, 2), r_f)

        st.markdown("### Final Preview")
        st.container(border=True).image(canvas)

        # Filename
        n1 = comp1.lower().replace(" ", "_")
        n2 = comp2.lower().replace(" ", "_")
        fname = f"{n1}_{n2}_logo_lockup.png"

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
