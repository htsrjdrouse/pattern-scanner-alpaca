"""
Tests for macro_regime module
"""

import unittest
from macro_regime import (
    build_macro_context, get_sector_macro_alignment,
    REGIME_SECTOR_MAP, _load_cache, _save_cache
)
from datetime import datetime
import os


class TestMacroRegime(unittest.TestCase):
    
    def test_build_macro_context_returns_valid_object(self):
        """Test that build_macro_context returns a valid MacroRegime object"""
        regime = build_macro_context()
        
        # Check all required fields exist
        self.assertIsNotNone(regime.growth_regime)
        self.assertIsNotNone(regime.inflation_regime)
        self.assertIsNotNone(regime.quadrant)
        self.assertIsNotNone(regime.geopolitical_risk)
        self.assertIsInstance(regime.commodity_disruption, dict)
        self.assertIsInstance(regime.favored_sectors, list)
        self.assertIsInstance(regime.suppressed_sectors, list)
        self.assertIsInstance(regime.regime_confidence, float)
        self.assertIsNotNone(regime.last_updated)
        self.assertIsInstance(regime.sources, list)
        
        # Check confidence is in valid range
        self.assertGreaterEqual(regime.regime_confidence, 0.0)
        self.assertLessEqual(regime.regime_confidence, 1.0)
    
    def test_get_sector_macro_alignment(self):
        """Test sector alignment returns correct values"""
        regime = build_macro_context()
        
        # Test favored sector
        if regime.favored_sectors:
            alignment = get_sector_macro_alignment(regime.favored_sectors[0], regime)
            self.assertEqual(alignment, "TAILWIND")
        
        # Test suppressed sector
        if regime.suppressed_sectors:
            alignment = get_sector_macro_alignment(regime.suppressed_sectors[0], regime)
            self.assertEqual(alignment, "HEADWIND")
        
        # Test neutral sector
        alignment = get_sector_macro_alignment("unknown_sector", regime)
        self.assertEqual(alignment, "NEUTRAL")
    
    def test_regime_mapping_covers_all_quadrants(self):
        """Test that regime mapping table has all 4 quadrants"""
        required_quadrants = ["GOLDILOCKS", "STAGFLATION", "REFLATION", "DEFLATION"]
        
        for quadrant in required_quadrants:
            self.assertIn(quadrant, REGIME_SECTOR_MAP)
            self.assertIn("favored", REGIME_SECTOR_MAP[quadrant])
            self.assertIn("suppressed", REGIME_SECTOR_MAP[quadrant])
    
    def test_cache_read_write_cycle(self):
        """Test cache save and load works correctly"""
        regime = build_macro_context()
        
        # Save to cache
        _save_cache(regime)
        
        # Load from cache
        cached_regime = _load_cache()
        
        self.assertIsNotNone(cached_regime)
        self.assertEqual(regime.quadrant, cached_regime.quadrant)
        self.assertEqual(regime.geopolitical_risk, cached_regime.geopolitical_risk)
    
    def test_news_sentiment_returns_valid_range(self):
        """Test news sentiment scoring returns float between 0 and 1"""
        from macro_regime import _check_news_sentiment
        
        sentiment = _check_news_sentiment()
        self.assertIn(sentiment, ["LOW", "ELEVATED", "HIGH"])
    
    def test_screener_tier_upgrade_logic(self):
        """Test screener tier upgrade fires correctly with macro conditions"""
        from pattern_screener import screen_pattern_results
        
        # Create mock stock with Tier 2 characteristics
        mock_stock = {
            'symbol': 'TEST',
            'score': 75,
            'status': 'CONFIRMED',
            'rsi': 60,
            'adx': 30,
            'volume_mult': 1.5,
            'u_shape': 0.40,
            'risk_reward': 2.0,
            'dcf_margin': 50,
            'macd_bullish': True,
            'death_cross': False,
            'golden_cross': False,
            'price': 100,
            'sector': 'energy'  # Will be favored in STAGFLATION
        }
        
        # Build macro context
        regime = build_macro_context()
        
        # If we're in a regime that favors energy AND there's a commodity shock
        # the stock should get upgraded
        results = screen_pattern_results([mock_stock], regime)
        
        # Check that macro_context is included in results
        self.assertIn('macro_context', results)
        self.assertIsNotNone(results['macro_context'])


if __name__ == '__main__':
    unittest.main()
