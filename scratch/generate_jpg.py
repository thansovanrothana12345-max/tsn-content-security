from PIL import Image, ImageDraw, ImageFont
import os

# Create a 400x400 solid color image
img = Image.new("RGB", (400, 400), color=(130, 84, 255)) # TSN accent purple

# Add some text
draw = ImageDraw.Draw(img)
draw.text((50, 180), "Test Evidence JPG", fill=(255, 255, 255))

# Save to scratch folder
scratch_dir = os.path.dirname(os.path.abspath(__file__))
target_path = os.path.join(scratch_dir, "test_evidence.jpg")
img.save(target_path, "JPEG")
print(f"Generated test image at: {target_path}")
