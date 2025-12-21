"""
Background handling for element segmentation
Detects and handles complex backgrounds to improve segmentation accuracy
"""
import logging
from typing import Dict, Optional, Tuple, List
from PIL import Image

logger = logging.getLogger(__name__)


class BackgroundHandler:
    """Handles background detection and processing for segmentation"""
    
    @staticmethod
    def detect_background_type(image: Image.Image) -> str:
        """
        Detect background type from image
        
        Args:
            image: PIL Image object
            
        Returns:
            Background type string: 'simple', 'gradient', 'textured', or 'complex'
        """
        try:
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            width, height = image.size
            
            # Sample edge pixels (likely background)
            edge_pixels = []
            # Top edge
            for x in range(0, width, max(1, width // 20)):
                edge_pixels.append(image.getpixel((x, 0)))
            # Bottom edge
            for x in range(0, width, max(1, width // 20)):
                edge_pixels.append(image.getpixel((x, height - 1)))
            # Left edge
            for y in range(0, height, max(1, height // 20)):
                edge_pixels.append(image.getpixel((0, y)))
            # Right edge
            for y in range(0, height, max(1, height // 20)):
                edge_pixels.append(image.getpixel((width - 1, y)))
            
            # Calculate color variance in edge pixels
            if not edge_pixels:
                return 'complex'
            
            # Calculate mean and variance for each channel
            r_values = [p[0] for p in edge_pixels]
            g_values = [p[1] for p in edge_pixels]
            b_values = [p[2] for p in edge_pixels]
            
            def variance(values):
                if not values:
                    return 0
                mean = sum(values) / len(values)
                return sum((x - mean) ** 2 for x in values) / len(values)
            
            r_var = variance(r_values)
            g_var = variance(g_values)
            b_var = variance(b_values)
            color_variance = (r_var + g_var + b_var) / 3
            
            # Sample center region for texture detection
            center_x, center_y = width // 2, height // 2
            center_region_size = min(width // 4, height // 4)
            center_pixels = []
            
            for x in range(max(0, center_x - center_region_size),
                          min(width, center_x + center_region_size),
                          max(1, center_region_size // 10)):
                for y in range(max(0, center_y - center_region_size),
                              min(height, center_y + center_region_size),
                              max(1, center_region_size // 10)):
                    center_pixels.append(image.getpixel((x, y)))
            
            # Calculate local variance (texture detection)
            if center_pixels:
                r_vals = [p[0] for p in center_pixels]
                g_vals = [p[1] for p in center_pixels]
                b_vals = [p[2] for p in center_pixels]
                local_variance = (variance(r_vals) + variance(g_vals) + variance(b_vals)) / 3
            else:
                local_variance = 0
            
            # Simple heuristic classification
            if color_variance < 100 and local_variance < 500:
                return 'simple'
            elif color_variance > 5000 or local_variance > 10000:
                return 'textured'  # High variance suggests texture
            elif color_variance > 1000:
                return 'gradient'
            else:
                return 'complex'
                
        except Exception as e:
            logger.warning(f"Failed to detect background type: {e}, defaulting to 'complex'")
            return 'complex'
    
    @staticmethod
    def analyze_background_info(image: Image.Image) -> Dict:
        """
        Analyze background information
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with background analysis results
        """
        try:
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            width, height = image.size
            
            # Sample edge pixels for background color
            edge_pixels = []
            # Sample edges (sparse sampling for performance)
            step = max(1, min(width, height) // 20)
            for x in range(0, width, step):
                edge_pixels.append(image.getpixel((x, 0)))
                edge_pixels.append(image.getpixel((x, height - 1)))
            for y in range(0, height, step):
                edge_pixels.append(image.getpixel((0, y)))
                edge_pixels.append(image.getpixel((width - 1, y)))
            
            if not edge_pixels:
                return {
                    'has_gradient': False,
                    'main_color': '未知',
                    'has_texture': False
                }
            
            # Calculate average color
            r_sum = sum(p[0] for p in edge_pixels)
            g_sum = sum(p[1] for p in edge_pixels)
            b_sum = sum(p[2] for p in edge_pixels)
            count = len(edge_pixels)
            avg_color = [int(r_sum / count), int(g_sum / count), int(b_sum / count)]
            
            # Check for gradient by comparing corners
            corners = [
                image.getpixel((0, 0)),
                image.getpixel((width - 1, 0)),
                image.getpixel((0, height - 1)),
                image.getpixel((width - 1, height - 1))
            ]
            
            def color_variance(pixels):
                if not pixels:
                    return 0
                r_vals = [p[0] for p in pixels]
                g_vals = [p[1] for p in pixels]
                b_vals = [p[2] for p in pixels]
                r_var = sum((r - sum(r_vals)/len(r_vals))**2 for r in r_vals) / len(r_vals)
                g_var = sum((g - sum(g_vals)/len(g_vals))**2 for g in g_vals) / len(g_vals)
                b_var = sum((b - sum(b_vals)/len(b_vals))**2 for b in b_vals) / len(b_vals)
                return (r_var + g_var + b_var) / 3
            
            corner_variance = color_variance(corners)
            has_gradient = corner_variance > 500
            
            # Simple color name mapping
            color_name = BackgroundHandler._rgb_to_color_name(avg_color)
            
            return {
                'has_gradient': has_gradient,
                'main_color': color_name,
                'has_texture': BackgroundHandler.detect_background_type(image) in ['textured', 'complex']
            }
            
        except Exception as e:
            logger.warning(f"Failed to analyze background: {e}")
            return {
                'has_gradient': False,
                'main_color': '未知',
                'has_texture': False
            }
    
    @staticmethod
    def _rgb_to_color_name(rgb: List[int]) -> str:
        """
        Convert RGB values to color name
        
        Args:
            rgb: RGB array [R, G, B]
            
        Returns:
            Color name string
        """
        r, g, b = rgb[0], rgb[1], rgb[2]
        
        # Simple color classification
        if r > 200 and g > 200 and b > 200:
            return '白色'
        elif r < 50 and g < 50 and b < 50:
            return '黑色'
        elif r > g and r > b:
            if r > 200:
                return '红色'
            else:
                return '深红色'
        elif g > r and g > b:
            if g > 200:
                return '绿色'
            else:
                return '深绿色'
        elif b > r and b > g:
            if b > 200:
                return '蓝色'
            else:
                return '深蓝色'
        elif abs(r - g) < 30 and abs(g - b) < 30:
            if r > 150:
                return '灰色'
            else:
                return '深灰色'
        else:
            return f'RGB({r},{g},{b})'

