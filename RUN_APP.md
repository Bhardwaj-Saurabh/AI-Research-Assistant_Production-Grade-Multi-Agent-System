# Running the AI Research Assistant Streamlit App

## Quick Start

### 1. Install Streamlit (if not already installed)
```bash
pip install streamlit
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### 2. Run the Streamlit App
```bash
streamlit run app.py
```

The app will automatically open in your default browser at `http://localhost:8501`

## Features

### 🎨 Beautiful ChatGPT-like Interface
- Clean, modern design with gradient headers
- User (👤) and Bot (🤖) personas with emojis
- Smooth chat-style interactions
- Aesthetic color scheme (purple gradient theme)

### 💬 Interactive Chat
- Type any research question in the chat input
- Click sample queries for quick testing
- View real-time research progress
- Download full research reports as Markdown

### 📊 Rich Metadata
- Domain classification and confidence
- Source count and quality metrics
- Credibility and coherence scores
- Performance insights and bottlenecks

### 📚 Research History
- Tracks your last 5 research queries
- One-click access to previous research
- Clear chat button to start fresh

### ⚙️ Configuration Display
- Shows current model and settings
- Displays authentication method
- Max iterations and quality thresholds

## Sample Queries

Try these to test the system:
- "What are the latest advances in quantum computing error correction?"
- "How does CRISPR gene editing work in agriculture?"
- "What are the health impacts of microplastics in marine ecosystems?"
- "Explain machine learning applications in drug discovery"

## Customization

### Change Theme Colors
Edit the CSS in `app.py` (lines 25-110) to customize:
- Background colors
- Button gradients
- Message styling
- Font sizes

### Modify Sample Queries
Update the `sample_queries` list in `app.py` (line 160) with your own topics.

### Adjust Config
Edit `.env` file to change:
- `MODEL` - Change the AI model
- `MAX_ITERATIONS` - Adjust research depth
- `QUALITY_THRESHOLD` - Set quality bar

## Troubleshooting

### Port Already in Use
If port 8501 is busy, specify a different port:
```bash
streamlit run app.py --server.port 8502
```

### Authentication Issues
Ensure your `.env` file has either:
- `GOOGLE_API_KEY` for API key authentication
- `PROJECT_ID` and service account for Vertex AI

### Browser Doesn't Open
Manually navigate to: `http://localhost:8501`

## Advanced Options

### Run in Production Mode
```bash
streamlit run app.py --server.headless true
```

### Enable Auto-Reload
```bash
streamlit run app.py --server.runOnSave true
```

### Change Theme
Create `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#667eea"
backgroundColor = "#f7f7f8"
secondaryBackgroundColor = "#ffffff"
textColor = "#262730"
font = "sans serif"
```

## Features to Add (Optional)

- Export chat history to JSON
- Voice input for questions
- Multi-language support
- Save/load research sessions
- Email research reports
- API endpoint for programmatic access

---

**Enjoy researching with your AI Assistant!** 🔬🤖
