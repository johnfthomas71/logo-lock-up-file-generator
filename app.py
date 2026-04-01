import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io

def process_logo(uploaded_file):
    # 1. Load and Remove Background
    img = Image.open(uploaded_file).convert("RGBA")
    no_bg = remove(img)
    
    # 2. Trim empty space (Crucial for 15px spacing/2px padding accuracy)
    # This crops the image to the actual pixels of the logo
    bbox = no_bg.getbbox()
    if bbox:
        no_bg = no_bg.crop(bbox)
    
    # 3. Convert to Pure White
    r, g, b, a = no_bg.split()
    white_logo = Image.merge("RGBA", (
        r.point(lambda _: 255), 
        g.point(lambda _: 255), 
        b.point(lambda _: 255), 
        a
    ))
    return white_logo

st.title("Pro Logo Lockup Tool")
st.write("Upload two logos to create a perfectly aligned, white-on-transparent composite.")

file1 = st.file_uploader("Upload Left Logo", type=["png", "jpg", "jpeg"])
file2 = st.file_uploader("Upload Right Logo", type=["png", "jpg", "jpeg"])

if file1 and file2:
    # Process both logos
    logo_a = process_logo(file1)
    logo_b = process_logo(file2)
    
    # --- LOGIC: AS CLOSE TO SAME HEIGHT AS POSSIBLE ---
    # We find the smaller height of the two and scale the larger one down 
    # to match it, ensuring no quality loss from upscaling.
    target_height = min(logo_a.height, logo_b.height)
    
    def resize_to_height(img, height):
        aspect_ratio = img.width / img.height
        new_width = int(height * aspect_ratio)
        return img.resize((new_width, height), Image.Resampling.LANCZOS)

    logo_a_resized = resize_to_height(logo_a, target_height)
    logo_b_resized = resize_to_height(logo_b, target_height)
    
    # --- LOGIC: SPACING AND PADDING ---
    spacing = 15
    padding_y = 2  # 2px top, 2px bottom
    
    total_width = logo_a_resized.width + spacing + logo_b_resized.width
    total_height = target_height + (padding_y * 2)
    
    # Create the final transparent canvas
    canvas = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
    
    # --- LOGIC: ALIGNMENT ---
    # Since they are the same height now, the 'y' coordinate is simply the top padding
    # This effectively aligns them by their horizontal middle.
    canvas.paste(logo_a_resized, (0, padding_y), logo_a_resized)
    canvas.paste(logo_b_resized, (logo_a_resized.width + spacing, padding_y), logo_b_resized)
    
    # Display over a dark background in Streamlit so the white is visible
    st.markdown("### Preview (Against Dark Background)")
    st.container(border=True).image(canvas, use_container_width=False)
    
    # Download Button
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    st.download_button(
        label="Download Combined PNG",
        data=buf.getvalue(),
        file_name="corporate_lockup_white.png",
        mime="image/png"
    )