"""
AI Research Assistant - Streamlit App
Beautiful ChatGPT-like interface for research queries
"""

import streamlit as st
import asyncio
import os
from datetime import datetime
from google import genai
from utils.config import config
from agents.orchestrator import execute_research_workflow, generate_research_report

# Page configuration
st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for ChatGPT-like aesthetic
st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #f7f7f8;
    }

    /* Chat message containers */
    .user-message {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .bot-message {
        background-color: #f7f7f8;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        border: 1px solid #e5e5e5;
    }

    /* Persona styling */
    .persona {
        font-size: 1.5rem;
        margin-right: 0.5rem;
    }

    /* Header styling */
    .app-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }

    /* Metrics styling */
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        border: none;
        font-weight: 600;
    }

    .stButton>button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }

    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #ffffff;
    }

    /* Status messages */
    .status-info {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }

    .status-success {
        background-color: #e8f5e9;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
    }

    .status-warning {
        background-color: #fff3e0;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ff9800;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'research_history' not in st.session_state:
    st.session_state.research_history = []

def initialize_client():
    """Initialize GenAI client with proper authentication."""
    try:
        # Try API key first (easiest)
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

        if api_key:
            client = genai.Client(api_key=api_key)
            return client, "API Key"
        elif config.project_id:
            # Use Vertex AI
            client = genai.Client(
                vertexai=True,
                project=config.project_id,
                location=config.location
            )
            return client, "Vertex AI"
        else:
            return None, "No authentication"
    except Exception as e:
        st.error(f"Failed to initialize client: {e}")
        return None, str(e)

def format_message(role, content, metadata=None):
    """Format a chat message with persona emoji."""
    if role == "user":
        emoji = "👤"
        css_class = "user-message"
    else:
        emoji = "🤖"
        css_class = "bot-message"

    st.markdown(f"""
    <div class="{css_class}">
        <span class="persona">{emoji}</span>
        <strong>{role.title()}</strong>
        <div style="margin-top: 0.5rem;">{content}</div>
    </div>
    """, unsafe_allow_html=True)

    if metadata:
        with st.expander("📊 Research Metadata"):
            st.json(metadata)

async def process_research_query(client, query):
    """Process a research query through the workflow."""
    try:
        # Execute the research workflow
        workflow_results = await execute_research_workflow(
            client=client,
            query=query,
            max_iterations=config.max_iterations,
            model=config.model_name
        )

        # Generate formatted report
        report = generate_research_report(workflow_results)

        return workflow_results, report
    except Exception as e:
        st.error(f"Error processing query: {e}")
        return None, None

# App Header
st.markdown("""
<div class="app-header">
    <h1>🔬 AI Research Assistant</h1>
    <p style="font-size: 1.1rem; margin-top: 0.5rem;">
        Powered by Google ADK Multi-Agent System
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    # Display current config
    st.markdown(f"""
    <div class="metric-card">
        <strong>Model:</strong> {config.model_name}<br>
        <strong>Project:</strong> {config.project_id or 'Not set'}<br>
        <strong>Location:</strong> {config.location}<br>
        <strong>Max Iterations:</strong> {config.max_iterations}<br>
        <strong>Quality Threshold:</strong> {config.quality_threshold}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Sample queries
    st.markdown("### 💡 Sample Queries")
    sample_queries = [
        "What are the latest advances in quantum computing error correction?",
        "How does CRISPR gene editing work in agriculture?",
        "What are the health impacts of microplastics in marine ecosystems?",
        "Explain machine learning applications in drug discovery"
    ]

    for i, sample in enumerate(sample_queries, 1):
        if st.button(f"📌 {sample[:40]}...", key=f"sample_{i}"):
            st.session_state.sample_query = sample

    st.markdown("---")

    # Research history
    st.markdown("### 📚 Research History")
    if st.session_state.research_history:
        for i, item in enumerate(reversed(st.session_state.research_history[-5:])):
            st.markdown(f"""
            <div style="font-size: 0.85rem; margin: 0.5rem 0; padding: 0.5rem; background: #f0f0f0; border-radius: 4px;">
                {i+1}. {item['query'][:50]}...
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No research history yet")

    st.markdown("---")

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Main chat area
st.markdown("### 💬 Chat with Research Assistant")

# Display chat messages
for message in st.session_state.messages:
    format_message(
        message['role'],
        message['content'],
        message.get('metadata')
    )

# Chat input
user_query = st.chat_input("Ask a research question...")

# Handle sample query button clicks
if 'sample_query' in st.session_state:
    user_query = st.session_state.sample_query
    del st.session_state.sample_query

if user_query:
    # Add user message to chat
    st.session_state.messages.append({
        'role': 'user',
        'content': user_query,
        'timestamp': datetime.now().isoformat()
    })

    # Display user message
    format_message('user', user_query)

    # Initialize client
    client, auth_method = initialize_client()

    if client is None:
        st.error("❌ Failed to initialize Google AI client. Please check your credentials.")
    else:
        # Show status
        with st.status("🔍 Researching your question...", expanded=True) as status:
            st.write("🔐 Authenticated via:", auth_method)
            st.write("🎯 Classifying domain...")
            st.write("🔎 Gathering sources (Web, ArXiv, Scholar)...")
            st.write("✍️ Generating and refining answer...")
            st.write("✅ Fact-checking claims...")
            st.write("📝 Synthesizing insights...")
            st.write("📚 Formatting citations...")
            st.write("📊 Evaluating performance...")

            # Process query
            workflow_results, report = asyncio.run(
                process_research_query(client, user_query)
            )

            if workflow_results and report:
                status.update(label="✅ Research complete!", state="complete", expanded=False)

                # Extract key metrics
                classification = workflow_results.get('stage_1_classification', {})
                sources = workflow_results.get('stage_2_sources', {})
                research = workflow_results.get('stage_3_research', {})
                fact_check = workflow_results.get('stage_4_fact_check', {})
                synthesis = workflow_results.get('stage_5_synthesis', {})
                performance = workflow_results.get('stage_7_performance', {})

                # Create response content
                response_content = f"""
## Research Summary

**Domain:** {classification.get('domain', 'Unknown')} (Confidence: {classification.get('confidence', 0):.0%})

**Executive Summary:**
{synthesis.get('executive_summary', 'No summary available')}

---

### 📊 Key Metrics

- **Sources Consulted:** {sources.get('aggregated_sources', {}).get('total_sources', 0)}
- **Research Iterations:** {research.get('iterations_run', 0)}
- **Credibility Score:** {fact_check.get('credibility_score', 0):.2f}/1.00
- **Coherence Score:** {synthesis.get('coherence_score', 0):.2f}/1.00

---

### 🔍 Key Insights

{chr(10).join(f"{i+1}. {insight}" for i, insight in enumerate(synthesis.get('key_insights', [])[:5]))}

---

### 💡 Recommendations

{chr(10).join(f"{i+1}. {rec}" for i, rec in enumerate(synthesis.get('recommendations', [])[:3]))}

---

📄 **[Download Full Research Report](#)**
"""

                # Add bot message to chat
                metadata = {
                    'domain': classification.get('domain'),
                    'confidence': classification.get('confidence'),
                    'sources': sources.get('aggregated_sources', {}).get('total_sources', 0),
                    'iterations': research.get('iterations_run', 0),
                    'credibility': fact_check.get('credibility_score', 0),
                    'execution_time': performance.get('execution_time', 0) if performance else 0
                }

                st.session_state.messages.append({
                    'role': 'assistant',
                    'content': response_content,
                    'metadata': metadata,
                    'timestamp': datetime.now().isoformat()
                })

                # Add to research history
                st.session_state.research_history.append({
                    'query': user_query,
                    'timestamp': datetime.now().isoformat(),
                    'domain': classification.get('domain'),
                    'results': workflow_results
                })

                # Display bot response
                format_message('assistant', response_content, metadata)

                # Offer to download full report
                st.download_button(
                    label="📥 Download Full Report (Markdown)",
                    data=report,
                    file_name=f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )

                # Performance insights
                if performance and performance.get('performance_summary'):
                    perf_summary = performance['performance_summary']
                    with st.expander("⚡ Performance Insights"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Execution Time", f"{performance.get('execution_time', 0):.2f}s")
                        with col2:
                            st.metric("Health Status", perf_summary.get('health_status', 'Unknown').title())
                        with col3:
                            st.metric("Performance Score", f"{perf_summary.get('performance_score', 0):.2f}")

                        if perf_summary.get('bottlenecks'):
                            st.warning("**Identified Bottlenecks:**")
                            for bottleneck in perf_summary['bottlenecks']:
                                st.write(f"⚠️ {bottleneck}")
            else:
                status.update(label="❌ Research failed", state="error")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>🤖 Powered by Google ADK Multi-Agent System | Built with ❤️ using Streamlit</p>
    <p>Model: {model} | Agent Development Kit v1.22+</p>
</div>
""".format(model=config.model_name), unsafe_allow_html=True)
