"""
Element Segmentation Service - uses Gemini Vision API to identify elements in images
"""
import json
import re
import logging
from typing import Dict, Tuple, List, Optional
from PIL import Image
from google import genai
from google.genai import types

# Import private function for config (can be imported despite underscore)
from services.ai_providers import _get_provider_config

logger = logging.getLogger(__name__)


class ElementSegmentationService:
    """Service for segmenting images into editable elements using Vision API"""
    
    def __init__(self, text_provider=None):
        """
        Initialize element segmentation service
        
        Args:
            text_provider: TextProvider instance (optional, for config reuse)
        
        Note:
            Vision API uses Gemini format, so always uses GOOGLE_API_KEY and GOOGLE_API_BASE
        """
        # Get configuration (priority: Flask app.config > env var > default)
        provider_format, api_key, api_base = _get_provider_config()
        
        # Vision API should use Gemini format
        # If config is OpenAI format, still need Google API (Vision API is Gemini's)
        if provider_format == 'openai':
            # Try to get Google API key from config (may be set to same value)
            try:
                from flask import current_app
                if current_app and hasattr(current_app, 'config'):
                    api_key = current_app.config.get('GOOGLE_API_KEY') or api_key
                    api_base = current_app.config.get('GOOGLE_API_BASE') or api_base
            except RuntimeError:
                # Not in Flask context, use environment variable
                import os
                api_key = os.getenv('GOOGLE_API_KEY') or api_key
                api_base = os.getenv('GOOGLE_API_BASE') or api_base
        
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for Vision API")
        
        # Create genai.Client (reuse config logic)
        self.client = genai.Client(
            http_options=types.HttpOptions(base_url=api_base) if api_base else None,
            api_key=api_key
        )
        self.model = "gemini-3-pro-image-preview"  # Vision API uses image generation model
        
        logger.info(f"ElementSegmentationService initialized with model: {self.model}")
    
    def segment_image(self, image_path: str) -> Dict:
        """
        Segment image into elements
        
        Args:
            image_path: Path to image file
            
        Returns:
            {
                'text_elements': [
                    {
                        'text': '文字内容',
                        'bbox': [x, y, width, height],
                        'font_size': 24,
                        'font_weight': 'bold'
                    }
                ],
                'icons': [...],
                'charts': [...],
                'background_info': {...}
            }
            
        Raises:
            ValueError: If Vision API returns invalid data
            Exception: If API call fails
        """
        # Load image
        try:
            image = Image.open(image_path)
            image_width, image_height = image.size
            logger.debug(f"Loaded image: {image_path}, size: {image_width}x{image_height}")
        except Exception as e:
            raise ValueError(f"Failed to load image {image_path}: {str(e)}") from e
        
        # Identify elements with Vision API
        elements_info = self._identify_elements_with_vision(image)
        
        # Validate and clean elements
        validated_elements = self._validate_and_clean_elements(
            elements_info, 
            (image_width, image_height)
        )
        
        return validated_elements
    
    def _identify_elements_with_vision(self, image: Image.Image) -> Dict:
        """
        Call Gemini Vision API to identify elements
        
        Args:
            image: PIL Image object
            
        Returns:
            Raw elements info from Vision API
            
        Raises:
            Exception: If API call fails
        """
        prompt = self._get_segmentation_prompt()
        
        try:
            logger.debug(f"Calling Vision API with model: {self.model}")
            response = self.client.models.generate_content(
                model=self.model,
                contents=[image, prompt],  # Image first, then prompt
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for stable results
                    response_mime_type="application/json"  # Request JSON output
                )
            )
            
            logger.debug("Vision API call completed")
            
            # Parse JSON response
            if not response.text:
                raise ValueError("Vision API returned empty response")
            
            elements_info = self._parse_json_response(response.text)
            logger.debug(f"Parsed elements: {len(elements_info.get('text_elements', []))} text, "
                        f"{len(elements_info.get('icons', []))} icons, "
                        f"{len(elements_info.get('charts', []))} charts")
            
            return elements_info
            
        except Exception as e:
            error_detail = f"Vision API call failed: {type(e).__name__}: {str(e)}"
            logger.error(error_detail, exc_info=True)
            raise Exception(error_detail) from e
    
    def _get_segmentation_prompt(self) -> str:
        """Get the prompt for element segmentation"""
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
    
    def _parse_json_response(self, response_text: str) -> Dict:
        """
        Parse JSON response, handling various format issues
        
        Args:
            response_text: Raw response text from Vision API
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            ValueError: If JSON parsing fails
        """
        cleaned = response_text.strip()
        
        # Remove markdown code block markers
        if cleaned.startswith('```'):
            # Remove opening ```json or ```
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.MULTILINE)
        if cleaned.endswith('```'):
            cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
        
        # Try to parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Try to extract JSON part (may contain other text)
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            logger.error(f"Failed to parse JSON. Response preview: {cleaned[:200]}")
            raise ValueError(f"Failed to parse JSON from response: {cleaned[:200]}") from e
    
    def _validate_and_clean_elements(self, elements_info: Dict, image_size: Tuple[int, int]) -> Dict:
        """
        Validate and clean element data
        
        Args:
            elements_info: Raw elements info from Vision API
            image_size: Image size (width, height)
        
        Returns:
            Validated and cleaned elements info
        """
        image_width, image_height = image_size
        validated = {
            'text_elements': [],
            'icons': [],
            'charts': [],
            'background_info': elements_info.get('background_info', {})
        }
        
        # Validate text elements
        for elem in elements_info.get('text_elements', []):
            if self._is_valid_bbox(elem.get('bbox'), image_width, image_height):
                validated['text_elements'].append(elem)
            else:
                logger.warning(f"Invalid text element bbox: {elem.get('bbox')}, image size: {image_width}x{image_height}")
        
        # Validate icons
        for elem in elements_info.get('icons', []):
            if self._is_valid_bbox(elem.get('bbox'), image_width, image_height):
                validated['icons'].append(elem)
            else:
                logger.warning(f"Invalid icon bbox: {elem.get('bbox')}, image size: {image_width}x{image_height}")
        
        # Validate charts
        for elem in elements_info.get('charts', []):
            if self._is_valid_bbox(elem.get('bbox'), image_width, image_height):
                validated['charts'].append(elem)
            else:
                logger.warning(f"Invalid chart bbox: {elem.get('bbox')}, image size: {image_width}x{image_height}")
        
        logger.info(f"Validated elements: {len(validated['text_elements'])} text, "
                   f"{len(validated['icons'])} icons, {len(validated['charts'])} charts")
        
        return validated
    
    def _is_valid_bbox(self, bbox: List[float], image_width: int, image_height: int) -> bool:
        """
        Validate if bbox is valid
        
        Args:
            bbox: [x, y, width, height]
            image_width: Image width
            image_height: Image height
        
        Returns:
            True if bbox is valid
        """
        if not bbox or len(bbox) != 4:
            return False
        
        try:
            x, y, width, height = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        except (ValueError, TypeError):
            return False
        
        # Check width and height
        if width <= 0 or height <= 0:
            return False
        
        # Check coordinates are within image bounds
        if x < 0 or y < 0:
            return False
        
        if x + width > image_width or y + height > image_height:
            return False
        
        return True

