"""
Result processing for element segmentation
Post-processes segmentation results: deduplication, merging, bbox optimization
"""
import logging
from typing import Dict, List, Tuple, Optional
from PIL import Image

logger = logging.getLogger(__name__)


class ResultProcessor:
    """Processes and optimizes segmentation results"""
    
    @staticmethod
    def validate_and_clean_elements(
        elements_info: Dict,
        image_size: Tuple[int, int]
    ) -> Dict:
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
        text_elements = ResultProcessor._validate_elements(
            elements_info.get('text_elements', []),
            image_width,
            image_height,
            'text'
        )
        validated['text_elements'] = text_elements
        
        # Validate icons
        icons = ResultProcessor._validate_elements(
            elements_info.get('icons', []),
            image_width,
            image_height,
            'icon'
        )
        validated['icons'] = icons
        
        # Validate charts
        charts = ResultProcessor._validate_elements(
            elements_info.get('charts', []),
            image_width,
            image_height,
            'chart'
        )
        validated['charts'] = charts
        
        # Post-process: filter small elements (likely noise)
        min_text_area = 100  # Minimum area for text elements (pixels^2)
        min_icon_area = 200  # Minimum area for icons (pixels^2)
        min_chart_area = 500  # Minimum area for charts (pixels^2)
        
        validated['text_elements'] = ResultProcessor._filter_small_elements(
            validated['text_elements'],
            min_text_area
        )
        validated['icons'] = ResultProcessor._filter_small_elements(
            validated['icons'],
            min_icon_area
        )
        validated['charts'] = ResultProcessor._filter_small_elements(
            validated['charts'],
            min_chart_area
        )
        
        # Post-process: remove duplicates and merge overlapping elements
        validated['text_elements'] = ResultProcessor._deduplicate_elements(
            validated['text_elements']
        )
        validated['icons'] = ResultProcessor._deduplicate_elements(
            validated['icons']
        )
        validated['charts'] = ResultProcessor._deduplicate_elements(
            validated['charts']
        )
        
        logger.info(
            f"Validated elements: {len(validated['text_elements'])} text, "
            f"{len(validated['icons'])} icons, {len(validated['charts'])} charts"
        )
        
        return validated
    
    @staticmethod
    def _validate_elements(
        elements: List[Dict],
        image_width: int,
        image_height: int,
        element_type: str
    ) -> List[Dict]:
        """
        Validate elements and filter invalid ones
        
        Args:
            elements: List of element dictionaries
            image_width: Image width
            image_height: Image height
            element_type: Type of element ('text', 'icon', 'chart')
            
        Returns:
            List of validated elements
        """
        validated = []
        for elem in elements:
            bbox = elem.get('bbox', [])
            if ResultProcessor._is_valid_bbox(bbox, image_width, image_height):
                # Ensure bbox is within bounds (clamp if needed)
                clamped_bbox = ResultProcessor._clamp_bbox(bbox, image_width, image_height)
                elem['bbox'] = clamped_bbox
                validated.append(elem)
            else:
                logger.warning(
                    f"Invalid {element_type} element bbox: {bbox}, "
                    f"image size: {image_width}x{image_height}"
                )
        return validated
    
    @staticmethod
    def _is_valid_bbox(
        bbox: List[float],
        image_width: int,
        image_height: int
    ) -> bool:
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
        
        # Check coordinates are within image bounds (allow slight overflow for rounding)
        if x < -10 or y < -10:  # Allow small negative values
            return False
        
        if x + width > image_width + 10 or y + height > image_height + 10:
            return False
        
        return True
    
    @staticmethod
    def _clamp_bbox(
        bbox: List[float],
        image_width: int,
        image_height: int
    ) -> List[float]:
        """
        Clamp bbox to image bounds and ensure reasonable size
        
        Args:
            bbox: [x, y, width, height]
            image_width: Image width
            image_height: Image height
            
        Returns:
            Clamped bbox [x, y, width, height]
        """
        x, y, width, height = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        
        # Clamp x and y to valid range
        x = max(0, min(x, image_width - 1))
        y = max(0, min(y, image_height - 1))
        
        # Clamp width and height to ensure within bounds
        width = max(1, min(width, image_width - x))
        height = max(1, min(height, image_height - y))
        
        return [x, y, width, height]
    
    @staticmethod
    def _filter_small_elements(
        elements: List[Dict],
        min_area: int = 100
    ) -> List[Dict]:
        """
        Filter out elements that are too small (likely noise or background decoration)
        
        Args:
            elements: List of element dictionaries
            min_area: Minimum area in pixels^2 to keep an element
            
        Returns:
            Filtered list of elements
        """
        filtered = []
        for elem in elements:
            bbox = elem.get('bbox', [])
            if len(bbox) == 4:
                area = float(bbox[2]) * float(bbox[3])  # width * height
                if area >= min_area:
                    filtered.append(elem)
                else:
                    logger.debug(
                        f"Filtered out small element: {elem.get('description', elem.get('text', 'unknown'))[:30]}, "
                        f"area: {area:.1f} < {min_area}"
                    )
        return filtered
    
    @staticmethod
    def _deduplicate_elements(elements: List[Dict]) -> List[Dict]:
        """
        Remove duplicate and highly overlapping elements
        
        Args:
            elements: List of element dictionaries
            
        Returns:
            Deduplicated list of elements
        """
        if len(elements) <= 1:
            return elements
        
        # Sort by area (larger first) to keep more complete elements
        sorted_elements = sorted(
            elements,
            key=lambda e: ResultProcessor._bbox_area(e.get('bbox', [0, 0, 0, 0])),
            reverse=True
        )
        
        result = []
        for elem in sorted_elements:
            # Check if this element overlaps significantly with any existing element
            is_duplicate = False
            bbox = elem.get('bbox', [])
            
            for existing_elem in result:
                existing_bbox = existing_elem.get('bbox', [])
                overlap_ratio = ResultProcessor._calculate_overlap(bbox, existing_bbox)
                
                # If overlap is more than 70%, consider it a duplicate (lowered from 80% for stricter filtering)
                if overlap_ratio > 0.7:
                    is_duplicate = True
                    logger.debug(
                        f"Removed duplicate element (overlap: {overlap_ratio:.2%}): "
                        f"{elem.get('description', elem.get('text', 'unknown'))[:30]}"
                    )
                    break
            
            if not is_duplicate:
                result.append(elem)
        
        return result
    
    @staticmethod
    def _bbox_area(bbox: List[float]) -> float:
        """Calculate bbox area"""
        if len(bbox) != 4:
            return 0
        return float(bbox[2]) * float(bbox[3])
    
    @staticmethod
    def _calculate_overlap(bbox1: List[float], bbox2: List[float]) -> float:
        """
        Calculate overlap ratio between two bboxes
        
        Args:
            bbox1: [x1, y1, w1, h1]
            bbox2: [x2, y2, w2, h2]
            
        Returns:
            Overlap ratio (0.0 to 1.0)
        """
        if len(bbox1) != 4 or len(bbox2) != 4:
            return 0.0
        
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate intersection
        x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        y_overlap = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
        intersection = x_overlap * y_overlap
        
        # Calculate union
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    @staticmethod
    def get_statistics(elements_info: Dict) -> Dict:
        """
        Get statistics about segmentation results
        
        Args:
            elements_info: Elements info dictionary
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'total_text_elements': len(elements_info.get('text_elements', [])),
            'total_icons': len(elements_info.get('icons', [])),
            'total_charts': len(elements_info.get('charts', [])),
            'total_elements': 0,
            'text_elements_with_content': 0,
            'average_text_length': 0.0,
        }
        
        text_elements = elements_info.get('text_elements', [])
        stats['total_elements'] = (
            stats['total_text_elements'] +
            stats['total_icons'] +
            stats['total_charts']
        )
        
        if text_elements:
            text_lengths = [len(elem.get('text', '')) for elem in text_elements]
            stats['text_elements_with_content'] = sum(1 for length in text_lengths if length > 0)
            stats['average_text_length'] = sum(text_lengths) / len(text_lengths) if text_lengths else 0.0
        
        return stats

