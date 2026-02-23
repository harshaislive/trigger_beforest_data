from crewai import Agent, Task, Crew, Process
from .llm import get_llm
from .tools import BraveSearchTool, RAGSearchTool, MemorySearchTool, URLContentTool


llm = get_llm()
brave_search = BraveSearchTool()
rag_search = RAGSearchTool()
memory_search = MemorySearchTool()
url_content = URLContentTool()


researcher_agent = Agent(
    role="Research Specialist",
    goal="Find the most relevant Beforest Ecoverse information from knowledge base and web",
    backstory="""You are an expert researcher with deep knowledge of the Beforest knowledge base.
Your specialty is finding accurate, relevant information from the knowledge base first, then
supplementing with web search if needed. The local beforest_data files represent the Beforest
Ecoverse websites and should be treated as high-trust sources. Canonical brand domains are:
beforest.co, bewild.life, hospitality.beforest.co, experiences.beforest.co, 10percent.beforest.co.
Never invent or guess domains. You always cite your sources.""",
    tools=[rag_search, brave_search, url_content],
    llm=llm,
    verbose=True,
    allow_delegation=False,
)


memory_agent = Agent(
    role="Conversation Memory Specialist",
    goal="Remember and utilize previous conversation context",
    backstory="""You have an excellent memory for conversations. Your job is to recall
previous messages from this user to maintain context and provide personalized responses.
Use the conversation history to understand what the user has already asked about.""",
    tools=[memory_search],
    llm=llm,
    verbose=True,
    allow_delegation=False,
)


reply_crafter_agent = Agent(
    role="Expert Copywriter",
    goal="Craft concise, factual, on-brand Beforest responses with a confident tone",
    backstory="""You are the voice of Beforest.

About Beforest:
- We build regenerative communities where people live with the land, not off it.
- Current collective locations include Coorg, Hyderabad, Mumbai, and Bhopal.
- Canonical brand domains are exactly: beforest.co, bewild.life, hospitality.beforest.co,
  experiences.beforest.co, and 10percent.beforest.co.

How you respond:
- You ARE Beforest. Do not say "I work at Beforest" or "reach out to the team".
- Prioritize factual accuracy from provided research and conversation memory.
- Be direct, clear, and premium in tone (confident, never arrogant).
- Keep replies compact with natural rhythm.
- Prefer 2 to 4 short chat-sized chunks over one dense paragraph when useful.
- Never use em dash characters. Use commas, full stops, or a regular hyphen.
- Never invent specifics. If information is missing or uncertain, say that briefly.
- Never invent website names or domains. If unsure, mention only canonical domains above.
- Avoid marketing hype. Sound practical, grounded, and human.
- Guide the user clearly through the Beforest Ecoverse: places, offerings, next steps, and who it is for.""",
    llm=llm,
    verbose=True,
    allow_delegation=False,
)


def create_crew(message: str, contact_id: str, name: str = "User") -> Crew:
    """Create and return a crew for processing the user message."""

    def should_run_research(text: str) -> bool:
        lower = text.lower().strip()
        conversational_signals = (
            "thanks",
            "thank you",
            "great",
            "awesome",
            "nice",
            "cool",
            "got it",
            "okay",
            "ok",
            "understood",
            "i like",
            "makes sense",
        )
        if any(signal in lower for signal in conversational_signals) and "?" not in lower:
            return False

        if len(lower) >= 45 and "?" in lower:
            return True

        if lower.endswith("?"):
            return True

        triggers = (
            "what",
            "how",
            "why",
            "where",
            "when",
            "which",
            "tell me",
            "explain",
            "details",
            "price",
            "cost",
            "collective",
            "beforest",
        )
        return any(t in lower for t in triggers)
    
    research_task = Task(
        description=f"""Research the user's question: {message}
        
        Steps:
        1. First search the knowledge base for relevant information
        2. If knowledge base doesn't have sufficient info, use web search
        3. For important web claims, open 1-2 best URLs and verify key facts
        4. Provide a short summary with sources""",
        expected_output="A summary of relevant information from knowledge base and/or web with sources cited",
        agent=researcher_agent,
    )
    
    memory_task = Task(
        description=f"""Get conversation history for user {contact_id} (name: {name})
        
        Retrieve the last 5-10 messages to understand the context.""",
        expected_output="Summary of recent conversation history",
        agent=memory_agent,
    )
    
    craft_task = Task(
        description=f"""Based on the research and memory context, craft a response to:
        
        User: {message}
        User Name: {name}
        
        Guidelines:
        - Speak as Beforest (first-person brand voice)
        - Prefer facts from research and memory over style
        - Be direct, practical, and premium in tone
        - Keep it concise but human, often as 2-4 short chunks
        - Never use em dash characters
        - Help user navigate the Beforest Ecoverse with clear next-step guidance
        - No fluff, no hype, no unnecessary adjectives
        - If user asks about a known Beforest brand (beforest, bewild, hospitality, experiences, 10percent), never say "no info" without checking provided research context first
        - If info is unavailable or uncertain, say so clearly in one short sentence""",
        expected_output="A single, premium response (2-3 sentences max)",
        agent=reply_crafter_agent,
    )
    
    tasks = [memory_task, craft_task]
    agents = [memory_agent, reply_crafter_agent]
    if should_run_research(message):
        tasks = [research_task, memory_task, craft_task]
        agents = [researcher_agent, memory_agent, reply_crafter_agent]

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    
    return crew


def run_crew(message: str, contact_id: str, name: str = "User") -> str:
    """Run the crew and return the response."""
    crew = create_crew(message, contact_id, name)
    result = crew.kickoff()
    return str(result)
