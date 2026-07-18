from typing import Dict, Any


class SEOStage:
    async def execute(self, script: Dict[str, Any]) -> Dict[str, Any]:
        title = script.get("title", "")
        from research.analyzers.seo_analyzer import SEOAnalyzer
        seo_analyzer = SEOAnalyzer()
        seo_result = await seo_analyzer.analyze([
            {"title": title, "views": "1000", "channel": ""},
        ])
        tags = seo_result.get("keywords", []) if isinstance(seo_result, dict) else []
        return {
            "optimized_title": title[:60],
            "description": script.get("hook", "") + f"\n\n{title}",
            "tags": tags[:25] if isinstance(tags, list) else [],
            "hashtags": [f"#{t}" for t in tags[:5]],
            "seo_analysis": seo_result,
        }
