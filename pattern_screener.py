"""
Pattern scanner result screener with tier-based filtering.
Applies systematic filters to identify high-conviction setups.
"""

def screen_pattern_results(results, macro_context=None):
    """
    Screen pattern scanner results into tiers.
    
    Args:
        results: List of dicts with pattern scanner output
        macro_context: Optional MacroRegime object for macro overlay
        
    Returns:
        Dict with tier1, tier2, tier3, exceptions, excluded
    """
    tier1 = []
    tier2 = []
    tier3 = []
    exceptions = []
    excluded = []
    
    for stock in results:
        # Extract fields
        symbol = stock.get('symbol', '')
        score = stock.get('score', 0)
        status = stock.get('status', '')
        rsi = stock.get('rsi', 0)
        adx = stock.get('adx', 0)
        volume_mult = stock.get('volume_mult', 0)
        u_shape = stock.get('u_shape', 0)
        risk_reward = stock.get('risk_reward', 0)
        dcf_margin = stock.get('dcf_margin', None)
        macd_bullish = stock.get('macd_bullish', False)
        death_cross = stock.get('death_cross', False)
        golden_cross = stock.get('golden_cross', False)
        price = stock.get('price', 0)
        sector = stock.get('sector', '')
        
        # Macro overlay flags
        macro_tailwind = False
        macro_headwind = False
        geo_risk_high = False
        commodity_shock = False
        
        if macro_context:
            from macro_regime import get_sector_macro_alignment, COMMODITY_SECTOR_MAP
            
            alignment = get_sector_macro_alignment(sector, macro_context)
            macro_tailwind = (alignment == "TAILWIND")
            macro_headwind = (alignment == "HEADWIND")
            geo_risk_high = (macro_context.geopolitical_risk == "HIGH")
            
            # Check commodity shock alignment
            for commodity, severity in macro_context.commodity_disruption.items():
                if severity == "HIGH":
                    affected_sectors = COMMODITY_SECTOR_MAP.get(commodity, [])
                    if sector in affected_sectors:
                        commodity_shock = True
                        break
        
        # RSI ceiling adjustment for commodity shocks
        rsi_ceiling = 82 if commodity_shock else 80
        
        # Automatic disqualifiers
        if (rsi > rsi_ceiling or rsi < 45 or adx < 10 or u_shape < 0.05 or 
            risk_reward < 1.0 or death_cross or
            (status == "FORMING" and score < 50)):
            reason = []
            if rsi > rsi_ceiling: reason.append(f"RSI > {rsi_ceiling} (overbought)")
            if rsi < 45: reason.append("RSI < 45 (weak momentum)")
            if adx < 10: reason.append("ADX < 10 (no trend)")
            if u_shape < 0.05: reason.append("U-shape < 0.05 (distorted)")
            if risk_reward < 1.0: reason.append("R:R < 1.0")
            if death_cross: reason.append("☠️ Death Cross")
            if status == "FORMING" and score < 50: reason.append("Too early")
            
            excluded.append({**stock, 'exclusion_reason': ', '.join(reason)})
            continue
        
        # Add flags
        flags = []
        if rsi > 75: flags.append("🔴 OVERBOUGHT")
        if volume_mult >= 2.0: flags.append("⚡ VOLUME SPIKE")
        if golden_cross: flags.append("⭐ GOLDEN CROSS")
        if dcf_margin and dcf_margin > 200: flags.append("💰 DEEP VALUE")
        if u_shape >= 0.80: flags.append("📐 PERFECT CUP")
        
        # Macro flags
        if macro_tailwind: flags.append("🌍 MACRO TAILWIND")
        if macro_headwind: flags.append("⚠️ MACRO HEADWIND")
        if geo_risk_high: flags.append("🚨 GEO RISK HIGH")
        if commodity_shock: flags.append("🛢️ COMMODITY SHOCK")
        
        stock_with_flags = {**stock, 'flags': flags}
        
        # Check DCF validity
        dcf_valid = dcf_margin is not None and dcf_margin > 0
        
        # Determine initial tier
        initial_tier = None
        
        # TIER 1: HIGH CONVICTION
        if (volume_mult >= 2.0 and adx >= 25 and 50 <= rsi <= 70 and
            u_shape >= 0.40 and risk_reward >= 1.5 and dcf_valid and macd_bullish):
            initial_tier = 1
        # TIER 2: STRONG SETUP
        elif (volume_mult >= 1.0 and adx >= 25 and 50 <= rsi <= 70 and
            u_shape >= 0.35 and risk_reward >= 1.5 and dcf_valid and macd_bullish):
            initial_tier = 2
        # TIER 3: WATCHLIST
        elif (volume_mult >= 0.5 and adx >= 25 and 50 <= rsi <= 70 and
            u_shape >= 0.40 and risk_reward >= 1.5 and macd_bullish):
            initial_tier = 3
        
        # Macro boost/downgrade logic
        if initial_tier and macro_context:
            # Upgrade: MACRO TAILWIND + commodity shock
            if macro_tailwind and commodity_shock and initial_tier > 1:
                initial_tier -= 1  # Tier 2 → 1, Tier 3 → 2
            # Downgrade: MACRO HEADWIND
            elif macro_headwind and initial_tier < 3:
                initial_tier += 1  # Tier 1 → 2, Tier 2 → 3
        
        # Assign to tier
        if initial_tier == 1:
            tier1.append(stock_with_flags)
        elif initial_tier == 2:
            tier2.append(stock_with_flags)
        elif initial_tier == 3:
            tier3.append(stock_with_flags)
        elif adx >= 35:
            # NOTABLE EXCEPTIONS: Strong ADX but fails 1-2 criteria
            fails = []
            if volume_mult < 2.0: fails.append("Volume < 2.0x")
            if not (50 <= rsi <= 70): fails.append(f"RSI {rsi:.0f} (need 50-70)")
            if u_shape < 0.40: fails.append(f"U-shape {u_shape:.2f} (need 0.40+)")
            if risk_reward < 1.5: fails.append(f"R:R {risk_reward:.1f} (need 1.5+)")
            if not dcf_valid: fails.append("DCF negative/N/A")
            if not macd_bullish: fails.append("MACD not bullish")
            
            if len(fails) <= 2:
                exceptions.append({**stock_with_flags, 'fails': fails})
    
    return {
        'tier1': tier1,
        'tier2': tier2,
        'tier3': tier3,
        'exceptions': exceptions,
        'excluded': excluded,
        'summary': {
            'total_scanned': len(results),
            'tier1_count': len(tier1),
            'tier2_count': len(tier2),
            'tier3_count': len(tier3),
            'exceptions_count': len(exceptions),
            'excluded_count': len(excluded)
        },
        'macro_context': macro_context
    }


def format_screener_output(screened):
    """Format screened results as readable text."""
    output = []
    summary = screened['summary']
    
    output.append("=" * 80)
    output.append("PATTERN SCANNER SCREENING RESULTS")
    output.append("=" * 80)
    output.append(f"Total stocks scanned: {summary['total_scanned']}")
    output.append(f"Passed screening: {summary['tier1_count'] + summary['tier2_count'] + summary['tier3_count']}")
    output.append("")
    
    # TIER 1
    output.append("🥇 TIER 1: HIGH CONVICTION")
    output.append("All quality filters passed. Immediate candidates for deeper analysis.")
    output.append("-" * 80)
    if screened['tier1']:
        for s in screened['tier1']:
            flags_str = ' '.join(s['flags']) if s['flags'] else ''
            output.append(f"{s['symbol']:<8} ${s['price']:>7.2f}  ADX:{s['adx']:>5.1f}  RSI:{s['rsi']:>5.1f}  "
                         f"Vol:{s['volume_mult']:>4.1f}x  U:{s['u_shape']:>4.2f}  R:R:{s['risk_reward']:>4.1f}  "
                         f"DCF:{s.get('dcf_margin', 0):>5.0f}%  {flags_str}")
    else:
        output.append("No stocks meet Tier 1 criteria")
    output.append("")
    
    # TIER 2
    output.append("🥈 TIER 2: STRONG SETUP")
    output.append("Strong trend with good pattern, moderate volume — worth monitoring.")
    output.append("-" * 80)
    if screened['tier2']:
        for s in screened['tier2']:
            flags_str = ' '.join(s['flags']) if s['flags'] else ''
            output.append(f"{s['symbol']:<8} ${s['price']:>7.2f}  ADX:{s['adx']:>5.1f}  RSI:{s['rsi']:>5.1f}  "
                         f"Vol:{s['volume_mult']:>4.1f}x  U:{s['u_shape']:>4.2f}  R:R:{s['risk_reward']:>4.1f}  "
                         f"DCF:{s.get('dcf_margin', 0):>5.0f}%  {flags_str}")
    else:
        output.append("No stocks meet Tier 2 criteria")
    output.append("")
    
    # TIER 3
    output.append("🥉 TIER 3: WATCHLIST")
    output.append("Good pattern quality and trend, waiting for volume confirmation.")
    output.append("-" * 80)
    if screened['tier3']:
        for s in screened['tier3']:
            flags_str = ' '.join(s['flags']) if s['flags'] else ''
            output.append(f"{s['symbol']:<8} ${s['price']:>7.2f}  ADX:{s['adx']:>5.1f}  RSI:{s['rsi']:>5.1f}  "
                         f"Vol:{s['volume_mult']:>4.1f}x  U:{s['u_shape']:>4.2f}  R:R:{s['risk_reward']:>4.1f}  "
                         f"{flags_str}")
    else:
        output.append("No stocks meet Tier 3 criteria")
    output.append("")
    
    # EXCEPTIONS
    if screened['exceptions']:
        output.append("⚡ NOTABLE EXCEPTIONS")
        output.append("Strong ADX but fails 1-2 criteria. Worth watching.")
        output.append("-" * 80)
        for s in screened['exceptions']:
            fails_str = ', '.join(s['fails'])
            output.append(f"{s['symbol']:<8} ADX:{s['adx']:>5.1f}  Fails: {fails_str}")
        output.append("")
    
    # SUMMARY
    output.append("📊 SCAN SUMMARY")
    output.append("-" * 80)
    output.append(f"Tier 1 count: {summary['tier1_count']} — Ready to trade")
    output.append(f"Tier 2 count: {summary['tier2_count']} — Monitor for volume")
    output.append(f"Tier 3 count: {summary['tier3_count']} — On radar")
    output.append(f"Notable Exceptions: {summary['exceptions_count']} — Watch for triggers")
    output.append(f"Excluded: {summary['excluded_count']} — Failed disqualifiers")
    output.append("")
    
    # Market observation
    if summary['tier1_count'] == 0:
        output.append("🚫 MARKET OBSERVATION:")
        output.append("No high-conviction setups available. Current conditions do not support")
        output.append("aggressive entries. Most patterns lack volume confirmation or show")
        output.append("overbought conditions. Wait for better risk/reward opportunities.")
    elif summary['tier1_count'] < 5:
        output.append("⚠️ MARKET OBSERVATION:")
        output.append("Limited high-conviction opportunities. Be selective and wait for")
        output.append("volume confirmation before entering positions.")
    else:
        output.append("✅ MARKET OBSERVATION:")
        output.append("Multiple high-quality setups available with strong volume and trend")
        output.append("confirmation. Market conditions support pattern-based entries.")
    
    # Macro regime summary
    macro_context = screened.get('macro_context')
    if macro_context:
        output.append("")
        output.append("🌍 MACRO REGIME CONTEXT")
        output.append("-" * 80)
        output.append(f"Quadrant: {macro_context.quadrant}  |  Geopolitical Risk: {macro_context.geopolitical_risk}")
        if macro_context.commodity_disruption:
            disruptions = ', '.join([f"{k.upper()}:{v}" for k, v in macro_context.commodity_disruption.items()])
            output.append(f"Commodity Disruptions: {disruptions}")
        output.append(f"Favored Sectors: {', '.join(macro_context.favored_sectors[:5])}")
    
    output.append("=" * 80)
    
    return '\n'.join(output)
