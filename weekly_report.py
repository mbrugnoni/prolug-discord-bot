import sqlite3
from datetime import datetime, timedelta
from collections import Counter
import re

class WeeklyReport:
    def __init__(self, db_path='chat_logs.db'):
        self.db_path = db_path

    def get_weekly_stats(self):
        """Get statistics for the last 7 days."""
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get all messages from the last 7 days
                cursor.execute('''
                    SELECT user_id, username, message_content
                    FROM chat_messages
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (seven_days_ago,))

                messages = cursor.fetchall()

                if not messages:
                    return {
                        'total_messages': 0,
                        'top_chatter': None,
                        'top_chatter_count': 0,
                        'most_discussed_topic': 'No messages this week',
                        'all_messages': []
                    }

                # Count messages per user
                user_message_counts = Counter()
                all_message_contents = []

                for msg in messages:
                    user_key = f"{msg['username']}"
                    user_message_counts[user_key] += 1
                    all_message_contents.append(msg['message_content'])

                # Get top chatter
                top_chatter = user_message_counts.most_common(1)[0] if user_message_counts else (None, 0)

                # Get most discussed topic
                most_discussed_topic = self._extract_most_discussed_topic(all_message_contents)

                return {
                    'total_messages': len(messages),
                    'top_chatter': top_chatter[0],
                    'top_chatter_count': top_chatter[1],
                    'most_discussed_topic': most_discussed_topic,
                    'all_messages': all_message_contents
                }

        except sqlite3.Error as e:
            print(f"Database error in weekly report: {e}")
            return None

    def _extract_most_discussed_topic(self, messages):
        """Extract the most discussed topic from messages using keyword analysis."""
        if not messages:
            return "No messages"

        # Combine all messages
        all_text = ' '.join(messages).lower()

        # Remove common words, URLs, mentions, and commands
        all_text = re.sub(r'http[s]?://\S+', '', all_text)  # Remove URLs
        all_text = re.sub(r'<@!?\d+>', '', all_text)  # Remove mentions
        all_text = re.sub(r'!\w+', '', all_text)  # Remove commands

        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'its', 'our', 'their', 'am', 'im', 'dont', 'doesnt',
            'not', 'no', 'yes', 'like', 'just', 'get', 'got', 'about', 'so', 'what',
            'when', 'where', 'who', 'how', 'why', 'if', 'then', 'than', 'some', 'any',
            'all', 'both', 'each', 'few', 'more', 'most', 'other', 'such', 'only', 'own',
            'same', 'than', 'too', 'very', 'one', 'two', 'three', 'lol', 'lmao', 'yeah',
            'ok', 'okay', 'thanks', 'thank', 'thats', 'its', 'youre', 'theyre', 'ive',
            'haha', 'oh', 'well', 'also', 'now', 'see', 'know', 'think', 'want', 'need'
        }

        # Extract words (at least 3 characters)
        words = re.findall(r'\b[a-z]{3,}\b', all_text)

        # Filter out stop words
        meaningful_words = [w for w in words if w not in stop_words]

        if not meaningful_words:
            return "General discussion"

        # Count word frequency
        word_counts = Counter(meaningful_words)

        # Get top 3 most common words
        top_words = word_counts.most_common(3)

        if not top_words:
            return "General discussion"

        # Format the topic based on top words
        if len(top_words) == 1:
            return top_words[0][0].capitalize()
        elif len(top_words) == 2:
            return f"{top_words[0][0].capitalize()} and {top_words[1][0]}"
        else:
            return f"{top_words[0][0].capitalize()}, {top_words[1][0]}, and {top_words[2][0]}"

    async def generate_report_with_ai(self, api_client, messages):
        """Use AI to analyze messages and extract the most discussed topic."""
        if not messages:
            return "No messages this week"

        # Sample messages if there are too many (to avoid token limits)
        sample_size = min(100, len(messages))
        sampled_messages = messages[:sample_size]

        messages_text = '\n'.join(sampled_messages[:50])  # Limit to 50 messages for context

        prompt = f"""Analyze these Discord chat messages from the past week and identify the single most discussed topic or theme in 2-5 words. Be specific and concise.

Messages:
{messages_text}

Most discussed topic (2-5 words):"""

        ai_messages = [
            {"role": "system", "content": "You are a helpful assistant that analyzes chat conversations and identifies main topics. Respond with only the topic name in 2-5 words."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await api_client.make_groq_request(ai_messages)
            if response and len(response) > 0:
                # Clean up the response
                topic = response.strip().strip('"\'')
                return topic if len(topic) < 100 else "Various topics"
        except Exception as e:
            print(f"Error generating AI topic analysis: {e}")

        return "Various topics"

    def format_report(self, stats):
        """Format the weekly statistics into a readable report."""
        if not stats or stats['total_messages'] == 0:
            return "📊 **Weekly Report**\n\nNo messages were logged this week!"

        report = "📊 **Weekly Report - Last 7 Days**\n\n"
        report += f"💬 **Total Messages:** {stats['total_messages']:,}\n"

        if stats['top_chatter']:
            report += f"🏆 **Top Chatter:** {stats['top_chatter']} ({stats['top_chatter_count']} messages)\n"

        report += f"🔥 **Most Discussed Topic:** {stats['most_discussed_topic']}\n"

        return report
