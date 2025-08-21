import os
from datetime import datetime, timedelta
import pandas as pd
from textblob import TextBlob
import praw
from dotenv import load_dotenv
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import ssl
import subprocess
import json
import requests

# Create a directory for NLTK data if it doesn't exist
nltk_data_dir = os.path.expanduser('~/nltk_data')
if not os.path.exists(nltk_data_dir):
    os.makedirs(nltk_data_dir)

# Set NLTK data path
nltk.data.path.append(nltk_data_dir)

# Download required NLTK data with SSL verification disabled
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download required NLTK data
try:
    nltk.download('punkt', download_dir=nltk_data_dir)
    nltk.download('stopwords', download_dir=nltk_data_dir)
    nltk.download('brown', download_dir=nltk_data_dir)
    nltk.download('averaged_perceptron_tagger', download_dir=nltk_data_dir)
except Exception as e:
    print(f"Error downloading NLTK data: {str(e)}")
    print("Continuing without some NLTK data. Some features may not work correctly.")

# Download TextBlob corpora
try:
    subprocess.run(['python', '-m', 'textblob.download_corpora'], check=True)
except Exception as e:
    print(f"Error downloading TextBlob corpora: {str(e)}")
    print("Continuing without TextBlob corpora. Some features may not work correctly.")

class RateLimit:
    def __init__(self):
        self.monthly_reads = 0
        self.monthly_writes = 0
        self.last_reset = datetime.now()
        self.MAX_MONTHLY_READS = 1000  # Increased for Reddit
        self.MAX_MONTHLY_WRITES = 500

    def can_read(self):
        self._check_reset()
        return self.monthly_reads < self.MAX_MONTHLY_READS

    def can_write(self):
        self._check_reset()
        return self.monthly_writes < self.MAX_MONTHLY_WRITES

    def increment_read(self):
        self._check_reset()
        if self.monthly_reads < self.MAX_MONTHLY_READS:
            self.monthly_reads += 1
            return True
        return False

    def increment_write(self):
        self._check_reset()
        if self.monthly_writes < self.MAX_MONTHLY_WRITES:
            self.monthly_writes += 1
            return True
        return False

    def _check_reset(self):
        current_time = datetime.now()
        # Reset if we're in a new month
        if current_time.year != self.last_reset.year or current_time.month != self.last_reset.month:
            self.monthly_reads = 0
            self.monthly_writes = 0
            self.last_reset = current_time

    def get_remaining_reads(self):
        self._check_reset()
        return max(0, self.MAX_MONTHLY_READS - self.monthly_reads)

    def get_remaining_writes(self):
        self._check_reset()
        return max(0, self.MAX_MONTHLY_WRITES - self.monthly_writes)

class SentimentAnalyzer:
    def __init__(self):
        load_dotenv()
        self.setup_reddit_api()
        self.rate_limit = RateLimit()
        self.gemini_api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyCMEgh5FzRGLHThmzdrBb6SCN5nlNSjpnE')
        
    def setup_reddit_api(self):
        """Initialize Reddit API client"""
        try:
            client_id = os.getenv('REDDIT_CLIENT_ID')
            client_secret = os.getenv('REDDIT_CLIENT_SECRET')
            user_agent = os.getenv('REDDIT_USER_AGENT')
            
            if not all([client_id, client_secret, user_agent]):
                raise ValueError("Missing required Reddit API credentials")
                
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
            # Test the connection
            self.reddit.user.me()
        except Exception as e:
            print(f"Error initializing Reddit API: {str(e)}")
            self.reddit = None
            raise ValueError(f"Failed to initialize Reddit API: {str(e)}")

    def analyze_text(self, text):
        """
        Analyze sentiment of a given text
        Returns: dict with sentiment scores and analysis
        """
        try:
            blob = TextBlob(text)
            
            # Get overall sentiment
            sentiment_score = blob.sentiment.polarity
            
            # Get sentiment breakdown
            sentiment_breakdown = {
                'positive': len([s for s in blob.sentences if s.sentiment.polarity > 0]),
                'negative': len([s for s in blob.sentences if s.sentiment.polarity < 0]),
                'neutral': len([s for s in blob.sentences if s.sentiment.polarity == 0])
            }
            
            # Extract key phrases (noun phrases)
            key_phrases = list(blob.noun_phrases)
            
            return {
                'sentiment_score': sentiment_score,
                'sentiment_breakdown': sentiment_breakdown,
                'key_phrases': key_phrases,
                'subjectivity': blob.sentiment.subjectivity
            }
        except Exception as e:
            print(f"Error analyzing text: {str(e)}")
            return {
                'sentiment_score': 0,
                'sentiment_breakdown': {'positive': 0, 'negative': 0, 'neutral': 0},
                'key_phrases': [],
                'subjectivity': 0,
                'error': str(e)
            }
    
    def generate_sentiment_summary(self, brand_name, sentiment_data):
        """Generate a detailed sentiment summary using Gemini API"""
        try:
            # Prepare the prompt for Gemini
            prompt = f"""
            Analyze the following sentiment data for {brand_name} and provide a detailed summary:
            
            Overall Sentiment Score: {sentiment_data['sentiment_score']}
            Total Mentions: {sentiment_data['total_mentions']}
            Sentiment Breakdown:
            - Positive: {sentiment_data['breakdown']['positive']}
            - Negative: {sentiment_data['breakdown']['negative']}
            - Neutral: {sentiment_data['breakdown']['neutral']}
            
            Most Positive Comment: {sentiment_data['sample_quotes']['most_positive']}
            Most Negative Comment: {sentiment_data['sample_quotes']['most_negative']}
            
            Please provide:
            1. A concise summary of the overall sentiment
            2. Key themes in the discussions
            3. Notable positive and negative points
            4. Any emerging trends or patterns
            5. Recommendations based on the sentiment analysis
            
            Format the response in a clear, professional manner.
            """
            
            # Use direct API call to Gemini
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={self.gemini_api_key}"
            
            request_body = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                json=request_body
            )
            
            if response.status_code == 200:
                response_data = response.json()
                ai_summary = response_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No summary available')
                
                return {
                    **sentiment_data,
                    'ai_summary': ai_summary
                }
            else:
                print(f"Error from Gemini API: {response.status_code} - {response.text}")
                return sentiment_data
                
        except Exception as e:
            print(f"Error generating AI summary: {str(e)}")
            return sentiment_data

    def analyze_brand_mentions(self, brand_name, days=7):
        """
        Analyze sentiment of brand mentions on Reddit
        Returns: dict with sentiment analysis and trends
        """
        if not self.reddit:
            return {
                'error': 'Reddit API not properly initialized',
                'remaining_reads': 0
            }
            
        if not self.rate_limit.can_read():
            return {
                'error': 'Monthly API read limit reached. Please try again next month.',
                'remaining_reads': self.rate_limit.get_remaining_reads()
            }

        if not brand_name or not isinstance(brand_name, str):
            return {
                'error': 'Invalid brand name provided',
                'remaining_reads': self.rate_limit.get_remaining_reads()
            }

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Search for Reddit posts and comments
        posts = []
        try:
            # Search in relevant subreddits
            subreddits = ['technology', 'business', 'stocks', 'investing', 'marketing']
            for subreddit_name in subreddits:
                if not self.rate_limit.can_read():
                    break
                    
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Search for posts
                for submission in subreddit.search(brand_name, time_filter='week', limit=10):
                    if not self.rate_limit.increment_read():
                        break
                        
                    if submission.created_utc >= start_date.timestamp():
                        # Only include posts that actually mention the brand
                        if brand_name.lower() in submission.title.lower() or brand_name.lower() in submission.selftext.lower():
                            posts.append({
                                'text': submission.title + " " + submission.selftext,
                                'created_at': datetime.fromtimestamp(submission.created_utc),
                                'user': submission.author.name if submission.author else '[deleted]',
                                'type': 'post',
                                'score': submission.score
                            })
                
                # Search for comments
                for submission in subreddit.search(brand_name, time_filter='week', limit=10):
                    if not self.rate_limit.can_read():
                        break
                        
                    submission.comments.replace_more(limit=0)  # Remove MoreComments objects
                    for comment in submission.comments.list():
                        if not self.rate_limit.increment_read():
                            break
                            
                        if comment.created_utc >= start_date.timestamp():
                            # Only include comments that actually mention the brand
                            if brand_name.lower() in comment.body.lower():
                                posts.append({
                                    'text': comment.body,
                                    'created_at': datetime.fromtimestamp(comment.created_utc),
                                    'user': comment.author.name if comment.author else '[deleted]',
                                    'type': 'comment',
                                    'score': comment.score
                                })
                
        except Exception as e:
            print(f"Error fetching Reddit data: {str(e)}")
            return {
                'error': f'Error fetching Reddit data: {str(e)}',
                'remaining_reads': self.rate_limit.get_remaining_reads()
            }
            
        # Analyze sentiment for each post/comment
        results = []
        for post in posts:
            sentiment = self.analyze_text(post['text'])
            results.append({
                'text': post['text'],
                'date': post['created_at'],
                'user': post['user'],
                'type': post['type'],
                'score': post['score'],
                'sentiment_score': sentiment['sentiment_score'],
                'subjectivity': sentiment['subjectivity']
            })
            
        # Convert to DataFrame for analysis
        if not results:
            return {
                'error': 'No Reddit mentions found for the brand in the specified time period',
                'remaining_reads': self.rate_limit.get_remaining_reads()
            }
            
        df = pd.DataFrame(results)
        
        # Calculate daily sentiment trends
        daily_sentiment = df.groupby(df['date'].dt.date)['sentiment_score'].mean()
        # Convert datetime.date keys to strings
        daily_sentiment_dict = {str(date): score for date, score in daily_sentiment.items()}
        
        # Calculate weighted sentiment (considering post/comment scores)
        if df['score'].sum() > 0:
            weighted_sentiment = (df['sentiment_score'] * df['score']).sum() / df['score'].sum()
        else:
            weighted_sentiment = df['sentiment_score'].mean()
        
        # Add sentiment label
        sentiment_label = "Positive" if weighted_sentiment > 0.1 else "Negative" if weighted_sentiment < -0.1 else "Neutral"
        
        # Calculate sentiment breakdown
        positive_mentions = len(df[df['sentiment_score'] > 0.1])
        negative_mentions = len(df[df['sentiment_score'] < -0.1])
        neutral_mentions = len(df) - positive_mentions - negative_mentions
        
        # Get sample quotes
        most_positive = df.nlargest(1, 'sentiment_score')
        most_negative = df.nsmallest(1, 'sentiment_score')
        
        # Generate sentiment summary
        sentiment_summary = {
            'overall_tone': sentiment_label,
            'sentiment_score': weighted_sentiment,
            'total_mentions': len(posts),
            'breakdown': {
                'positive': positive_mentions,
                'negative': negative_mentions,
                'neutral': neutral_mentions
            },
            'sample_quotes': {
                'most_positive': most_positive['text'].iloc[0] if not most_positive.empty else None,
                'most_negative': most_negative['text'].iloc[0] if not most_negative.empty else None
            },
            'daily_sentiment': daily_sentiment_dict,
            'remaining_reads': self.rate_limit.get_remaining_reads()
        }
        
        # After generating sentiment_summary, add AI analysis
        sentiment_summary = self.generate_sentiment_summary(brand_name, sentiment_summary)
        
        return sentiment_summary

    def get_usage_stats(self):
        """Get current API usage statistics"""
        return {
            'monthly_reads': self.rate_limit.monthly_reads,
            'monthly_writes': self.rate_limit.monthly_writes,
            'remaining_reads': self.rate_limit.get_remaining_reads(),
            'remaining_writes': self.rate_limit.get_remaining_writes(),
            'next_reset': (self.rate_limit.last_reset.replace(day=1) + timedelta(days=32)).replace(day=1)
        }

    def get_sentiment_summary(self, brand_name, days=7):
        """
        Get a summary of brand sentiment analysis
        """
        analysis = self.analyze_brand_mentions(brand_name, days)
        if not analysis:
            return "Unable to fetch brand mentions"
            
        sentiment_score = analysis['sentiment_score']
        sentiment_label = "Positive" if sentiment_score > 0.1 else "Negative" if sentiment_score < -0.1 else "Neutral"
        
        return {
            'brand': brand_name,
            'sentiment_label': sentiment_label,
            'sentiment_score': round(sentiment_score, 2),
            'total_mentions': analysis['total_mentions'],
            'trend': "Improving" if sentiment_score > 0 else "Declining" if sentiment_score < 0 else "Stable"
        }

if __name__ == "__main__":
    # Example usage
    analyzer = SentimentAnalyzer()
    
    # Analyze a sample text
    text = "I love this product! It's amazing and works great."
    result = analyzer.analyze_text(text)
    print("\nText Analysis Result:")
    print(f"Sentiment Score: {result['sentiment_score']}")
    print(f"Key Phrases: {result['key_phrases']}")
    
    # Analyze a brand
    brand = "Apple"
    summary = analyzer.get_sentiment_summary(brand)
    print("\nBrand Analysis Result:")
    print(f"Brand: {summary['brand']}")
    print(f"Overall Sentiment: {summary['sentiment_label']}")
    print(f"Sentiment Score: {summary['sentiment_score']}")
    print(f"Total Mentions: {summary['total_mentions']}")
    print(f"Trend: {summary['trend']}") 