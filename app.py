import streamlit as st
from rembg import remove
from PIL import Image
import io

def process_logo(uploaded_file):
    img = Image.open(uploaded_file).convert("RGBA")
    no_bg = remove(img)
    # Trim to artwork edges to ensure 15px spacing is accurate
    bbox = no_bg.getbbox()
    if bbox:
        no_bg = no_bg.crop(bbox)
    # Force all non-transparent pixels to White
    r, g, b, a = no_bg.split()
    white_logo = Image.merge("RGBA", (r.point(lambda _: 255), g.point(lambda _: 255), b.point(lambda _: 255), a))
    return white_logo

st.set_page_config(page_title="Logo Lockup Tool", layout="centered")
st.title("🏗️ Logo Lockup Generator")
st.write("Upload logos, name the companies, and download your white-on-transparent lockup.")

# --- STEP 1: Company Names for File Naming ---
st.subheader("1. Enter Company Names")
col_n1, col_n2 = st.columns(2)
with col_n1:
    comp1 = st.text_input("First Company Name", placeholder="e.g. MongoDB")
with col_n2:
    comp2 = st.text_input("Second Company Name", placeholder="e.g. PwC")

# --- STEP 2: Upload Files ---
st.subheader("2. Upload Logos")
col1, col2 = st.columns(2)
with col1:
    file1 = st.file_uploader("Left Logo File", type=["png", "jpg", "jpeg"])
with col2:
    file2 = st.file_uploader("Right Logo File", type=["png", "jpg", "jpeg"])

if file1 and file2 and comp1 and comp2:
    # Process logos
    l_logo = process_logo(file1)
    r_logo = process_logo(file2)
    
    # Scale to match height (using the shorter logo as the master height)
    h = min(l_logo.height, r_logo.height)
    l_res = l_logo.resize((int(h * (l_logo.width/l_logo.height)), h), Image.Resampling.LANCZOS)
    r_res = r_logo.resize((int(h * (r_logo.width/r_logo.height)), h), Image.Resampling.LANCZOS)
    
    # Create Canvas (15px spacing, 2px padding top/bottom)
    canvas = Image.new("RGBA", (l_res.width + 15 + r_res.width, h + 4), (0,0,0,0))
    canvas.paste(l_res, (0, 2), l_res)
    canvas.paste(r_res, (l_res.width + 15, 2), r_res)
    
    st.markdown("### Preview")
    # Wrap in a container to see white logo against dark UI background
    st.container(border=True).image(canvas)
    
    # Format the filename according to your convention
    # Example: mongodb_pwc_logo_lockup.png
    clean_n1 = comp1.lower().replace(" ", "_")
    clean_n2 = comp2.lower().replace(" ", "_")
    final_filename = f"{clean_n1}_{clean_n2}_logo_lockup.png"
    
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    
    st.download_button(
        label=f"Download {final_filename}", 
        data=buf.getvalue(), 
        file_name=final_filename, 
        mime="image/png"
    )
else:
    if (file1 or file2) and not (comp1 and comp2):
        st.info("Please enter both company names to enable the download.")
