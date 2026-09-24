import os
import qrcode

# ==============================================================================
# CONFIGURATION - Update these to match your GitHub setup
# ==============================================================================
GITHUB_USERNAME = "your-username"  # Replace with your actual GitHub username
REPO_NAME = "ar-aircraft-library"   # Replace with your repository name

BASE_URL = f"https://postj-gtps.github.io/ar-vehicle-library/pages"
PAGES_DIR = "./pages"
QR_DIR = "./qr_codes"

# Create the output folder for QR images if it doesn't exist
os.makedirs(QR_DIR, exist_ok=True)

# Generate a QR code for every .html page found in /pages/
html_files = [f for f in os.listdir(PAGES_DIR) if f.endswith(".html")]

if not html_files:
    print(f"[WARNING] No .html files found in '{PAGES_DIR}'. Make sure your pages are generated first!")
else:
    for html_file in html_files:
        page_name = os.path.splitext(html_file)[0]
        target_url = f"{BASE_URL}/{html_file}"
        
        # Build high-resolution QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,  # High-res output suitable for printing
            border=2,
        )
        qr.add_data(target_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        output_filename = os.path.join(QR_DIR, f"{page_name}_QR.png")
        img.save(output_filename)
        print(f"Generated QR: {output_filename} --> {target_url}")

    print(f"\nSUCCESS! Generated {len(html_files)} QR code PNG files in '{QR_DIR}'.")