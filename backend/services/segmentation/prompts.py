"""
Prompt management for element segmentation
Supports different prompt strategies for various background types
"""
from typing import Dict, Optional
from enum import Enum


class BackgroundType(Enum):
    """Background type classification"""
    SIMPLE = "simple"  # Simple solid color or minimal background
    GRADIENT = "gradient"  # Gradient background
    TEXTURED = "textured"  # Textured background (like template_y.png)
    COMPLEX = "complex"  # Complex decorative background


class SegmentationPromptManager:
    """Manages segmentation prompts for different scenarios"""
    
    @staticmethod
    def get_default_prompt() -> str:
        """Get default segmentation prompt"""
        return """请仔细分析这张PPT幻灯片图片，识别其中的所有元素。

要求：
1. 识别所有文字内容，包括：
   - 文字的具体内容
   - 文字的位置（bounding box，格式：[x, y, width, height]，单位：像素）
   - 估算的字体大小（像素）
   - 字体粗细（bold 或 normal）

2. 识别所有图标和图片元素，包括：
   - 位置（bounding box）
   - 简要描述

3. 识别所有图表、图形元素，包括：
   - 位置（bounding box）
   - 类型描述（如：柱状图、饼图、流程图等）

4. 分析背景信息：
   - 是否有渐变
   - 主要颜色

请严格按照以下 JSON 格式返回结果，不要添加任何其他文字说明：

{
    "text_elements": [
        {
            "text": "文字内容",
            "bbox": [x, y, width, height],
            "font_size": 24,
            "font_weight": "bold"
        }
    ],
    "icons": [
        {
            "type": "icon",
            "bbox": [x, y, width, height],
            "description": "图标描述"
        }
    ],
    "charts": [
        {
            "type": "chart",
            "bbox": [x, y, width, height],
            "description": "图表描述"
        }
    ],
    "background_info": {
        "has_gradient": false,
        "main_color": "白色"
    }
}

注意：
- bbox 坐标从图片左上角 (0, 0) 开始
- 格式为 [x, y, width, height]，其中：
  - x, y: 左上角坐标（像素）
  - width, height: 宽度和高度（像素）
- 如果某个类别没有元素，返回空数组 []
- 确保所有坐标都在图片范围内
- 字体大小是估算值，基于文字在图片中的相对大小"""
    
    @staticmethod
    def get_complex_background_prompt() -> str:
        """Get prompt optimized for complex backgrounds (like template_y.png)"""
        return """请仔细分析这张PPT幻灯片图片，识别其中的所有可编辑元素。

重要提示：
- 这张图片有复杂的背景（如纹理、装饰图案、渐变等）
- **背景装饰元素（如边框、花纹、背景图案、装饰性图标）不应该被识别为前景元素**
- **只识别真正的内容元素：文字、图标、图表、图片等**
- **边界框要尽可能精确，紧密包围元素内容，不要包含多余的背景区域**

要求：
1. 识别所有文字内容（不包括背景中的装饰文字），包括：
   - 文字的具体内容
   - 文字的位置（bounding box，格式：[x, y, width, height]，单位：像素）
   - **边界框应该紧密包围文字，不要包含过多空白**
   - 估算的字体大小（像素）
   - 字体粗细（bold 或 normal）
   - **只识别作为内容主体的文字，忽略背景装饰中的文字**

2. 识别所有图标和图片元素（不包括背景装饰），包括：
   - 位置（bounding box）
   - 简要描述
   - **边界框应该紧密包围图标，不要包含背景区域**
   - **只识别作为内容主体的图标/图片，背景装饰图案不算**
   - **不要识别背景中的小装饰元素（如小图标、装饰性图案）**

3. 识别所有图表、图形元素，包括：
   - 位置（bounding box）
   - 类型描述（如：柱状图、饼图、流程图等）

4. 分析背景信息：
   - 是否有渐变
   - 主要颜色
   - 是否有复杂纹理或装饰

请严格按照以下 JSON 格式返回结果，不要添加任何其他文字说明：

{
    "text_elements": [
        {
            "text": "文字内容",
            "bbox": [x, y, width, height],
            "font_size": 24,
            "font_weight": "bold"
        }
    ],
    "icons": [
        {
            "type": "icon",
            "bbox": [x, y, width, height],
            "description": "图标描述"
        }
    ],
    "charts": [
        {
            "type": "chart",
            "bbox": [x, y, width, height],
            "description": "图表描述"
        }
    ],
    "background_info": {
        "has_gradient": false,
        "main_color": "白色",
        "has_texture": false
    }
}

注意：
- bbox 坐标从图片左上角 (0, 0) 开始
- 格式为 [x, y, width, height]，其中：
  - x, y: 左上角坐标（像素）
  - width, height: 宽度和高度（像素）
- 如果某个类别没有元素，返回空数组 []
- **确保所有坐标都在图片范围内**
- **边界框要尽可能精确，紧密包围元素内容**
- **不要将背景装饰误识别为前景元素**
- **对于文字元素，边界框应该紧密包围文字内容，不要包含过多空白**
- **对于图标，只识别有意义的图标，忽略背景中的小装饰元素**"""
    
    @staticmethod
    def get_prompt(background_type: Optional[BackgroundType] = None) -> str:
        """
        Get appropriate prompt based on background type
        
        Args:
            background_type: Background type classification
            
        Returns:
            Prompt string
        """
        if background_type == BackgroundType.TEXTURED or background_type == BackgroundType.COMPLEX:
            return SegmentationPromptManager.get_complex_background_prompt()
        else:
            return SegmentationPromptManager.get_default_prompt()


def get_prompt_for_background_type(background_type: Optional[BackgroundType] = None) -> str:
    """
    Convenience function to get prompt for background type
    
    Args:
        background_type: Background type classification
        
    Returns:
        Prompt string
    """
    return SegmentationPromptManager.get_prompt(background_type)

