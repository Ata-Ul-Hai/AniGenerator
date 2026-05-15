"""Tests for multi_model_director dataclasses."""

import pytest
from unittest.mock import MagicMock, patch
from hypothesis import given, settings, example
from hypothesis.strategies import (
    text,
    integers,
    lists,
    dictionaries,
    one_of,
    just,
    booleans,
)
from backend.services.multi_model_director import (
    ChoreographyMap,
    ContextualAnalyzer,
    LottieCandidate,
    TimingMetadata,
    ValidationResult,
    VisualManifest,
)


class TestVisualManifest:
    """Tests for VisualManifest dataclass."""

    def test_instantiation_with_valid_data(self):
        """Verify VisualManifest can be instantiated with valid data."""
        manifest = VisualManifest(
            concepts=["concept1", "concept2"],
            themes=["theme1", "theme2"],
            scene_guidance=["guidance1", "guidance2"],
            raw_text="Sample raw text",
        )

        assert manifest.concepts == ["concept1", "concept2"]
        assert manifest.themes == ["theme1", "theme2"]
        assert manifest.scene_guidance == ["guidance1", "guidance2"]
        assert manifest.raw_text == "Sample raw text"

    def test_field_types(self):
        """Verify field types match design specification."""
        manifest = VisualManifest(
            concepts=["concept1"],
            themes=["theme1"],
            scene_guidance=["guidance1"],
            raw_text="raw",
        )

        assert isinstance(manifest.concepts, list)
        assert isinstance(manifest.themes, list)
        assert isinstance(manifest.scene_guidance, list)
        assert isinstance(manifest.raw_text, str)

        # Verify list contents are strings
        assert all(isinstance(c, str) for c in manifest.concepts)
        assert all(isinstance(t, str) for t in manifest.themes)
        assert all(isinstance(g, str) for g in manifest.scene_guidance)

    def test_empty_lists_allowed(self):
        """Verify empty lists are valid for list fields."""
        manifest = VisualManifest(
            concepts=[],
            themes=[],
            scene_guidance=[],
            raw_text="",
        )

        assert manifest.concepts == []
        assert manifest.themes == []
        assert manifest.scene_guidance == []


class TestChoreographyMap:
    """Tests for ChoreographyMap dataclass."""

    def test_instantiation_with_valid_data(self):
        """Verify ChoreographyMap can be instantiated with valid data."""
        choreography = ChoreographyMap(
            scene_count=5,
            narrative_flow=["scene1", "scene2", "scene3"],
            pacing="medium",
        )

        assert choreography.scene_count == 5
        assert choreography.narrative_flow == ["scene1", "scene2", "scene3"]
        assert choreography.pacing == "medium"

    def test_field_types(self):
        """Verify field types match design specification."""
        choreography = ChoreographyMap(
            scene_count=3,
            narrative_flow=["flow1", "flow2"],
            pacing="fast",
        )

        assert isinstance(choreography.scene_count, int)
        assert isinstance(choreography.narrative_flow, list)
        assert isinstance(choreography.pacing, str)

        # Verify list contents are strings
        assert all(isinstance(f, str) for f in choreography.narrative_flow)

    def test_pacing_values(self):
        """Verify pacing accepts valid string values."""
        for pacing in ["fast", "medium", "slow"]:
            choreography = ChoreographyMap(
                scene_count=1,
                narrative_flow=["flow"],
                pacing=pacing,
            )
            assert choreography.pacing == pacing


class TestLottieCandidate:
    """Tests for LottieCandidate dataclass."""

    def test_instantiation_with_valid_data(self):
        """Verify LottieCandidate can be instantiated with valid data."""
        candidate = LottieCandidate(
            url="https://example.com/lottie.json",
            title="Sample Animation",
            duration_ms=2000,
            preview_url="https://example.com/preview.png",
            lottie_json={"v": "5.5.7", "fr": 30},
        )

        assert candidate.url == "https://example.com/lottie.json"
        assert candidate.title == "Sample Animation"
        assert candidate.duration_ms == 2000
        assert candidate.preview_url == "https://example.com/preview.png"
        assert candidate.lottie_json == {"v": "5.5.7", "fr": 30}

    def test_field_types(self):
        """Verify field types match design specification."""
        candidate = LottieCandidate(
            url="https://example.com/lottie.json",
            title="Title",
            duration_ms=1000,
            preview_url="https://example.com/preview.png",
            lottie_json={},
        )

        assert isinstance(candidate.url, str)
        assert isinstance(candidate.title, str)
        assert isinstance(candidate.duration_ms, int)
        assert isinstance(candidate.preview_url, str)
        assert isinstance(candidate.lottie_json, dict)

    def test_empty_lottie_json_allowed(self):
        """Verify empty dict is valid for lottie_json field."""
        candidate = LottieCandidate(
            url="https://example.com/lottie.json",
            title="Title",
            duration_ms=500,
            preview_url="https://example.com/preview.png",
            lottie_json={},
        )

        assert candidate.lottie_json == {}


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_instantiation_with_valid_data(self):
        """Verify ValidationResult can be instantiated with valid data."""
        result = ValidationResult(
            score=0.85,
            is_valid=True,
            reason="High relevance score",
        )

        assert result.score == 0.85
        assert result.is_valid is True
        assert result.reason == "High relevance score"

    def test_field_types(self):
        """Verify field types match design specification."""
        result = ValidationResult(
            score=0.5,
            is_valid=False,
            reason="test",
        )

        assert isinstance(result.score, float)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.reason, str)

    def test_score_boundaries(self):
        """Verify score accepts float values across valid range."""
        for score in [0.0, 0.5, 1.0]:
            result = ValidationResult(
                score=score,
                is_valid=False,
                reason="test",
            )
            assert result.score == score


class TestTimingMetadata:
    """Tests for TimingMetadata dataclass."""

    def test_instantiation_with_valid_data(self):
        """Verify TimingMetadata can be instantiated with valid data."""
        timing = TimingMetadata(
            draw_duration_ms=1000,
            hold_ms=500,
            draw_start_ms=0,
        )

        assert timing.draw_duration_ms == 1000
        assert timing.hold_ms == 500
        assert timing.draw_start_ms == 0

    def test_field_types(self):
        """Verify field types match design specification."""
        timing = TimingMetadata(
            draw_duration_ms=2000,
            hold_ms=1000,
            draw_start_ms=0,
        )

        assert isinstance(timing.draw_duration_ms, int)
        assert isinstance(timing.hold_ms, int)
        assert isinstance(timing.draw_start_ms, int)

    def test_draw_start_ms_always_zero(self):
        """Verify draw_start_ms is always 0 as per design."""
        timing = TimingMetadata(
            draw_duration_ms=1500,
            hold_ms=300,
            draw_start_ms=0,
        )

        assert timing.draw_start_ms == 0


class TestContextualAnalyzerFallback:
    """Tests for ContextualAnalyzer fallback behavior on API failure."""

    def test_contextual_analyzer_fallback_on_api_failure(self):
        """Verify ContextualAnalyzer returns valid fallback manifest when Groq API fails.
        
        This test mocks the Groq client to raise RuntimeError and verifies that
        a valid minimal VisualManifest is returned with concepts derived from text chunking.
        """
        # Create analyzer with mocked settings
        with patch('backend.services.multi_model_director.get_settings') as mock_settings:
            mock_settings.return_value.groq_api_key = "test-key"
            mock_settings.return_value.max_scenes = 5
            
            analyzer = ContextualAnalyzer()
            
            # Mock the client to raise RuntimeError (simulating API failure)
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = RuntimeError("API failure")
            analyzer._client = mock_client
            
            # Test text chunk with multiple sentences
            test_text = "The cat sat on the mat. It was a sunny day. Birds were singing."
            
            # Call analyze - should fall back to text chunking
            manifest, choreography = analyzer.analyze(test_text)
            
            # Assert that a valid VisualManifest is returned
            assert isinstance(manifest, VisualManifest)
            assert isinstance(manifest.concepts, list)
            assert len(manifest.concepts) > 0
            
            # Verify concepts are derived from text chunking (sentence splitting)
            expected_concepts = ["The cat sat on the mat.", "It was a sunny day.", "Birds were singing."]
            assert manifest.concepts == expected_concepts
            
            # Verify other fields
            assert manifest.themes == []
            assert manifest.scene_guidance == []
            assert manifest.raw_text == test_text
            
            # Verify ChoreographyMap is also returned
            assert isinstance(choreography, ChoreographyMap)
            assert choreography.scene_count == len(manifest.concepts)
            assert choreography.narrative_flow == manifest.concepts
            assert choreography.pacing == "medium"
class TestAssetDiscoveryFallback:
    """Tests for AssetDiscoveryAgent fallback chain."""

    @patch('backend.services.multi_model_director.AssetDiscoveryAgent.search_lottiefiles')
    @patch('backend.services.multi_model_director.AssetDiscoveryAgent.parse_lottie_json')
    @patch('backend.services.multi_model_director.fetch_icon_svg')
    def test_asset_discovery_lottie_to_iconify_fallback(
        self, mock_fetch_icon, mock_parse_lottie, mock_search_lottie
    ):
        """Verify LottieFiles returns empty, Iconify fallback is called.
        
        This test mocks LottieFiles search to return empty results and mocks
        Iconify to return a valid SVG. Verifies that the fallback chain works
        correctly - when Lottie fails, Iconify should be tried.
        """
        from backend.services.multi_model_director import AssetDiscoveryAgent
        
        # Mock LottieFiles to return empty list (no results)
        mock_search_lottie.return_value = []
        
        # Mock Iconify to return a valid SVG
        mock_fetch_icon.return_value = '<svg xmlns="http://www.w3.org/2000/svg"><path d="test"/></svg>'
        
        # Create agent and call discover_assets
        agent = AssetDiscoveryAgent()
        result = agent.discover_assets("test scene with visual elements", scene_id=1)
        
        # Verify LottieFiles was called
        mock_search_lottie.assert_called()
        
        # Verify Iconify fallback was attempted (fetch_icon_svg was called)
        mock_fetch_icon.assert_called()
        
        # Verify result is the SVG string from Iconify
        assert result is not None
        assert isinstance(result, str)
        assert '<svg' in result

    @patch('backend.services.multi_model_director.AssetDiscoveryAgent.search_lottiefiles')
    @patch('backend.services.multi_model_director.AssetDiscoveryAgent.parse_lottie_json')
    @patch('backend.services.multi_model_director.fetch_icon_svg')
    def test_asset_discovery_iconify_to_template_fallback(
        self, mock_fetch_icon, mock_parse_lottie, mock_search_lottie
    ):
        """Verify both LottieFiles and Iconify fail, return None for template fallback.
        
        This test mocks both LottieFiles search to return empty and Iconify
        to return None. Verifies that None is returned when both fallbacks fail,
        which should trigger the hardcoded template fallback.
        """
        from backend.services.multi_model_director import AssetDiscoveryAgent
        
        # Mock LottieFiles to return empty list (no results)
        mock_search_lottie.return_value = []
        
        # Mock Iconify to return None (fallback failure)
        mock_fetch_icon.return_value = None
        
        # Create agent and call discover_assets
        agent = AssetDiscoveryAgent()
        result = agent.discover_assets("abstract concept visualization", scene_id=1)
        
        # Verify LottieFiles was called
        mock_search_lottie.assert_called()
        
        # Verify Iconify fallback was attempted
        mock_fetch_icon.assert_called()
        
        # Verify result is None when both fallbacks fail
        assert result is None


# Feature: multi-model-animation-director, Property 10: LottieFiles result structure
class TestLottieFilesResultStructure:
    """Property-based tests for LottieFiles result structure (Property 10).
    
    Validates: Requirements 14.3
    
    Property 10: LottieFiles result structure
    For any non-empty LottieFiles search response, every element in the 
    returned list must be a dict containing the keys url, title, duration_ms, 
    and preview_url.
    """

    @given(
        keywords=text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        api_url=text(min_size=0, max_size=100),
        api_title=text(min_size=0, max_size=100),
        api_duration=integers(min_value=0),
        api_preview=text(min_size=0, max_size=100),
    )
    @settings(max_examples=100)
    def test_lottiefiles_result_structure_property(self, keywords, api_url, api_title, api_duration, api_preview):
        """Property test: Every dict in LottieFiles result must have required keys.
        
        This test generates random mock LottieFiles API responses with various
        field name formats and verifies that the search function normalizes 
        all responses to contain url, title, duration_ms, and preview_url.
        
        Validates: Requirements 14.3
        """
        from backend.services.multi_model_director import AssetDiscoveryAgent
        from unittest.mock import patch, MagicMock
        
        # Create mock responses with various LottieFiles API field name formats
        # The API may return different field names like:
        # url/downloadUrl/jsonUrl, title/name, duration/durationMs, preview/previewUrl/thumbnailUrl
        mock_results_variations = [
            # Standard format
            {"url": api_url, "title": api_title, "duration": api_duration, "preview": api_preview},
            # Alternate format with downloadUrl
            {"downloadUrl": api_url, "name": api_title, "durationMs": api_duration, "previewUrl": api_preview},
            # JSON URL format
            {"jsonUrl": api_url, "title": api_title, "duration": api_duration, "thumbnailUrl": api_preview},
            # Mixed format
            {"url": api_url, "name": api_title, "durationMs": api_duration, "preview": api_preview},
        ]
        
        required_keys = {"url", "title", "duration_ms", "preview_url"}
        
        for mock_result in mock_results_variations:
            mock_response_data = {"results": [mock_result]}
            
            with patch('backend.services.multi_model_director.requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value = mock_response
                
                agent = AssetDiscoveryAgent()
                search_results = agent.search_lottiefiles(keywords)
                
                # Property: The result must contain the required keys
                if search_results:
                    for result in search_results:
                        result_keys = set(result.keys())
                        assert required_keys.issubset(result_keys), (
                            f"Result missing required keys. "
                            f"Expected at least {required_keys}, got {result_keys}"
                        )
                        
                        # Verify types
                        assert isinstance(result["url"], str), f"url must be string, got {type(result['url'])}"
                        assert isinstance(result["title"], str), f"title must be string, got {type(result['title'])}"
                        assert isinstance(result["duration_ms"], int), f"duration_ms must be int, got {type(result['duration_ms'])}"
                        assert isinstance(result["preview_url"], str), f"preview_url must be string, got {type(result['preview_url'])}"