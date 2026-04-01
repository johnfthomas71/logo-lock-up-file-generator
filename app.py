import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io

def process_logo(uploaded_file, make_white=True):
    # 1. Load original image
    img = Image.open(uploaded_file).convert("RGBA")
    
    # 2. Standard Background Removal (Default settings are usually most stable)
    # We remove the 'alpha_matting' which was causing the jagged 'bites'
    no_bg = remove(img)
    
    # 3. Trim empty space
    bbox = no_bg.getbbox()
    if bbox:
        no_bg = no_bg.crop(bbox)
    
    if make_white:
        # 4. Professional White Overlay
        # Create a solid white image the exact size of our logo
        white_layer = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
        
        # Use the AI-generated alpha channel as a MASK
        # This keeps the edges smooth (anti-aliased) while making the logo 100% white
        mask = no_bg.split()[3] 
        white_layer.putalpha(mask)
        
        return white_layer
    
    return no_bg

# --- UI SETUP ---
st.set_page_config(page_title="Logo Lockup Tool", layout="centered")
st.title("🏗️ Logo Lockup Generator")

with st.sidebar:
    st.header("Settings")
    make_white = st.checkbox("Convert to White", value=True)
    st.write("Turn this off if the logos look 'hollow' or jagged.")

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
    with st.spinner("Creating smooth lockup..."):
        try:
            logo_a = process_logo(file1, make_white)
            logo_b = process_logo(file2, make_white)
            
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
