from PIL import Image
import os

png_path = r"C:\Users\12740\.gemini\antigravity-ide\brain\fd5dbae5-eb7e-442f-91fa-63c48e8f40aa\pdf_ocr_app_icon_1781176372416.png"
ico_path = r"C:\Users\12740\Documents\antigravity\pdf for notebookLM\app_icon.ico"

img = Image.open(png_path)
icon_sizes = [(16,16), (32, 32), (48, 48), (64,64), (128, 128), (256, 256)]
img.save(ico_path, format="ICO", sizes=icon_sizes)
print(f"Successfully converted to {ico_path}")
