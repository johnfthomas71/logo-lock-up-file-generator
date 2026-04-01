import streamlit as st
from PIL import Image, ImageOps, ImageChops
import io

def process_logo_as_vector(uploaded_file, make_white=True):
    # 1. Load image and ensure it has an Alpha channel
    img = Image.open(uploaded_file).convert("RGBA")
    
    # 2. Create a 'Mask' based on brightness
    # We convert to grayscale to find the 'shape' of the logo
    gray = img.convert("L")
    
    # If the background is white, we want to invert so the logo is 'light' (opaque)
    # and the background is 'dark' (transparent)
    mask = ImageOps.invert(gray)
    
    # 3. Clean up the mask
    # We boost the contrast of the mask to ensure the logo is 100% solid
    # and the background is 100% gone.
    mask = mask.point(lambda p: 255 if p > 50 else 0) # Thresholding
    
    # 4. Create the new image
    if make_white:
        # Create a solid white block
        result = Image.new("RGBA", img.size, (255, 255, 255, 255))
    else:
        # Keep original colors but apply the new clean mask
        result = img.copy()
        
    result.putalpha(mask)
    
    # 5. Trim empty space
    bbox = result.getbbox()
    if bbox:
        result = result.crop(bbox)
        
    return result

# --- UI SETUP ---
st.set_page_config(page_title="Logo Lockup Tool", layout="centered")
st.title("🏗️ Logo Lockup Generator")

st.info("💡 **Tip:** Use this tool for logos on solid white or light backgrounds.")

# --- STEP 1: NAMES ---
st.subheader("1. Company Names")
c_col1, c_col2 = st.columns(2)
with c_col1:
    comp1 = st.text_input("Left Company", value="MongoDB")
with c_col2:
    comp2 = st.text_input("Right Company", value="Verizon")

# --- STEP 2: UPLOADS ---
st.subheader("2. Upload Logos")
u_col1, u_col2 = st.columns(2)
with u_col1:
    file1 = st.file_uploader("Left Logo", type=["png", "jpg", "jpeg"], key="l")
with u_col2:
    file2 = st.file_uploader("Right Logo", type=["png", "jpg", "jpeg"], key="r")

# --- STEP 3: PROCESSING ---
if file1 and file2:
    try:
        # Process logos using the 'Luminance' method instead of AI
        logo_a = process_logo_as_vector(file1)
        logo_b = process_logo_as_vector(file2)
        
        # Match Heights
        target_h = min(logo_a.height, logo_b.height)
        
        def scale(img, h):
            aspect = img.width / img.height
            return img.resize((int(h * aspect), h), Image.Resampling.LANCZOS)

        l_f = scale(logo_a, target_h)
        r_f = scale(logo_b, target_h)
        
        # Canvas (15px spacing, 2px padding)
        canvas_w = l_f.width + 15 + r_f.width
        canvas_h = target_h + 4
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        
        canvas.paste(l_f, (0, 2), l_f)
        canvas.paste(r_f, (l_f.width + 15, 2), r_f)
        
        st.markdown("### Preview")
        st.container(border=True).image(canvas)
        
        # Filename
        n1 = comp1.lower().replace(" ","_")
        n2 = comp2.lower().replace(" ","_")
        fname = f"{n1}_{n2}_logo_lockup.png"
        
        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        st.download_button(f"Download {fname}", buf.getvalue(), fname, "image/png")
        
    except Exception as e:
        st.error(f"Error: {e}")
