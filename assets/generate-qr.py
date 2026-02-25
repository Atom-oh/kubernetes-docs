#!/usr/bin/env python3
"""Generate EKS-branded QR code with official AWS EKS logo in center.

Downloads the AWS EKS Architecture Icon and embeds it in the center of a
QR code. Uses HIGH error correction to allow ~30% center obstruction.
"""

import qrcode
from PIL import Image, ImageDraw
from pathlib import Path
from urllib.request import urlretrieve

# Configuration
URL = "https://atomoh.gitbook.io/kubernetes-docs/amazon-eks/eks-hybrid-nodes"
OUTPUT = "assets/eks-hybrid-nodes-qr.png"
SIZE = 800
LOGO_RATIO = 0.23  # logo covers ~23% of QR width (within 30% safe zone)

# AWS brand colors
AWS_DARK_NAVY = "#232F3E"
WHITE = "#FFFFFF"

# AWS EKS Architecture Icon
EKS_ICON_URL = "https://icon.icepanel.io/AWS/png-512/Containers/Elastic-Kubernetes-Service.png"
EKS_ICON_CACHE = "/tmp/eks-icon.png"

# 1. Download EKS icon if not cached
icon_path = Path(EKS_ICON_CACHE)
if not icon_path.exists():
    print("Downloading AWS EKS icon...")
    urlretrieve(EKS_ICON_URL, EKS_ICON_CACHE)

# 2. Generate QR code with HIGH error correction
qr = qrcode.QRCode(
    version=None,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4,
)
qr.add_data(URL)
qr.make(fit=True)

qr_img = qr.make_image(fill_color=AWS_DARK_NAVY, back_color=WHITE).convert("RGBA")
qr_img = qr_img.resize((SIZE, SIZE), Image.LANCZOS)

# 3. Prepare logo with circular white background
logo_size = int(SIZE * LOGO_RATIO)
logo = Image.open(EKS_ICON_CACHE).convert("RGBA")
logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

# Create rounded-rect white background behind the logo
pad = 14
disc_size = logo_size + pad * 2
disc = Image.new("RGBA", (disc_size, disc_size), (0, 0, 0, 0))
disc_draw = ImageDraw.Draw(disc)
disc_draw.rounded_rectangle([0, 0, disc_size - 1, disc_size - 1], radius=20, fill=WHITE)

# Paste logo centered on the white disc
disc.paste(logo, (pad, pad), logo)

# 4. Composite logo onto QR code center
logo_x = (SIZE - disc_size) // 2
logo_y = (SIZE - disc_size) // 2
qr_img.paste(disc, (logo_x, logo_y), disc)

# 5. Save
qr_img = qr_img.convert("RGB")
qr_img.save(OUTPUT, "PNG", dpi=(300, 300))
print(f"QR code saved to {OUTPUT} ({SIZE}x{SIZE}px)")
