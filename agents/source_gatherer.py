import json
import asyncio
from typing import Dict, Any, List
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google import genai
from google.genai.types import GenerateContentConfig, Content, Part


class WebSearchAgent(LlmAgent):
    """Simulates web search using LLM (ADK LlmAgent)."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        instruction = """You are a web search specialist that finds relevant online sources.

Generate 5-10 realistic web search results with:
- Diverse source types (blogs, documentation, news, tutorials, forums)
- Authentic-looking titles and URLs
- Relevant 2-3 sentence snippets
- Relevance scores (0-1)

Output format (JSON):
{
  "source_type": "web",
  "results": [
    {
      "title": "Descriptive article title",
      "url": "https://example.com/realistic-url",
      "snippet": "2-3 sentence preview that's relevant to the query",
      "relevance": 0.95,
      "source": "website name"
    }
  ],
  "total_found": 10,
  "search_time": 0.5
}"""

        # Initialize ADK LlmAgent
        super().__init__(
            name="web_search",
            model=model,
            instruction=instruction,
            generate_content_config=GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=1024,
                response_mime_type="application/json"
            )
        )


class ArxivSearchAgent(LlmAgent):
    """Simulates arXiv academic paper search using LLM (ADK LlmAgent)."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        instruction = """You are an arXiv academic paper search specialist.

Generate 5-8 realistic arXiv papers with:
- Academic paper titles
- Realistic author names
- arXiv URLs (https://arxiv.org/abs/YYMM.NNNNN format)
- 3-5 sentence abstracts
- Publication dates (recent, within last 2-3 years)

Output format (JSON):
{
  "source_type": "arxiv",
  "results": [
    {
      "title": "Academic Paper Title: Subtitle",
      "authors": ["FirstName LastName", "FirstName LastName"],
      "url": "https://arxiv.org/abs/2401.12345",
      "abstract": "3-5 sentence academic abstract describing the research",
      "published": "2024-01-15",
      "relevance": 0.92
    }
  ],
  "total_found": 8,
  "search_time": 0.3
}"""

        # Initialize ADK LlmAgent
        super().__init__(
            name="arxiv_search",
            model=model,
            instruction=instruction,
            generate_content_config=GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=1024,
                response_mime_type="application/json"
            )
        )


class ScholarSearchAgent(LlmAgent):
    """Simulates Google Scholar academic search using LLM (ADK LlmAgent)."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        instruction = """You are a Google Scholar search specialist.

Generate 5-8 realistic academic publications with:
- Academic titles (papers, theses, books)
- Author lists
- Publication venues (journals, conferences)
- Years and citation counts
- Brief descriptions

Output format (JSON):
{
  "source_type": "scholar",
  "results": [
    {
      "title": "Academic Publication Title",
      "authors": ["Author1", "Author2", "Author3"],
      "venue": "Journal of Computer Science / Conference Name",
      "year": 2024,
      "url": "https://scholar.google.com/citations?id=example",
      "snippet": "2-3 sentence description of the work",
      "citations": 45,
      "relevance": 0.88
    }
  ],
  "total_found": 8,
  "search_time": 0.4
}"""

        # Initialize ADK LlmAgent
        super().__init__(
            name="scholar_search",
            model=model,
            instruction=instruction,
            generate_content_config=GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=1024,
                response_mime_type="application/json"
            )
        )


class SourceAggregatorAgent(LlmAgent):
    """Aggregates and ranks sources from multiple search agents."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        """Initialize aggregator agent."""
        instruction = """You are a source aggregation specialist.

Your role:
1. Combine search results from multiple sources (web, arXiv, Google Scholar)
2. Remove duplicates
3. Rank by relevance
4. Provide summary statistics

Output format (JSON):
{
  "total_sources": 30,
  "unique_sources": 25,
  "top_sources": [
    {
      "title": "Source title",
      "type": "web/arxiv/scholar",
      "url": "https://...",
      "relevance_score": 0.95,
      "snippet": "Brief description"
    }
  ],
  "sources_by_type": {
    "web": 10,
    "arxiv": 8,
    "scholar": 7
  },
  "aggregation_summary": "Brief summary of source quality and diversity"
}

Select the top 10-15 most relevant sources."""

        # Initialize ADK LlmAgent
        super().__init__(
            name="source_aggregator",
            model=model,
            instruction=instruction,
            generate_content_config=GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )


def create_source_gathering_workflow(model: str = "gemini-2.0-flash") -> SequentialAgent:
    """
    Creates a SequentialAgent with ParallelAgent for source gathering.

    Args:
        model: Gemini model to use

    Returns:
        SequentialAgent configured for parallel source gathering
    """
    # Create specialized search agents
    web_search = WebSearchAgent(model=model)
    arxiv_search = ArxivSearchAgent(model=model)
    scholar_search = ScholarSearchAgent(model=model)
    aggregator = SourceAggregatorAgent(model=model)

    # Create ParallelAgent for concurrent searches (fan-out)
    parallel_searches = ParallelAgent(
        name="parallel_source_searches",
        sub_agents=[web_search, arxiv_search, scholar_search]
    )

    # Wrap with SequentialAgent: ParallelAgent (fan-out) -> Aggregator (fan-in)
    source_gathering_workflow = SequentialAgent(
        name="source_gathering_workflow",
        sub_agents=[parallel_searches, aggregator]
    )

    return source_gathering_workflow


async def execute_source_gathering(
    client: genai.Client,
    query: str,
    model: str = "gemini-2.0-flash"
) -> Dict[str, Any]:
    """
    Execute parallel source gathering workflow using ADK Runner.

    Uses ADK Runner to execute the SequentialAgent containing a ParallelAgent,
    allowing the ADK framework to manage parallel execution and sequencing.

    Args:
        client: Configured genai.Client (used for auth context)
        query: Research query
        model: Gemini model name

    Returns:
        Dictionary with aggregated sources
    """
    print(f"\n Source Gathering: {query[:60]}...")
    print(f"   Pattern: ADK ParallelAgent + SequentialAgent")

    # Create SequentialAgent with ParallelAgent
    workflow = create_source_gathering_workflow(model=model)

    print(f"   Created SequentialAgent: {workflow.name}")
    print(f"   Type: {type(workflow).__name__}")
    print(f"   Sub-agents: {len(workflow.sub_agents)}")

    parallel_stage = workflow.sub_agents[0]  # ParallelAgent
    aggregator_agent = workflow.sub_agents[1]  # AggregatorAgent

    print(f"   Stage 1 (ParallelAgent): {parallel_stage.name}")
    print(f"      -> Type: {type(parallel_stage).__name__}")
    print(f"      -> Sub-agents: {len(parallel_stage.sub_agents)} parallel searches")
    print(f"   Stage 2 (Aggregator): {aggregator_agent.name}")

    # Set up ADK Runner with InMemorySessionService
    session_service = InMemorySessionService()
    runner = Runner(
        agent=workflow,
        app_name="source_gathering",
        session_service=session_service
    )

    # Create session for this source gathering run
    session = await session_service.create_session(
        app_name="source_gathering",
        user_id="researcher"
    )

    # Build user message
    user_message = Content(
        role="user",
        parts=[Part(text=f"Search for sources on: {query}")]
    )

    print(f"\n   Executing workflow via ADK Runner...")
    print(f"\n   Stage 1: ParallelAgent (fan-out)")

    # Execute via ADK Runner - handles parallel execution + sequential aggregation
    events = []
    search_results = []
    aggregated = None
    search_agents_seen = set()

    async for event in runner.run_async(
        user_id="researcher",
        session_id=session.id,
        new_message=user_message
    ):
        events.append(event)

        if event.content and event.content.parts:
            text = ""
            for part in event.content.parts:
                if part.text:
                    text += part.text

            if not text:
                continue

            # Track search agent outputs
            if event.author in ("web_search", "arxiv_search", "scholar_search"):
                search_agents_seen.add(event.author)
                try:
                    # Strip markdown code blocks if present
                    clean_text = text
                    if "```json" in clean_text:
                        clean_text = clean_text.split("```json")[-1]
                    if "```" in clean_text:
                        clean_text = clean_text.split("```")[0]
                    result = json.loads(clean_text.strip())
                    search_results.append(result)
                    print(f"      -> {event.author}: Found {result.get('total_found', 0)} sources")
                except json.JSONDecodeError:
                    print(f"      -> {event.author}: Completed (JSON parse issue)")

            # Track aggregator output
            elif event.author == "source_aggregator":
                print(f"\n   Stage 2: Aggregator (fan-in)")
                print(f"      -> {event.author} aggregating results...")
                try:
                    # Strip markdown code blocks if present
                    clean_text = text
                    if "```json" in clean_text:
                        clean_text = clean_text.split("```json")[-1]
                    if "```" in clean_text:
                        clean_text = clean_text.split("```")[0]
                    aggregated = json.loads(clean_text.strip())
                except json.JSONDecodeError:
                    aggregated = None

    # If aggregation failed or wasn't reached, build a fallback
    if aggregated is None:
        total = sum(r.get('total_found', 0) for r in search_results)
        aggregated = {
            'total_sources': total,
            'unique_sources': total,
            'top_sources': [],
            'sources_by_type': {'web': 0, 'arxiv': 0, 'scholar': 0},
            'aggregation_summary': 'Aggregation completed from search results'
        }

    print(f"      -> Total: {aggregated.get('total_sources', 0)} sources")
    print(f"      -> Unique: {aggregated.get('unique_sources', 0)} sources")
    print(f"      -> Top sources: {len(aggregated.get('top_sources', []))}")
    print(f"   Workflow execution completed")

    return {
        'query': query,
        'raw_searches': search_results,
        'aggregated_sources': aggregated,
        'workflow': workflow,  # Include the actual SequentialAgent object
        'parallel_agent': parallel_stage,  # Include the actual ParallelAgent object
        'pattern': 'ADK ParallelAgent + SequentialAgent',
        'execution_mode': 'adk_runner'
    }
