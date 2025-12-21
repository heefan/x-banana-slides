"""
手动测试脚本：测试元素分割导出功能 (Story 2)

使用方法:
    python test_export_segmented_manual.py [image_path1] [image_path2] ...
    或者不传参数，自动查找项目图片
"""
import os
import sys
from pathlib import Path
from typing import Optional, List

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from services.export_service import ExportService
from config import get_config


def find_test_images() -> List[str]:
    """自动查找测试图片"""
    config = get_config()
    upload_folder = Path(config.UPLOAD_FOLDER)
    
    # Find any project folder
    project_dirs = [d for d in upload_folder.iterdir() if d.is_dir() and d.name != 'temp']
    if not project_dirs:
        print("❌ 未找到任何项目目录")
        return []
    
    # Find page images within projects
    image_paths = []
    for project_dir in project_dirs:
        page_images_dir = project_dir / 'pages'
        if page_images_dir.exists():
            for img_file in sorted(page_images_dir.glob('slide_*.png')):
                image_paths.append(str(img_file))
                # Limit to first 3 images for testing
                if len(image_paths) >= 3:
                    break
        if len(image_paths) >= 3:
            break
    
    return image_paths


def test_segmented_export(image_paths: List[str], output_path: Optional[str] = None):
    """测试元素分割导出功能"""
    print(f"\n{'='*60}")
    print("测试元素分割导出功能 (Story 2)")
    print(f"{'='*60}\n")
    
    if not image_paths:
        print("❌ 没有找到测试图片")
        print("\n使用方法:")
        print("  python test_export_segmented_manual.py [image_path1] [image_path2] ...")
        print("  或者确保 uploads/ 目录下有项目图片")
        return
    
    print(f"📸 找到 {len(image_paths)} 张测试图片:")
    for i, img_path in enumerate(image_paths, 1):
        print(f"  {i}. {img_path}")
    
    # Check if images exist
    valid_paths = []
    for img_path in image_paths:
        if os.path.exists(img_path):
            valid_paths.append(img_path)
        else:
            print(f"⚠️  图片不存在: {img_path}")
    
    if not valid_paths:
        print("❌ 没有有效的图片路径")
        return
    
    # Determine output path
    if not output_path:
        # Use first image's directory
        first_image_dir = Path(valid_paths[0]).parent
        output_path = str(first_image_dir / "test_segmented_export.pptx")
    
    print(f"\n📝 输出文件: {output_path}")
    print(f"\n{'='*60}")
    print("开始导出...")
    print(f"{'='*60}\n")
    
    try:
        # Test segmented export
        print("🔄 使用元素分割导出...")
        ExportService.create_pptx_with_segmented_elements(
            image_paths=valid_paths,
            output_file=output_path,
            use_segmentation=True
        )
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"\n✅ 导出成功！")
            print(f"   📄 文件: {output_path}")
            print(f"   📊 大小: {file_size / 1024:.2f} KB")
            print(f"\n💡 提示:")
            print(f"   1. 打开 {output_path} 查看结果")
            print(f"   2. 检查文字是否可编辑")
            print(f"   3. 检查图标是否可以移动")
            print(f"   4. 检查元素位置是否准确")
        else:
            print(f"❌ 导出失败：文件未生成")
    
    except Exception as e:
        print(f"\n❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        
        # Try simple export as fallback test
        print(f"\n{'='*60}")
        print("尝试简单导出（降级测试）...")
        print(f"{'='*60}\n")
        try:
            fallback_output = output_path.replace('.pptx', '_simple.pptx')
            ExportService.create_pptx_from_images(valid_paths, output_file=fallback_output)
            if os.path.exists(fallback_output):
                print(f"✅ 简单导出成功（降级）: {fallback_output}")
        except Exception as e2:
            print(f"❌ 简单导出也失败: {e2}")
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Use provided image paths
        image_paths = sys.argv[1:]
        test_segmented_export(image_paths)
    else:
        # Auto-find images
        image_paths = find_test_images()
        test_segmented_export(image_paths)

