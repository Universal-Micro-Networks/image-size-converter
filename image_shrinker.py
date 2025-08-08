from PIL import Image
import os

def generate_ios_assets(image_path):
    # 入力画像ファイルの読み込み
    img = Image.open(image_path)

    # ファイル名と拡張子を分割
    filename, ext = os.path.splitext(os.path.basename(image_path))
    base_name = filename.replace('@3x', '')  # 元が@3xだった場合の処理

    # 出力ディレクトリの作成
    output_dir = os.path.dirname(image_path)

    # 3x サイズ → 保存（元画像）
    img.save(os.path.join(output_dir, f"{base_name}@3x{ext}"))

    # 2x サイズ生成
    img_2x = img.resize((img.width // 3 * 2, img.height // 3 * 2), Image.LANCZOS)
    img_2x.save(os.path.join(output_dir, f"{base_name}@2x{ext}"))

    # 1x サイズ生成
    img_1x = img.resize((img.width // 3, img.height // 3), Image.LANCZOS)
    img_1x.save(os.path.join(output_dir, f"{base_name}{ext}"))

    print("✅ 画像リソースを出力しました:")
    print(f" - {base_name}{ext} (1x)")
    print(f" - {base_name}@2x{ext}")
    print(f" - {base_name}@3x{ext}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "-s":
        generate_ios_assets(sys.argv[2])
    else:
        print("Usage: python main.py -s <image_path>")
