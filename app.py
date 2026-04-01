import streamlit as st
from rembg import remove
from PIL import Image, ImageFilter
import io

def process_logo(uploaded_file):
    # 1. Open and remove background
    img = Image.open(uploaded_file).convert("RGBA")
    
    # We use a higher 'alpha_matting' foreground threshold to keep the text solid
    no_bg = remove(img)
    
    # 2. Trim to edges
    bbox = no_bg.getbbox()
    if bbox:
        no_bg = no_bg.crop(bbox)
        
    # 3. Extract the Alpha (the "shape")
    alpha = no_bg.split()[3]
    
    # 4. MORPHOLOGICAL CLOSING: This fills the 'hollow' holes inside letters 
    # caused by gradients, without making the outside edges blurry.
    # We expand the white mask by 2 pixels to bridge the gaps...
    alpha = alpha.filter(ImageFilter.MaxFilter(3))
    # ...then we shrink it back by 2 pixels to restore the original size.
    alpha = alpha.filter(ImageFilter.MinFilter(3))
    
    # 5. Create Pure White Result
    # We create a solid white image and apply our newly "healed" mask
    white_logo = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
    white_logo.putalpha(alpha)
    
    return white_logo

# --- UI ---
st.set_page_config(page_title="Logo Lockup Tool", layout="centered")
st.title("🏗️ Final Pro Logo Lockup")
st.write("Specialized for logos with gradients and shadows.")

# --- NAMES ---
c1_val = st.text_input("Left Company", value="MongoDB")
c2_val = st.text_input("Right Company", value="Verizon")

# --- UPLOADS ---
u1 = st.file_uploader("Left Logo", type=["png", "jpg", "jpeg"], key="l")
u2 = st.file_uploader("Right Logo", type=["png", "jpg", "jpeg"], key="r")

if u1 and u2:
    with st.spinner("Healing logo shapes..."):
        try:
            logo_a = process_logo(u1)
            logo_b = process_logo(u2)
            
            # Align heights
            h = min(logo_a.height, logo_b.height)
            def scale(img, target_h):
                return img.resize((int(target_h * (img.width/img.height)), target_h), Image.Resampling.LANCZOS)
            
            l_f, r_f = scale(logo_a, h), scale(logo_b, h)
            
            # Combine
            canvas = Image.new("RGBA", (l_f.width + 15 + r_f.width, h + 4), (0,0,0,0))
            canvas.paste(l_f, (0, 2), l_f)
            canvas.paste(r_f, (l_f.width + 15, 2), r_f)
            
            st.markdown("### Final Preview")
            st.container(border=True).image(canvas)
            
            fname = f"{c1_val.lower().replace(' ','_')}_{c2_val.lower().replace(' ','_')}_logo_lockup.png"
            buf = io.BytesIO()
            canvas.save(buf, format="PNG")
            st.download_button(f"Download {fname}", buf.getvalue(), fname, "image/png")
            
        except Exception as e:
            st.error(f"Error: {e}")
