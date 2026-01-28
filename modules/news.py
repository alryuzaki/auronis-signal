import logging
import datetime
import feedparser
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class NewsAggregator:
    def __init__(self):
        self.last_news_links = set() # Cache to avoid duplicates
        self.feeds = {
            'crypto': [
                'https://cointelegraph.com/rss',
                'https://www.coindesk.com/arc/outboundfeeds/rss/'
            ],
            'stocks': [
                'https://finance.yahoo.com/news/rssindex',
                'https://feeds.content.dowjones.io/public/rss/mw/topstories'
            ],
            'forex': [
                'https://www.dailyfx.com/feeds/market-news',
                'https://www.investing.com/rss/news_1.rss' # General forex news
            ],
            'gold': [
                'https://www.kitco.com/rss/latest/commodities',
                'https://www.investing.com/rss/commodities_Metals.rss'
            ]
        }

    async def check_and_send_news(self, context: ContextTypes.DEFAULT_TYPE):
        """
        Fetch news and send to respective groups.
        Context job data should contain group IDs:
        {'crypto': id, 'stocks': id, 'forex': id, 'gold': id}
        """
        groups = context.job.data.get('groups', {})
        
        for category, urls in self.feeds.items():
            group_id = groups.get(category)
            if not group_id:
                continue

            for url in urls:
                try:
                    feed = feedparser.parse(url)
                    # Check the latest 3 entries
                    for entry in feed.entries[:3]:
                        if entry.link in self.last_news_links:
                            continue
                            
                        # Post News
                        msg = self.format_news_message(entry, category)
                        await context.bot.send_message(chat_id=group_id, text=msg, parse_mode='HTML')
                        
                        # Cache
                        self.last_news_links.add(entry.link)
                        # Keep cache small
                        if len(self.last_news_links) > 500:
                            self.last_news_links = set(list(self.last_news_links)[-200:])
                            
                except Exception as e:
                    logger.error(f"Error fetching news for {category} from {url}: {e}")

    def format_news_message(self, entry, category):
        # Icons
        icons = {
            'crypto': '₿',
            'stocks': '📈',
            'forex': '💱',
            'gold': '🥇'
        }
        icon = icons.get(category, '📰')
        
        title = entry.title
        link = entry.link
        
        # Simple HTML format
        msg = (
            f"{icon} <b>{category.upper()} NEWS</b>\n\n"
            f"<b>{title}</b>\n\n"
            f"<a href='{link}'>Read More</a>"
        )
        return msg
