"""
手动测试 ElementSegmentationService
用于验证真实 Vision API 调用
"""
import os
import sys
import json
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from services.element_segmentation_service import ElementSegmentationService


def test_segmentation(image_path: str):
    """测试元素分割服务"""
    print(f"\n{'='*60}")
    print(f"测试图片: {image_path}")
    print(f"{'='*60}\n")
    
    # 检查图片是否存在
    if not os.path.exists(image_path):
        print(f"❌ 图片不存在: {image_path}")
        return None
    
    try:
        # 创建服务实例
        print("1. 初始化 ElementSegmentationService...")
        service = ElementSegmentationService()
        print("   ✓ 服务初始化成功")
        print(f"   模型: {service.model}")
        
        # 调用分割
        print("\n2. 调用 Vision API 识别元素...")
        print("   (这可能需要 3-10 秒...)")
        elements = service.segment_image(image_path)
        print("   ✓ 元素识别成功")
        
        # 打印结果
        print("\n3. 识别结果:")
        print(f"   - 文字元素: {len(elements.get('text_elements', []))} 个")
        print(f"   - 图标: {len(elements.get('icons', []))} 个")
        print(f"   - 图表: {len(elements.get('charts', []))} 个")
        print(f"   - 背景信息: {elements.get('background_info', {})}")
        
        # 打印前几个文字元素
        text_elements = elements.get('text_elements', [])
        if text_elements:
            print("\n4. 文字元素详情（前5个）:")
            for i, elem in enumerate(text_elements[:5], 1):
                text = elem.get('text', '')
                bbox = elem.get('bbox', [])
                font_size = elem.get('font_size', 'N/A')
                font_weight = elem.get('font_weight', 'N/A')
                print(f"   {i}. 文字: {text[:60]}{'...' if len(text) > 60 else ''}")
                print(f"      位置: {bbox}")
                print(f"      字体: {font_size}pt, {font_weight}")
        
        # 打印图标
        icons = elements.get('icons', [])
        if icons:
            print("\n5. 图标详情（前3个）:")
            for i, icon in enumerate(icons[:3], 1):
                bbox = icon.get('bbox', [])
                desc = icon.get('description', '')
                print(f"   {i}. 描述: {desc}")
                print(f"      位置: {bbox}")
        
        # 打印图表
        charts = elements.get('charts', [])
        if charts:
            print("\n6. 图表详情（前3个）:")
            for i, chart in enumerate(charts[:3], 1):
                bbox = chart.get('bbox', [])
                desc = chart.get('description', '')
                print(f"   {i}. 描述: {desc}")
                print(f"      位置: {bbox}")
        
        # 保存完整结果到 JSON 文件（可选）
        output_file = image_path.replace('.png', '_elements.json').replace('.jpg', '_elements.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(elements, f, ensure_ascii=False, indent=2)
        print(f"\n7. 完整结果已保存到: {output_file}")
        
        print(f"\n{'='*60}")
        print("✓ 测试完成")
        print(f"{'='*60}\n")
        
        return elements
        
    except ValueError as e:
        print(f"❌ 配置错误: {str(e)}")
        print("   请确保设置了 GOOGLE_API_KEY 环境变量")
        return None
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    # 使用项目中的实际图片测试
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
    else:
        # 尝试查找项目中的图片
        uploads_dir = Path(__file__).parent.parent / 'uploads'
        if uploads_dir.exists():
            # 查找第一个可用的图片
            for project_dir in uploads_dir.iterdir():
                pages_dir = project_dir / 'pages'
                if pages_dir.exists():
                    for img_file in pages_dir.glob('*.png'):
                        test_image = str(img_file)
                        print(f"找到测试图片: {test_image}")
                        break
                    else:
                        continue
                    break
            else:
                test_image = None
        else:
            test_image = None
    
    if not test_image:
        print("用法: python test_segmentation_manual.py <图片路径>")
        print("\n示例:")
        print("  python test_segmentation_manual.py ../uploads/xxx/pages/slide_01.png")
        print("\n或者直接运行，会自动查找项目中的图片")
        sys.exit(1)
    
    test_segmentation(test_image)

