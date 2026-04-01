import streamlit as st
from rembg import remove
from PIL import Image, ImageEnhance, ImageOps
import io

def process_logo(uploaded_file, make_white=True):
    # 1. Load and Pre-process (Boost contrast to help AI see edges)
    img = Image.open(uploaded_file).convert("RGBA")
    
    # Enhance contrast slightly to help background removal
    enhancer = ImageEnhance.Contrast(img)
    temp_img = enhancer.enhance(1.5)
    
    # 2. Remove Background with Alpha Matting (Better Edges)
    no_bg = remove(temp_img, alpha_matting=True)
    
    # 3. Trim empty space
    bbox = no_bg.getbbox()
    if bbox:
        no_bg = no_bg.crop(bbox)
    
    if make_white:
        # 4. Transform to SOLID White
        # We extract the alpha channel and 'harden' it 
        # (Anything more than 10% opaque becomes 100% opaque)
        r, g, b, a = no_bg.split()
        a = a.point(lambda p: 255 if p > 10 else 0)
        
        # Merge into a solid white logo
        white_logo = Image.merge("RGBA", (
            r.point(lambda _: 255), 
            g.point(lambda _: 255), 
            b.point(lambda _: 255), 
            a
        ))
        return white_logo
    
    return no_bg

# --- UI SETUP ---
st.set_page_config(page_title="Logo Lockup Tool", layout="centered")
st.title("🏗️ Pro Logo Lockup Generator")

# Sidebar settings
with st.sidebar:
    st.header("Settings")
    make_white = st.checkbox("Convert logos to Pure White", value=True)
    st.info("The 'White' mode is optimized for dark backgrounds.")

# --- STEP 1: NAMES ---
st.subheader("1. Company Names")
c_col1, c_col2 = st.columns(2)
with c_col1:
    comp1 = st.text_input("Left Company", placeholder="e.g. MongoDB")
with c_col2:
    comp2 = st.text_input("Right Company", placeholder="e.g. Verizon")

# --- STEP 2: UPLOADS ---
st.subheader("2. Upload Logos")
u_col1, u_col2 = st.columns(2)
with u_col1:
    file1 = st.file_uploader("Left Logo", type=["png", "jpg", "jpeg"])
with u_col2:
    file2 = st.file_uploader("Right Logo", type=["png", "jpg", "jpeg"])

# --- STEP 3: PROCESSING ---
if file1 and file2 and comp1 and comp2:
    with st.spinner("Refining edges and generating lockup..."):
        try:
            logo_a = process_logo(file1, make_white)
            logo_b = process_logo(file2, make_white)
            
            # Match Heights
            target_h = min(logo_a.height, logo_b.height)
            
            def scale(img, h):
                return img.resize((int(h * (img.width/img.height)), h), Image.Resampling.LANCZOS)

            l_f = scale(logo_a, target_h)
            r_f = scale(logo_b, target_h)
            
            # Canvas Construction (15px spacing, 2px padding)
            canvas = Image.new("RGBA", (l_f.width + 15 + r_f.width, target_h + 4), (0,0,0,0))
            canvas.paste(l_f, (0, 2), l_f)
            canvas.paste(r_f, (l_f.width + 15, 2), r_f)
            
            st.markdown("### Preview")
            # Show against dark background for visibility
            st.container(border=True).image(canvas)
            
            # Filename formatting
            n1, n2 = comp1.lower().replace(" ","_"), comp2.lower().replace(" ","_")
            fname = f"{n1}_{n2}_logo_lockup.png"
            
            buf = io.BytesIO()
            canvas.save(buf, format="PNG")
            st.download_button(f"Download {fname}", buf.getvalue(), fname, "image/png")
            
        except Exception as e:
            st.error(f"Processing Error: {e}")
