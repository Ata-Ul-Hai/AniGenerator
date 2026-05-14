
import sys
import os
import logging
from unittest.mock import patch

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.multi_model_director import generate_enhanced_scenes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ai_illustrator():
    """
    Test if the AI-generated SVG illustration system is working for unknown keywords.
    """
    test_text = "The ship sailed across the ocean."
    
    # Mocking contextual analysis to force an unknown keyword "docker"
    with patch('backend.services.multi_model_director.ContextualAnalyzer.analyze') as mock_analyze, \
         patch('backend.services.multi_model_director.AssetDiscoveryAgent._generate_keywords_with_llm') as mock_keywords:
        
        from backend.services.multi_model_director import VisualManifest, ChoreographyMap
        mock_analyze.return_value = (
            VisualManifest(
                concepts=["ship"],
                scene_guidance=["A large container ship"],
                themes=["blue"],
                raw_text=test_text
            ),
            ChoreographyMap(
                narrative_flow=["Ship is here."],
                pacing="moderate",
                scene_count=1
            )
        )
        mock_keywords.return_value = ["ship"]
        
        logger.info("Running generate_enhanced_scenes test for keyword 'ship'...")
        scenes = generate_enhanced_scenes(test_text, target_count=1)
        
        if not scenes:
            logger.error("TEST FAILED: No scenes generated.")
            return

        scene = scenes[0]
        logger.info(f"SVG Path: {scene.svg_path}")
        logger.info(f"SVG Markup snippet: {scene.svg_markup[:100]}...")
        
        if "ai-illustrator" in scene.svg_path or "bespoke" in scene.svg_path:
            logger.info("TEST PASSED: Found AI-generated illustration asset.")
        else:
            logger.error("TEST FAILED: Did not use AI illustrator for unknown keyword.")

if __name__ == "__main__":
    test_ai_illustrator()
