
import sys
import os
import json
import logging

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.multi_model_director import generate_enhanced_scenes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from unittest.mock import MagicMock, patch
from backend.services.multi_model_director import generate_enhanced_scenes, IllustrationCandidate

def test_pipeline_fetching():
    """
    Test if the illustration discovery and fetching is working properly.
    """
    test_text = "In this scene, a developer is coding a secure blockchain network."
    
    # Mocking dependencies to avoid needing API keys
    with patch('backend.services.multi_model_director.ContextualAnalyzer.analyze') as mock_analyze, \
         patch('backend.services.multi_model_director.AssetDiscoveryAgent._generate_keywords_with_llm') as mock_keywords:
        
        # Mock Contextual Analysis
        from backend.services.multi_model_director import VisualManifest, ChoreographyMap
        mock_analyze.return_value = (
            VisualManifest(
                concepts=["coding", "security"],
                scene_guidance=["A developer coding", "Secure network"],
                themes=["modern blue"],
                raw_text=test_text
            ),
            ChoreographyMap(
                narrative_flow=["Welcome to the world of coding.", "Security is paramount."],
                pacing="moderate",
                scene_count=2
            )
        )
        
        # Mock Keyword Generation
        mock_keywords.side_effect = [["coding"], ["security"]]
        
        logger.info("Running generate_enhanced_scenes test (with MOCK LLM)...")
        scenes = generate_enhanced_scenes(test_text, max_scenes=2)
    
    if not scenes:
        logger.error("TEST FAILED: No scenes generated.")
        return
    
    logger.info(f"Generated {len(scenes)} scenes.")
    
    for i, scene in enumerate(scenes):
        logger.info(f"--- Scene {scene.scene_id} ---")
        logger.info(f"Narration: {scene.narration}")
        logger.info(f"SVG Path: {scene.svg_path}")
        
        # Check if svg_markup is valid
        if not scene.svg_markup:
            logger.error(f"TEST FAILED: Scene {scene.scene_id} has no SVG markup.")
        elif "illustration://" in scene.svg_path:
            logger.info(f"TEST PASSED: Found illustration asset with markup.")
        elif "inline://" in scene.svg_path:
            logger.info(f"TEST PASSED: Found Iconify/Template fallback with markup.")
        
        # Verify it's not a Lottie URL (which we removed)
        if "lottiefiles" in scene.svg_path or "lottie://" in scene.svg_path:
            logger.error(f"TEST FAILED: Found deprecated Lottie reference.")

    logger.info("Test completed successfully.")

if __name__ == "__main__":
    test_pipeline_fetching()
