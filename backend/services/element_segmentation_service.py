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
from services.segmentation import (
    SegmentationPromptManager,
    BackgroundHandler,
    ResultProcessor,
    BackgroundType
)

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
        
        # Detect background type to select appropriate prompt
        background_type_str = BackgroundHandler.detect_background_type(image)
        logger.debug(f"Detected background type: {background_type_str}")
        
        # Map string to BackgroundType enum
        background_type_map = {
            'simple': BackgroundType.SIMPLE,
            'gradient': BackgroundType.GRADIENT,
            'textured': BackgroundType.TEXTURED,
            'complex': BackgroundType.COMPLEX
        }
        background_type = background_type_map.get(background_type_str, BackgroundType.COMPLEX)
        
        # Identify elements with Vision API (using appropriate prompt)
        elements_info = self._identify_elements_with_vision(image, background_type)
        
        # Enhance background info if not provided
        if not elements_info.get('background_info'):
            elements_info['background_info'] = BackgroundHandler.analyze_background_info(image)
        
        # Validate and clean elements using ResultProcessor
        validated_elements = ResultProcessor.validate_and_clean_elements(
            elements_info, 
            (image_width, image_height)
        )
        
        return validated_elements
    
    def _identify_elements_with_vision(
        self,
        image: Image.Image,
        background_type: Optional[BackgroundType] = None
    ) -> Dict:
        """
        Call Gemini Vision API to identify elements
        
        Args:
            image: PIL Image object
            background_type: Background type for prompt selection
            
        Returns:
            Raw elements info from Vision API
            
        Raises:
            Exception: If API call fails
        """
        # Use prompt manager to get appropriate prompt
        prompt = SegmentationPromptManager.get_prompt(background_type)
        
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
    

