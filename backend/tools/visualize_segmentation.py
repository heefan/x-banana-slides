"""
Visualization tool for segmentation results
Draws bounding boxes on images to visualize segmentation results
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from services.element_segmentation_service import ElementSegmentationService
from services.segmentation import ResultProcessor


class SegmentationVisualizer:
    """Visualizes segmentation results by drawing bounding boxes on images"""
    
    # Color scheme for different element types
    COLORS = {
        'text': (0, 100, 255),      # Blue for text
        'icon': (0, 200, 0),        # Green for icons
        'chart': (255, 0, 0),       # Red for charts
        'background': (128, 128, 128)  # Gray for background info
    }
    
    def __init__(self, line_width: int = 3, font_size: int = 16):
        """
        Initialize visualizer
        
        Args:
            line_width: Width of bounding box lines
            font_size: Font size for labels
        """
        self.line_width = line_width
        self.font_size = font_size
        self.font = None
        try:
            # Try to load a font (fallback to default if not available)
            self.font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except Exception:
            try:
                self.font = ImageFont.load_default()
            except Exception:
                self.font = None
    
    def visualize(
        self,
        image_path: str,
        elements_info: Dict,
        output_path: Optional[str] = None,
        show_labels: bool = True
    ) -> Image.Image:
        """
        Visualize segmentation results on image
        
        Args:
            image_path: Path to original image
            elements_info: Elements info dictionary from segmentation
            output_path: Optional output path for saved image
            show_labels: Whether to show text labels on bounding boxes
            
        Returns:
            PIL Image with bounding boxes drawn
        """
        # Load image
        image = Image.open(image_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create a copy for drawing
        vis_image = image.copy()
        draw = ImageDraw.Draw(vis_image)
        
        # Draw text elements
        for elem in elements_info.get('text_elements', []):
            self._draw_bbox(
                draw,
                elem.get('bbox', []),
                self.COLORS['text'],
                label=elem.get('text', '')[:30] if show_labels else None
            )
        
        # Draw icons
        for elem in elements_info.get('icons', []):
            self._draw_bbox(
                draw,
                elem.get('bbox', []),
                self.COLORS['icon'],
                label=elem.get('description', 'Icon')[:30] if show_labels else None
            )
        
        # Draw charts
        for elem in elements_info.get('charts', []):
            self._draw_bbox(
                draw,
                elem.get('bbox', []),
                self.COLORS['chart'],
                label=elem.get('description', 'Chart')[:30] if show_labels else None
            )
        
        # Save if output path provided
        if output_path:
            vis_image.save(output_path, quality=95)
            print(f"Visualization saved to: {output_path}")
        
        return vis_image
    
    def _draw_bbox(
        self,
        draw: ImageDraw.Draw,
        bbox: List[float],
        color: Tuple[int, int, int],
        label: Optional[str] = None
    ):
        """
        Draw bounding box on image
        
        Args:
            draw: PIL ImageDraw object
            bbox: [x, y, width, height]
            color: RGB color tuple
            label: Optional text label
        """
        if len(bbox) != 4:
            return
        
        x, y, width, height = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        
        # Draw rectangle
        draw.rectangle(
            [x, y, x + width, y + height],
            outline=color,
            width=self.line_width
        )
        
        # Draw label if provided
        if label and self.font:
            try:
                # Draw text background
                bbox_text = draw.textbbox((x, y - 20), label, font=self.font)
                draw.rectangle(
                    bbox_text,
                    fill=(255, 255, 255, 200),
                    outline=color,
                    width=1
                )
                # Draw text
                draw.text(
                    (x, y - 20),
                    label,
                    fill=color,
                    font=self.font
                )
            except Exception:
                # Fallback if text drawing fails
                pass
    
    def create_comparison(
        self,
        original_path: str,
        elements_info: Dict,
        output_path: Optional[str] = None
    ) -> Image.Image:
        """
        Create side-by-side comparison (original vs annotated)
        
        Args:
            original_path: Path to original image
            elements_info: Elements info dictionary
            output_path: Optional output path
            
        Returns:
            PIL Image with comparison
        """
        original = Image.open(original_path)
        if original.mode != 'RGB':
            original = original.convert('RGB')
        
        annotated = self.visualize(original_path, elements_info, show_labels=True)
        
        # Create side-by-side image
        width, height = original.size
        comparison = Image.new('RGB', (width * 2 + 20, height), color=(255, 255, 255))
        
        comparison.paste(original, (0, 0))
        comparison.paste(annotated, (width + 20, 0))
        
        # Add labels
        draw = ImageDraw.Draw(comparison)
        if self.font:
            try:
                draw.text((10, 10), "Original", fill=(0, 0, 0), font=self.font)
                draw.text((width + 30, 10), "Annotated", fill=(0, 0, 0), font=self.font)
            except Exception:
                pass
        
        if output_path:
            comparison.save(output_path, quality=95)
            print(f"Comparison saved to: {output_path}")
        
        return comparison


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(
        description='Visualize segmentation results on images'
    )
    parser.add_argument(
        '--image',
        type=str,
        required=True,
        help='Path to input image'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output path for visualized image (default: <image>_visualized.png)'
    )
    parser.add_argument(
        '--comparison',
        action='store_true',
        help='Create side-by-side comparison (original vs annotated)'
    )
    parser.add_argument(
        '--json',
        type=str,
        default=None,
        help='Path to JSON file with segmentation results (if not provided, will run segmentation)'
    )
    parser.add_argument(
        '--no-labels',
        action='store_true',
        help='Do not show labels on bounding boxes'
    )
    parser.add_argument(
        '--show-stats',
        action='store_true',
        help='Show statistics about segmentation results'
    )
    
    args = parser.parse_args()
    
    # Check if image exists
    if not os.path.exists(args.image):
        print(f"❌ Image not found: {args.image}")
        sys.exit(1)
    
    # Load or generate segmentation results
    if args.json and os.path.exists(args.json):
        print(f"Loading segmentation results from: {args.json}")
        with open(args.json, 'r', encoding='utf-8') as f:
            elements_info = json.load(f)
    else:
        print("Running segmentation...")
        try:
            service = ElementSegmentationService()
            elements_info = service.segment_image(args.image)
            print("✓ Segmentation completed")
        except Exception as e:
            print(f"❌ Segmentation failed: {e}")
            sys.exit(1)
    
    # Show statistics if requested
    if args.show_stats:
        stats = ResultProcessor.get_statistics(elements_info)
        print("\n" + "="*60)
        print("Segmentation Statistics:")
        print("="*60)
        print(f"Total text elements: {stats['total_text_elements']}")
        print(f"Total icons: {stats['total_icons']}")
        print(f"Total charts: {stats['total_charts']}")
        print(f"Total elements: {stats['total_elements']}")
        print(f"Text elements with content: {stats['text_elements_with_content']}")
        print(f"Average text length: {stats['average_text_length']:.1f}")
        print("="*60 + "\n")
    
    # Create visualizer
    visualizer = SegmentationVisualizer()
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        base_name = Path(args.image).stem
        output_dir = Path(args.image).parent
        if args.comparison:
            output_path = str(output_dir / f"{base_name}_comparison.png")
        else:
            output_path = str(output_dir / f"{base_name}_visualized.png")
    
    # Create visualization
    if args.comparison:
        print("Creating comparison image...")
        visualizer.create_comparison(args.image, elements_info, output_path)
    else:
        print("Creating visualization...")
        visualizer.visualize(
            args.image,
            elements_info,
            output_path,
            show_labels=not args.no_labels
        )
    
    print(f"✓ Visualization saved to: {output_path}")
    
    # Save JSON if not already saved
    if not args.json:
        json_path = Path(args.image).parent / f"{Path(args.image).stem}_elements.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(elements_info, f, ensure_ascii=False, indent=2)
        print(f"✓ JSON results saved to: {json_path}")


if __name__ == '__main__':
    main()

