import os
import sys
import subprocess
import shutil

def main():
    # 强制将 stdout 重新配置为 utf-8，如果在支持的环境下运行，这能解决一部分 unicode 打印问题。
    # 如果失败，我们依靠文本中没有 emoji 来保证安全。
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

    print("="*60)
    print("        PDF OCR for NotebookLM EXE Packaging Script")
    print("="*60)

    # 1. 确保安装了 PyInstaller
    try:
        import PyInstaller
        print("[OK] PyInstaller is installed.")
    except ImportError:
        print("[!] PyInstaller not found. Trying to install automatically...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
            import PyInstaller
            print("[OK] PyInstaller installed successfully.")
        except Exception as e:
            print(f"[FAIL] Failed to install PyInstaller: {e}")
            print("Please run manually: pip install pyinstaller")
            return

    # 2. 导入并定位 customtkinter
    try:
        import customtkinter
        ctk_path = os.path.dirname(customtkinter.__file__)
        print(f"[OK] Found customtkinter path: {ctk_path}")
    except ImportError:
        print("[!] customtkinter not found. Trying to install automatically...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "customtkinter"], check=True)
            import customtkinter
            ctk_path = os.path.dirname(customtkinter.__file__)
            print("[OK] customtkinter installed successfully.")
        except Exception as e:
            print(f"[FAIL] Failed to install customtkinter: {e}")
            return

    # 3. 构造打包资源附加参数 (--add-data)
    # Windows 平台下格式为 "源路径;目标包内相对路径"
    add_data_param = f"{ctk_path}{os.pathsep}customtkinter{os.sep}"
    print(f"[Config] Resource mapping: {add_data_param}")

    # 4. 选择打包模式 (单文件还是单文件夹)
    # 默认使用单文件夹模式 --onedir，因为启动速度最快，也最稳定。
    # 如果希望单文件，可以将 --onedir 改为 --onefile。
    mode = "--onedir"
    if len(sys.argv) > 1 and sys.argv[1] == "onefile":
        mode = "--onefile"
        print("[Config] Packaging mode: Single File (.exe)")
    else:
        print("[Config] Packaging mode: Single Directory (Fast startup, recommended)")

    # 清理历史构建缓存
    print("[Clean] Cleaning historical build caches...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"[WARN] Failed to clean {folder}: {e}")

    # 5. 执行 PyInstaller 打包
    cmd = [
        "pyinstaller",
        "--noconfirm",
        mode,
        "--windowed",  # 隐藏黑色命令行窗口，纯 GUI 启动
        "--icon=app_icon.ico",
        f"--add-data={add_data_param}",
        "gui_app.py"
    ]

    print(f"\n[Run] Starting PyInstaller compilation process...")
    print("Command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            # 打包成功后，将附属文件拷贝到 exe 所在的同级目录下
            dest_dir = "dist/gui_app" if mode == "--onedir" else "dist"
            try:
                shutil.copy2("batch_processor.py", os.path.join(dest_dir, "batch_processor.py"))
                print(f"[Done] Copied batch_processor.py to {dest_dir} successfully.")
                if os.path.exists("app_icon.ico"):
                    shutil.copy2("app_icon.ico", os.path.join(dest_dir, "app_icon.ico"))
            except Exception as e:
                print(f"[WARN] Failed to copy supplementary files to {dest_dir}: {e}")

            print("\n" + "="*60)
            print("[Done] Packaging completed successfully!")
            if mode == "--onefile":
                print(f"Generated single EXE at: dist/gui_app.exe")
            else:
                print(f"Generated directory at: dist/gui_app/")
                print(f"Please run the program from: dist/gui_app/gui_app.exe")
            print("="*60)
    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] PyInstaller failed with exit code: {e.returncode}")
    except Exception as e:
        print(f"\n[FAIL] Unknown error occurred: {e}")

if __name__ == "__main__":
    main()
