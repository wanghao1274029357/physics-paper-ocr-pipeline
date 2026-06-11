from PIL import Image, ImageDraw

def process_icon():
    img_path = r"C:\Users\12740\.gemini\antigravity-ide\brain\fd5dbae5-eb7e-442f-91fa-63c48e8f40aa\pdf_ocr_app_icon_1781176372416.png"
    ico_path = r"C:\Users\12740\Documents\antigravity\pdf for notebookLM\app_icon.ico"
    
    try:
        img = Image.open(img_path).convert("RGBA")
        w, h = img.size
        
        # 创建 Alpha 透明遮罩
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        
        # 很多 AI 图标自带一点黑底边缘，我们向内收缩 6% 并打磨出一个完美的平滑圆角
        margin = int(w * 0.06)
        rad = int(w * 0.22) # 圆角半径设定为宽度的22%，这是苹果风/现代UI最常用的G7曲率参数
        
        # 绘制纯白色的圆角矩形区域（作为保留区）
        draw.rounded_rectangle((margin, margin, w - margin, h - margin), radius=rad, fill=255)
        
        # 应用遮罩，把外围那层黑框变成纯透明（Alpha=0）
        result = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        result.paste(img, (0, 0), mask=mask)
        
        # 自动裁剪掉四周已经被我们变透明的无用空间，让图标撑满整个框
        bbox = result.getbbox()
        if bbox:
            result = result.crop(bbox)
            
        # 重新生成多分辨率的 ICO
        icon_sizes = [(16,16), (24,24), (32, 32), (48, 48), (64,64), (128, 128), (256, 256)]
        result.save(ico_path, format="ICO", sizes=icon_sizes)
        print("Success! The icon background has been made transparent with smooth rounded corners.")
    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == '__main__':
    process_icon()
