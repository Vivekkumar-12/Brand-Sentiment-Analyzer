document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    // Function to add a message to the chat
    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'flex items-start';
        
        const iconDiv = document.createElement('div');
        iconDiv.className = 'flex-shrink-0';
        
        const icon = document.createElement('div');
        icon.className = `w-8 h-8 rounded-full ${isUser ? 'bg-green-500' : 'bg-blue-500'} flex items-center justify-center`;
        icon.innerHTML = `<i class="fas ${isUser ? 'fa-user' : 'fa-robot'} text-white"></i>`;
        
        const messageContent = document.createElement('div');
        messageContent.className = `ml-3 ${isUser ? 'bg-green-100' : 'bg-blue-100'} rounded-lg p-3 max-w-[80%]`;
        
        const messageText = document.createElement('p');
        messageText.className = 'text-sm text-gray-800';
        messageText.textContent = message;
        
        messageContent.appendChild(messageText);
        iconDiv.appendChild(icon);
        messageDiv.appendChild(iconDiv);
        messageDiv.appendChild(messageContent);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Function to analyze sentiment
    async function analyzeSentiment(text) {
        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text }),
            });
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error analyzing sentiment:', error);
            return null;
        }
    }

    // Function to analyze brand sentiment
    async function analyzeBrandSentiment(brand, days = 7) {
        try {
            const response = await fetch('/analyze-brand', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ brand, days }),
            });
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error analyzing brand sentiment:', error);
            return null;
        }
    }

    // Function to get API usage stats
    async function getUsageStats() {
        try {
            const response = await fetch('/usage-stats');
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching usage stats:', error);
            return null;
        }
    }

    // Function to display API usage
    async function displayUsageStats() {
        const stats = await getUsageStats();
        if (stats) {
            const usageMessage = 
                `API Usage Statistics:\n` +
                `- Remaining reads: ${stats.remaining_reads}/100\n` +
                `- Remaining writes: ${stats.remaining_writes}/500\n` +
                `- Next reset: ${new Date(stats.next_reset).toLocaleDateString()}`;
            addMessage(usageMessage);
        }
    }

    // Function to process user input
    async function processUserInput(input) {
        if (!input) {
            console.error('Input is undefined or empty');
            return;
        }

        // Add user message to chat
        addMessage(input, true);

        // Check if it's a text analysis request
        if (input.toLowerCase().includes('analyze this text:')) {
            const text = input.substring(input.toLowerCase().indexOf('analyze this text:') + 'analyze this text:'.length).trim();
            if (!text) {
                addMessage('Please provide text to analyze after "analyze this text:"');
                return;
            }
            const result = await analyzeSentiment(text);
            
            if (result) {
                const sentimentScore = result.sentiment_score || 0;
                const sentiment = sentimentScore > 0.1 ? 'positive' : 
                                sentimentScore < -0.1 ? 'negative' : 'neutral';
                
                const response = `Sentiment Analysis Results:\n` +
                               `Overall Sentiment: ${sentiment}\n` +
                               `Sentiment Score: ${sentimentScore.toFixed(2)}\n` +
                               `Key Phrases: ${result.key_phrases ? result.key_phrases.join(', ') : 'None found'}`;
                
                addMessage(response);
            } else {
                addMessage('Sorry, I encountered an error while analyzing the text. Please try again.');
            }
        }
        // Check if it's a brand analysis request
        else if (input.toLowerCase().includes('check sentiment for brand:')) {
            const brand = input.substring(input.toLowerCase().indexOf('check sentiment for brand:') + 'check sentiment for brand:'.length).trim();
            if (!brand) {
                addMessage('Please provide a brand name after "check sentiment for brand:"');
                return;
            }
            const result = await analyzeBrandSentiment(brand);
            
            if (result) {
                if (result.error) {
                    addMessage(`Error: ${result.error}`);
                    if (result.remaining_reads !== undefined) {
                        addMessage(`Remaining API calls this month: ${result.remaining_reads}`);
                    }
                } else {
                    const overallSentiment = result.sentiment_score || 0;
                    const sentimentLabel = result.overall_tone || 'Neutral';
                    const breakdown = result.breakdown || { positive: 0, negative: 0, neutral: 0 };
                    const sampleQuotes = result.sample_quotes || { most_positive: null, most_negative: null };
                    const aiSummary = result.ai_summary || 'AI summary not available';
                    
                    let response = `Brand Sentiment Analysis for "${brand}":\n\n`;
                    response += `Overall Sentiment: ${overallSentiment.toFixed(2)} (${sentimentLabel})\n`;
                    response += `Total Mentions: ${result.total_mentions || 0}\n\n`;
                    
                    response += `Sentiment Breakdown:\n`;
                    response += `- Positive mentions: ${breakdown.positive}\n`;
                    response += `- Negative mentions: ${breakdown.negative}\n`;
                    response += `- Neutral mentions: ${breakdown.neutral}\n\n`;
                    
                    if (sampleQuotes.most_positive) {
                        response += `Most Positive Comment:\n"${sampleQuotes.most_positive.substring(0, 200)}${sampleQuotes.most_positive.length > 200 ? '...' : ''}"\n\n`;
                    }
                    
                    if (sampleQuotes.most_negative) {
                        response += `Most Negative Comment:\n"${sampleQuotes.most_negative.substring(0, 200)}${sampleQuotes.most_negative.length > 200 ? '...' : ''}"\n\n`;
                    }
                    
                    response += `AI-Generated Analysis:\n${aiSummary}\n\n`;
                    response += `Remaining API calls: ${result.remaining_reads || 0}`;
                    
                    addMessage(response);
                }
            } else {
                addMessage('Sorry, I encountered an error while analyzing the brand. Please try again.');
            }
        }
        // Check API usage
        else if (input.toLowerCase().includes('show usage') || input.toLowerCase().includes('api usage')) {
            await displayUsageStats();
        }
        // Default response for unrecognized input
        else {
            addMessage('I can help you analyze text or brand sentiment. Try saying:\n' +
                      '- "Analyze this text: [your text]"\n' +
                      '- "Check sentiment for brand: [brand name]"\n' +
                      '- "Show usage" to see API limits');
        }
    }

    // Event listeners
    sendButton.addEventListener('click', () => {
        const input = userInput?.value;
        if (!input) {
            console.error('User input element or its value is undefined');
            return;
        }
        const trimmedInput = input.trim();
        if (trimmedInput) {
            processUserInput(trimmedInput);
            userInput.value = '';
        }
    });

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const input = userInput?.value;
            if (!input) {
                console.error('User input element or its value is undefined');
                return;
            }
            const trimmedInput = input.trim();
            if (trimmedInput) {
                processUserInput(trimmedInput);
                userInput.value = '';
            }
        }
    });

    // Show initial usage stats
    displayUsageStats();
}); 