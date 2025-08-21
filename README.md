# Brand Sentiment Analyzer

This project analyzes brand sentiment using multiple APIs and natural language processing techniques.

## Features
- Text sentiment analysis using TextBlob
- Social media sentiment analysis (Twitter)
- Brand mention tracking
- Sentiment visualization and reporting

## Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API keys:
```
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
```

3. Run the analyzer:
```bash
python sentiment_analyzer.py
```

## Usage
The sentiment analyzer can be used in two ways:
1. Analyze text directly:
```python
from sentiment_analyzer import SentimentAnalyzer
analyzer = SentimentAnalyzer()
result = analyzer.analyze_text("Your text here")
```

2. Analyze brand mentions on social media:
```python
result = analyzer.analyze_brand_mentions("brand_name", days=7)
```

## Output
The analyzer provides:
- Overall sentiment score (-1 to 1)
- Sentiment breakdown (positive, negative, neutral)
- Key phrases and topics
- Sentiment trends over time 