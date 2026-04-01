import streamlit as st
from rembg import remove
from PIL import Image
import io

def process_logo(uploaded_file):
    # 1. Load Image
    img = Image.open(uploaded_file).convert("RGBA")
    
    # 2. AI Background Removal 
    # This identifies the "shape" regardless of background color
    no_bg = remove(img)
    
    # 3. Trim to artwork edges
    bbox = no_bg.getbbox()
    if bbox:
        no_bg = no_bg.crop(bbox)
    
    # 4. THE FIX: Solidify and Whiten
    # We extract the 'Alpha' (the transparency mask the AI created)
    r, g, b, alpha = no_bg.split()
    
    # "Binary Threshold": If the AI says a pixel is even 5% logo, 
    # we make it 100% solid logo. This fills the 'hollow' Verizon letters.
    alpha = alpha.point(lambda p: 255 if p > 10 else 0)
    
    # Create a brand new solid white image and apply our solid mask
    white_logo = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
    white_logo.putalpha(alpha)
    
    return white_logo

# --- UI SETUP ---
st.set_page_config(page_title="Logo Lockup Tool", layout="centered")
st.title("🏗️ Pro Logo Lockup Generator")
st.write("Automatically removes backgrounds and creates solid white lockups.")

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
    with st.spinner("Analyzing shapes and solidifying white..."):
        try:
            logo_a = process_logo(file1)
            logo_b = process_logo(file2)
            
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
