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
                    SELECT user_id, username, message_content, channel_name
                    FROM chat_messages
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (seven_days_ago,))

                messages = cursor.fetchall()

                if not messages:
                    return {
                        'total_messages': 0,
                        'top_chatter': None,
                        'top_chatter_id': None,
                        'top_chatter_count': 0,
                        'most_discussed_topic': 'No messages this week',
                        'most_active_channel': None,
                        'most_active_channel_count': 0,
                        'all_messages': []
                    }

                # Count messages per user and per channel
                user_message_counts = Counter()
                user_id_to_username = {}
                channel_message_counts = Counter()
                all_message_contents = []

                for msg in messages:
                    user_id = msg['user_id']
                    user_message_counts[user_id] += 1
                    user_id_to_username[user_id] = msg['username']
                    channel_message_counts[msg['channel_name']] += 1
                    all_message_contents.append(msg['message_content'])

                # Get top chatter (by user_id)
                top_chatter = user_message_counts.most_common(1)[0] if user_message_counts else (None, 0)
                top_chatter_id = top_chatter[0]
                top_chatter_name = user_id_to_username.get(top_chatter_id) if top_chatter_id else None

                # Get most active channel
                top_channel = channel_message_counts.most_common(1)[0] if channel_message_counts else (None, 0)

                # Get most discussed topic
                most_discussed_topic = self._extract_most_discussed_topic(all_message_contents)

                return {
                    'total_messages': len(messages),
                    'top_chatter': top_chatter_name,
                    'top_chatter_id': top_chatter_id,
                    'top_chatter_count': top_chatter[1],
                    'most_discussed_topic': most_discussed_topic,
                    'most_active_channel': top_channel[0],
                    'most_active_channel_count': top_channel[1],
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

    def _extract_word_stats(self, messages):
        """Extract word and bigram frequencies from ALL messages for AI analysis."""
        if not messages:
            return {'words': [], 'bigrams': []}

        # Combine all messages
        all_text = ' '.join(messages).lower()

        # Remove URLs, mentions, and commands
        all_text = re.sub(r'http[s]?://\S+', '', all_text)
        all_text = re.sub(r'<@!?\d+>', '', all_text)
        all_text = re.sub(r'!\w+', '', all_text)

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
        meaningful_words = [w for w in words if w not in stop_words]

        # Count single word frequency
        word_counts = Counter(meaningful_words)

        # Extract bigrams (two-word phrases) from meaningful words
        bigrams = []
        for i in range(len(meaningful_words) - 1):
            bigram = f"{meaningful_words[i]} {meaningful_words[i+1]}"
            bigrams.append(bigram)

        bigram_counts = Counter(bigrams)

        return {
            'words': word_counts.most_common(30),
            'bigrams': bigram_counts.most_common(20)
        }

    async def generate_report_with_ai(self, api_client, messages):
        """Use AI to analyze word frequency stats from ALL messages to identify the most discussed topic."""
        if not messages:
            return "No messages this week"

        # Extract word/bigram frequencies from ALL messages
        stats = self._extract_word_stats(messages)

        if not stats['words']:
            return "General discussion"

        # Format stats for AI prompt
        word_stats = ", ".join([f"{w}({c})" for w, c in stats['words'][:30]])
        bigram_stats = ", ".join([f'"{b}"({c})' for b, c in stats['bigrams'][:20]]) if stats['bigrams'] else "none"

        prompt = f"""Based on this word frequency data from a Discord server's weekly chat:

Top words (count): {word_stats}
Top phrases (count): {bigram_stats}
Total messages analyzed: {len(messages)}

Identify the main topic or theme being discussed in 2-5 words. Be specific and concise."""

        ai_messages = [
            {"role": "system", "content": "You are a helpful assistant that interprets word frequency statistics from chat conversations to identify main topics. Respond with only the topic name in 2-5 words."},
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

        if stats.get('top_chatter_id'):
            report += f"🏆 **Top Chatter:** <@{stats['top_chatter_id']}> ({stats['top_chatter_count']} messages)\n"

        if stats.get('most_active_channel'):
            report += f"📢 **Most Active Channel:** #{stats['most_active_channel']} ({stats['most_active_channel_count']} messages)\n"

        report += f"🔥 **Most Discussed Topic:** {stats['most_discussed_topic']}\n"

        return report
