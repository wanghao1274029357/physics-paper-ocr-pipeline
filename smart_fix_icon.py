from PIL import Image, ImageDraw

def force_crop():
    img_path = r"C:\Users\12740\.gemini\antigravity-ide\brain\fd5dbae5-eb7e-442f-91fa-63c48e8f40aa\pdf_ocr_app_icon_1781176372416.png"
    ico_path = r"C:\Users\12740\Documents\antigravity\pdf for notebookLM\app_icon.ico"

    img = Image.open(img_path).convert("RGBA")
    w, h = img.size

    # 根据您截图中的比例判断，之前向内收缩 6% 只切掉了一层皮，那层黑框极其厚。
    # 真正的蓝色高亮主体差不多被包裹在中间 66% 的区域。
    # 所以我们这次强制向内“深挖”切除四周各 17% 的无用深色边距。
    margin_x = int(w * 0.17)
    margin_y = int(h * 0.17)
    
    # 将主体蓝色部分抠出来
    cropped = img.crop((margin_x, margin_y, w - margin_x, h - margin_y))
    cw, ch = cropped.size
    
    # 为扣出来的这个主体创建一个极其完美的圆角遮罩
    mask = Image.new("L", (cw, ch), 0)
    draw = ImageDraw.Draw(mask)
    rad = int(cw * 0.22)
    draw.rounded_rectangle((0, 0, cw, ch), radius=rad, fill=255)
    
    # 合成具有完美平滑圆角的最终图标
    final_img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    final_img.paste(cropped, (0, 0))
    final_img.putalpha(mask)
    
    # 另存为 ICO
    icon_sizes = [(16,16), (24,24), (32, 32), (48, 48), (64,64), (128, 128), (256, 256)]
    final_img.save(ico_path, format="ICO", sizes=icon_sizes)
    print(f"Force crop completed. Margins removed: X({margin_x}), Y({margin_y})")

if __name__ == '__main__':
    force_crop()
