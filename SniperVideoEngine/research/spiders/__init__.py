"""
Dezafira Research Spiders
Spiders para coleta de dados do YouTube.
"""
from .youtube_search import YouTubeSearchSpider
from .channel_analyzer import ChannelAnalyzerSpider
from .video_analyzer import VideoAnalyzerSpider
from .trending_tracker import TrendingTrackerSpider
from .thumbnail_collector import ThumbnailCollectorSpider
from .comment_analyzer import CommentAnalyzerSpider
from .youtube_docs import YouTubeDocsSpider

__all__ = [
    "YouTubeSearchSpider",
    "ChannelAnalyzerSpider",
    "VideoAnalyzerSpider",
    "TrendingTrackerSpider",
    "ThumbnailCollectorSpider",
    "CommentAnalyzerSpider",
    "YouTubeDocsSpider",
]
