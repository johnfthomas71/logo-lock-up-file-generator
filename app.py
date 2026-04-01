import streamlit as st
from rembg import remove
from PIL import Image
import io

# --- LOGIC: THE LOGO TRANSFORMER ---
def process_logo(uploaded_file):
    # 1. Load and Remove Background
    img = Image.open(uploaded_file).convert("RGBA")
    no_bg = remove(img)
    
    # 2. Trim empty space (Crucial for 15px spacing accuracy)
    # This removes any "invisible" padding the original file had
    bbox = no_bg.getbbox()
    if bbox:
        no_bg = no_bg.crop(bbox)
    
    # 3. Force to Pure White
    r, g, b, a = no_bg.split()
    white_logo = Image.merge("RGBA", (
        r.point(lambda _: 255), 
        g.point(lambda _: 255), 
        b.point(lambda _: 255), 
        a
    ))
    return white_logo

# --- UI SETUP ---
st.set_page_config(page_title="Logo Lockup Tool", layout="centered")
st.title("🏗️ Logo Lockup Generator")
st.write("Upload two logos to create a white-on-transparent lockup.")

# --- STEP 1: NAMES ---
st.subheader("1. Company Names")
c_col1, c_col2 = st.columns(2)
with c_col1:
    comp1 = st.text_input("Left Company Name", placeholder="e.g. MongoDB")
with c_col2:
    comp2 = st.text_input("Right Company Name", placeholder="e.g. PwC")

# --- STEP 2: UPLOADS ---
st.subheader("2. Upload Logos")
u_col1, u_col2 = st.columns(2)
with u_col1:
    file1 = st.file_uploader("Upload Left Logo", type=["png", "jpg", "jpeg"])
with u_col2:
    file2 = st.file_uploader("Upload Right Logo", type=["png", "jpg", "jpeg"])

# --- STEP 3: PROCESSING ---
if file1 and file2 and comp1 and comp2:
    with st.spinner("Processing... (The first time takes ~30s to load the AI model)"):
        try:
            # Transform logos
            logo_a = process_logo(file1)
            logo_b = process_logo(file2)
            
            # Scale logic: Match height of the shorter logo
            target_h = min(logo_a.height, logo_b.height)
            
            def scale_it(img, h):
                aspect = img.width / img.height
                return img.resize((int(h * aspect), h), Image.Resampling.LANCZOS)

            l_final = scale_it(logo_a, target_h)
            r_final = scale_it(logo_b, target_h)
            
            # Canvas: 15px spacing, 2px padding top/bottom
            spacing = 15
            padding = 2
            canvas_w = l_final.width + spacing + r_final.width
            canvas_h = target_h + (padding * 2)
            
            canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            
            # Paste (Aligned middle horizontally)
            canvas.paste(l_final, (0, padding), l_final)
            canvas.paste(r_final, (l_final.width + spacing, padding), r_final)
            
            # --- RESULTS ---
            st.markdown("### Preview (Against Dark Background)")
            # Bordered container so the white logos are visible to the user
            st.container(border=True).image(canvas)
            
            # Filename formatting: mongodb_pwc_logo_lockup.png
            n1 = comp1.lower().replace(" ", "_")
            n2 = comp2.lower().replace(" ", "_")
            fname = f"{n1}_{n2}_logo_lockup.png"
            
            buf = io.BytesIO()
            canvas.save(buf, format="PNG")
            
            st.download_button(
                label=f"Download {fname}",
                data=buf.getvalue(),
                file_name=fname,
                mime="image/png"
            )
            
        except Exception as e:
            st.error(f"Error: {e}")
else:
    if (file1 or file2) and not (comp1 and comp2):
        st.info("ℹ️ Please enter both company names to enable the generator.")
