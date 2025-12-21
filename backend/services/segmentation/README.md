# Segmentation Module

模块化的图像元素分割功能。

## 模块结构

- `prompts.py`: Prompt 管理，支持不同背景类型的专用 prompt
- `background_handler.py`: 背景检测和处理
- `result_processor.py`: 结果后处理（验证、去重、优化）

## 使用方法

### 基本使用

```python
from services.element_segmentation_service import ElementSegmentationService

service = ElementSegmentationService()
elements = service.segment_image('path/to/image.png')
```

### 背景类型检测

系统会自动检测背景类型并选择相应的 prompt：
- `simple`: 简单纯色背景
- `gradient`: 渐变背景
- `textured`: 纹理背景（如 template_y.png）
- `complex`: 复杂装饰背景

对于 `textured` 和 `complex` 类型，会使用优化的 prompt，特别强调：
- 区分背景装饰和前景内容
- 只识别真正的内容元素
- 更精确的边界框

## 可视化工具

使用 `tools/visualize_segmentation.py` 可以可视化分割结果：

```bash
# 基本使用
python backend/tools/visualize_segmentation.py --image path/to/image.png

# 生成对比图
python backend/tools/visualize_segmentation.py --image image.png --comparison

# 使用已有的 JSON 结果
python backend/tools/visualize_segmentation.py --image image.png --json results.json

# 显示统计信息
python backend/tools/visualize_segmentation.py --image image.png --show-stats
```

## 测试工具

使用 `test_segmentation_manual.py` 进行测试：

```bash
# 基本测试（自动生成可视化）
python backend/test_segmentation_manual.py path/to/image.png

# 生成对比图
python backend/test_segmentation_manual.py image.png --comparison

# 指定输出目录
python backend/test_segmentation_manual.py image.png --output-dir ./output
```

