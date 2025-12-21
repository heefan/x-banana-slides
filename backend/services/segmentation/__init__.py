"""
Segmentation module - modular components for image element segmentation
"""
from .prompts import SegmentationPromptManager, get_prompt_for_background_type, BackgroundType
from .background_handler import BackgroundHandler
from .result_processor import ResultProcessor

__all__ = [
    'SegmentationPromptManager',
    'get_prompt_for_background_type',
    'BackgroundType',
    'BackgroundHandler',
    'ResultProcessor',
]

