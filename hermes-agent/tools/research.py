#!/usr/bin/env python3
"""
Dezafira Tool: Research Niche
Executado pelo Nous Hermes Agent via Shell.
"""
import sys
import os
import asyncio
import json

sys.path.insert(0, '/app')

def main():
    if len(sys.argv) < 2:
        print("Uso: python research.py <theme>")
        print("  theme: nicho/tema para pesquisar")
        sys.exit(1)

    theme = sys.argv[1]
    print(f"[Dezafira] Pesquisando nicho: {theme}")

    try:
        from research.engine import ResearchEngine

        engine = ResearchEngine()
        result = asyncio.run(engine.research_niche(theme))

        print(f"[Dezafira] Resultado:")
        print(f"  Score: {result.niche_score}/100")
        print(f"  Competição: {result.competition_level}")
        print(f"  Vídeos trending: {len(result.trending_videos)}")
        print(f"  Padrões de título: {result.title_patterns[:3]}")

        # Resultado para Nous Hermes
        output = {
            "success": True,
            "theme": theme,
            "niche_score": result.niche_score,
            "competition": result.competition_level,
            "trending_count": len(result.trending_videos),
            "title_patterns": result.title_patterns[:5],
            "trending_videos": [
                {"title": v.title, "views": v.views}
                for v in result.trending_videos[:5]
            ]
        }
        print(json.dumps(output, ensure_ascii=False))

    except Exception as e:
        print(f"[Dezafira] ERRO: {e}", file=sys.stderr)
        output = {"success": False, "error": str(e)}
        print(json.dumps(output))
        sys.exit(1)

if __name__ == "__main__":
    main()
