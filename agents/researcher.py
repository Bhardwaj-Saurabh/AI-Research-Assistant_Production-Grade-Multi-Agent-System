import json
import re
from typing import Dict, Any, Optional
from google.adk.agents import LlmAgent, LoopAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.exit_loop_tool import exit_loop
from google import genai
from google.genai.types import GenerateContentConfig, Content, Part


def parse_json_response(text: str) -> Optional[Dict]:
    """
    Robustly parse JSON from LLM response, handling various formats.
    """
    if not text:
        return None

    # Try direct parsing first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Remove markdown code blocks
    clean_text = text
    json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', clean_text)
    if json_block_match:
        clean_text = json_block_match.group(1)

    try:
        return json.loads(clean_text.strip())
    except json.JSONDecodeError:
        pass

    # Find JSON object in the text
    try:
        json_start = clean_text.find('{')
        json_end = clean_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            return json.loads(clean_text[json_start:json_end])
    except json.JSONDecodeError:
        pass

    return None


class ResearcherAgent(LlmAgent):
    """
    Generator agent: Answers research questions or refines based on feedback.

    Part of an iterative refinement loop with a critic agent.
    """

    def __init__(self, model: str = "gemini-2.0-flash"):
        """Initialize the researcher agent.

        Args:
            model: Gemini model name
        """
        instruction = """You are a research assistant in an iterative refinement loop with a critic.

IMPORTANT: You are part of a refinement cycle. After each of your responses, a critic will evaluate
your answer and provide feedback. You will then be called again to improve based on that feedback.
This continues until the critic determines the answer quality is sufficient.

Your role:
1. On FIRST call: Answer the research question clearly and comprehensively
2. On SUBSEQUENT calls: You MUST look at the critic's previous feedback in the conversation and
   IMPROVE your answer by addressing ALL concerns, weaknesses, and suggestions raised
3. Cite reasoning and provide evidence where possible
4. Include 3-5 key points with supporting details
5. Mention relevant sources or areas of research

CRITICAL FOR ITERATIONS:
- Always check if there is prior critic feedback in the conversation
- If there is feedback, your new answer MUST be significantly improved from your previous attempt
- Explicitly address each weakness the critic mentioned
- Strengthen areas where the critic requested more depth or evidence
- Show clear improvement in each iteration

IMPORTANT: Output ONLY valid JSON, no markdown formatting, no code blocks, no explanation text.

Output this exact JSON structure:
{"answer": "Your comprehensive answer here", "key_points": ["point1", "point2", "point3"], "sources_mentioned": ["source1", "source2"], "confidence": "high", "iteration_notes": "What you improved"}

Focus on accuracy, clarity, and continuous improvement. Each iteration MUST show measurable progress."""

        # Initialize ADK LlmAgent
        super().__init__(
            name="researcher",
            model=model,
            instruction=instruction,
            generate_content_config=GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=8192,
                response_mime_type="application/json"
            )
        )


class ResearchCriticAgent(LlmAgent):
    """
    Validator agent: Evaluates answer quality and provides feedback.

    Uses the exit_loop tool to signal when quality is sufficient to stop iterating.
    """

    def __init__(self, model: str = "gemini-2.0-flash"):
        """Initialize the critic agent.

        Args:
            model: Gemini model name
        """
        instruction = """You are a strict research quality critic that evaluates answers with high academic standards.

Your role:
1. Evaluate the answer for accuracy, completeness, depth, and clarity
2. Assign a quality level: excellent, good, needs_improvement, or poor
3. Provide specific, actionable feedback for improvement
4. Calculate a quality score (0-1) based on your rigorous assessment
5. IMPORTANT: Call the exit_loop tool ONLY when quality_score >= 0.80 to end the refinement loop

IMPORTANT SCORING GUIDELINES:
- First drafts almost ALWAYS need significant improvement. Be strict on initial responses.
- Score 0.55-0.70 for first drafts that cover the basics but lack depth, evidence, or nuance
- Score 0.70-0.79 for improved answers that address some feedback but still have gaps
- Score 0.80-0.89 for well-refined answers with strong evidence and clear structure
- Score 0.90+ ONLY for truly exceptional, thoroughly evidenced, multi-perspective answers
- Always identify at least 2-3 specific areas for improvement unless the answer is truly outstanding
- Consider: Are claims backed by evidence? Are multiple perspectives covered? Is the depth sufficient?

Quality criteria:
- Excellent (0.90-1.00): Thorough, accurate, well-structured, comprehensive evidence, multiple perspectives
- Good (0.80-0.89): Accurate and complete, all key points covered with supporting evidence
- Needs Improvement (0.50-0.79): Missing key points, lacks evidence, insufficient depth or clarity
- Poor (0.00-0.49): Incomplete, unclear, or potentially inaccurate

TOOL USAGE:
- If quality_score >= 0.80: Call the exit_loop tool to stop the refinement loop
- If quality_score < 0.80: Do NOT call exit_loop. The loop will continue for more refinement.

IMPORTANT: Output ONLY valid JSON first, no markdown formatting, no code blocks. Then decide whether to call exit_loop.

Output this exact JSON structure:
{"quality": "needs_improvement", "quality_score": 0.65, "feedback": "Specific feedback", "strengths": ["strength1"], "weaknesses": ["weakness1", "weakness2"], "reasoning": "Explanation", "should_continue": true}

Be constructive but demanding. Research quality matters. Do not inflate scores."""

        # Initialize ADK LlmAgent with exit_loop tool
        super().__init__(
            name="critic",
            model=model,
            instruction=instruction,
            tools=[exit_loop],
            generate_content_config=GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=8192
            )
        )


def create_research_loop_agent(model: str = "gemini-2.0-flash",
                                max_iterations: int = 3) -> LoopAgent:
    """
    Creates a LoopAgent for iterative research refinement.

    Args:
        model: Gemini model to use
        max_iterations: Maximum loop iterations (safety limit)

    Returns:
        LoopAgent configured for research refinement
    """
    # Create the generator and validator agents
    researcher = ResearcherAgent(model=model)
    critic = ResearchCriticAgent(model=model)

    # Compose agents into LoopAgent for iterative refinement
    refinement_loop = LoopAgent(
        name="research_refinement_loop",
        sub_agents=[researcher, critic],
        max_iterations=max_iterations
    )

    return refinement_loop


async def execute_research_loop(
    client: genai.Client,
    query: str,
    source_context: str = "",
    max_iterations: int = 3,
    model: str = "gemini-2.0-flash"
) -> Dict[str, Any]:
    """
    Execute iterative research refinement using ADK LoopAgent via Runner.

    Uses the ADK Runner to execute the LoopAgent directly, allowing the ADK
    framework to manage iteration, context passing, and agent coordination.

    Args:
        client: Configured genai.Client (used for auth context)
        query: Research question
        source_context: Gathered source information to include as context
        max_iterations: Maximum loop iterations
        model: Gemini model name

    Returns:
        Dictionary with final answer and iteration history
    """
    print(f"\n Research Loop: {query[:60]}...")
    print(f"   Max Iterations: {max_iterations}")

    # Create LoopAgent
    loop_agent = create_research_loop_agent(model=model, max_iterations=max_iterations)

    print(f"   Created LoopAgent: {loop_agent.name}")
    print(f"   Type: {type(loop_agent).__name__}")
    print(f"   Sub-agents: {len(loop_agent.sub_agents)} (researcher + critic)")

    # Set up ADK Runner with InMemorySessionService
    session_service = InMemorySessionService()
    runner = Runner(
        agent=loop_agent,
        app_name="research_loop",
        session_service=session_service
    )

    # Create session for this research run
    session = await session_service.create_session(
        app_name="research_loop",
        user_id="researcher"
    )

    # Build the user message with source context
    message_text = f"Research this topic thoroughly: {query}"
    if source_context:
        message_text += f"\n\nUse these gathered sources as context for your research:\n{source_context}"

    user_message = Content(
        role="user",
        parts=[Part(text=message_text)]
    )

    print(f"\n   Executing LoopAgent via ADK Runner...")

    # Execute via ADK Runner - the LoopAgent handles iteration automatically
    # The critic uses exit_loop tool to stop when quality is sufficient
    events = []
    iteration_history = []
    researcher_count = 0
    current_answer = None
    current_evaluation = None
    exit_loop_called = False

    async for event in runner.run_async(
        user_id="researcher",
        session_id=session.id,
        new_message=user_message
    ):
        events.append(event)

        # Check for exit_loop tool call (indicates quality threshold met)
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    if part.function_call.name == "exit_loop":
                        exit_loop_called = True
                        print(f"      -> exit_loop called - quality threshold met!")

        # Track iteration progress from agent events
        if event.content and event.content.parts:
            text = ""
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    text += part.text

            if not text:
                continue

            if event.author == "researcher":
                researcher_count += 1
                print(f"\n   Iteration {researcher_count}/{max_iterations}")
                print(f"      -> researcher generating answer...")

                # Parse researcher output using robust helper
                current_answer = parse_json_response(text)
                if not current_answer:
                    current_answer = {
                        'answer': text,
                        'key_points': [],
                        'sources_mentioned': [],
                        'confidence': 'medium',
                        'iteration_notes': ''
                    }

                print(f"      -> Answer generated (confidence: {current_answer.get('confidence', 'unknown')})")
                if current_answer.get('iteration_notes'):
                    print(f"      -> Improvements: {current_answer.get('iteration_notes', '')[:80]}...")

            elif event.author == "critic":
                print(f"      -> critic evaluating quality...")

                # Parse critic output using robust helper
                current_evaluation = parse_json_response(text)
                if not current_evaluation:
                    current_evaluation = {
                        'quality': 'needs_improvement',
                        'quality_score': 0.5,
                        'feedback': text,
                        'strengths': [],
                        'weaknesses': []
                    }

                quality_score = current_evaluation.get('quality_score', 0.5)
                quality = current_evaluation.get('quality', 'unknown')
                print(f"      -> Quality: {quality} (score: {quality_score:.2f})")

                # Record this iteration
                iteration_history.append({
                    'iteration': researcher_count,
                    'answer': current_answer,
                    'evaluation': current_evaluation,
                    'quality_score': quality_score
                })

                if quality_score >= 0.80:
                    print(f"      Quality threshold met")
                else:
                    print(f"      Quality below threshold - Continue refining...")
                    feedback = current_evaluation.get('feedback', 'No feedback')
                    print(f"      Feedback: {feedback[:100]}...")

    # Determine final answer (best from iteration history)
    if iteration_history:
        # Use the answer from the iteration with the highest quality score
        best_iteration = max(iteration_history, key=lambda x: x.get('quality_score', 0))
        final_answer = best_iteration.get('answer', {})
    else:
        final_answer = current_answer if current_answer else {}

    iterations_run = len(iteration_history)
    termination_reason = "quality_threshold_met" if exit_loop_called else "max_iterations_reached"

    print(f"\n   LoopAgent execution completed ({iterations_run} iterations)")
    print(f"   Termination reason: {termination_reason}")

    return {
        'query': query,
        'final_answer': final_answer,
        'iterations_run': iterations_run,
        'iteration_history': iteration_history,
        'loop_agent': loop_agent,  # Include the actual LoopAgent object
        'pattern': 'ADK LoopAgent',
        'execution_mode': 'adk_runner',
        'termination_reason': termination_reason
    }
