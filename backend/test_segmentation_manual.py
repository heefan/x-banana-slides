"""
手动测试 ElementSegmentationService
用于验证真实 Vision API 调用
支持可视化输出
"""
import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（从项目根目录）
_project_root = Path(__file__).parent.parent
_env_file = _project_root / '.env'
if _env_file.exists():
    load_dotenv(dotenv_path=_env_file, override=True)
    print(f"✓ 已加载 .env 文件: {_env_file}")
else:
    print(f"⚠️  .env 文件不存在: {_env_file}")

# 添加 backend 到路径
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from services.element_segmentation_service import ElementSegmentationService
from tools.visualize_segmentation import SegmentationVisualizer
from services.segmentation import ResultProcessor


def test_segmentation(
    image_path: str,
    visualize: bool = True,
    comparison: bool = False,
    output_dir: str = None,
    show_stats: bool = True
):
    """
    测试元素分割服务
    
    Args:
        image_path: 图片路径
        visualize: 是否生成可视化图片
        comparison: 是否生成对比图（原图 vs 标注图）
        output_dir: 输出目录（默认与图片同目录）
        show_stats: 是否显示统计信息
    """
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
        
        # 显示统计信息
        if show_stats:
            stats = ResultProcessor.get_statistics(elements)
            print("\n3. 识别结果统计:")
            print(f"   - 文字元素: {stats['total_text_elements']} 个")
            print(f"   - 图标: {stats['total_icons']} 个")
            print(f"   - 图表: {stats['total_charts']} 个")
            print(f"   - 总元素数: {stats['total_elements']} 个")
            print(f"   - 有内容的文字元素: {stats['text_elements_with_content']} 个")
            print(f"   - 平均文字长度: {stats['average_text_length']:.1f} 字符")
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
        
        # 确定输出目录
        if output_dir:
            output_path_base = Path(output_dir)
        else:
            # 默认保存到图片所在目录的 segmentation_results 子文件夹
            output_path_base = Path(image_path).parent / 'segmentation_results'
        
        # 创建输出目录（如果不存在）
        output_path_base.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 输出目录: {output_path_base}")
        
        # 保存完整结果到 JSON 文件
        json_output = output_path_base / f"{Path(image_path).stem}_elements.json"
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(elements, f, ensure_ascii=False, indent=2)
        print(f"\n7. 完整结果已保存到: {json_output}")
        
        # 生成可视化图片
        if visualize:
            print("\n8. 生成可视化图片...")
            visualizer = SegmentationVisualizer()
            
            if comparison:
                vis_output = output_path_base / f"{Path(image_path).stem}_comparison.png"
                visualizer.create_comparison(str(image_path), elements, str(vis_output))
                print(f"   ✓ 对比图已保存到: {vis_output}")
            else:
                vis_output = output_path_base / f"{Path(image_path).stem}_visualized.png"
                visualizer.visualize(str(image_path), elements, str(vis_output), show_labels=True)
                print(f"   ✓ 可视化图片已保存到: {vis_output}")
        
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
    parser = argparse.ArgumentParser(
        description='测试元素分割服务，支持可视化输出'
    )
    parser.add_argument(
        'image',
        nargs='?',
        type=str,
        help='图片路径'
    )
    parser.add_argument(
        '--no-visualize',
        action='store_true',
        help='不生成可视化图片'
    )
    parser.add_argument(
        '--comparison',
        action='store_true',
        help='生成对比图（原图 vs 标注图）'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='输出目录（默认与图片同目录）'
    )
    parser.add_argument(
        '--no-stats',
        action='store_true',
        help='不显示统计信息'
    )
    
    args = parser.parse_args()
    
    # 确定测试图片
    if args.image:
        test_image = args.image
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
        print("用法: python test_segmentation_manual.py <图片路径> [选项]")
        print("\n示例:")
        print("  python test_segmentation_manual.py ../uploads/xxx/pages/slide_01.png")
        print("  python test_segmentation_manual.py image.png --comparison")
        print("  python test_segmentation_manual.py image.png --output-dir ./output")
        print("\n选项:")
        print("  --no-visualize    不生成可视化图片")
        print("  --comparison      生成对比图（原图 vs 标注图）")
        print("  --output-dir DIR  指定输出目录")
        print("  --no-stats        不显示统计信息")
        print("\n或者直接运行，会自动查找项目中的图片")
        sys.exit(1)
    
    test_segmentation(
        test_image,
        visualize=not args.no_visualize,
        comparison=args.comparison,
        output_dir=args.output_dir,
        show_stats=not args.no_stats
    )

