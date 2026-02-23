from crewai import Agent, Task, Crew, Process
from .llm import get_llm
from .tools import BraveSearchTool, RAGSearchTool, MemorySearchTool


llm = get_llm()
brave_search = BraveSearchTool()
rag_search = RAGSearchTool()
memory_search = MemorySearchTool()


researcher_agent = Agent(
    role="Research Specialist",
    goal="Find the most relevant information from knowledge base and web to answer user questions accurately",
    backstory="""You are an expert researcher with deep knowledge of the Beforest knowledge base.
Your specialty is finding accurate, relevant information from the knowledge base first, then
supplementing with web search if needed. You always cite your sources.""",
    tools=[rag_search, brave_search],
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
    goal="Craft premium, compelling, no-fluff responses in the style of Ogilvy advertising",
    backstory="""You are David Ogilvy reincarnated. You write crisp, persuasive,
and premium copy that cuts through noise. Your responses are:
- Direct and assertive
- Premium in tone (confident, not arrogant)
- Completely free of fluff and filler
- Action-oriented
- Maximum 2-3 sentences unless detail is explicitly needed

You take information from the research and memory agents and transform it into
compelling, concise responses that drive action.""",
    llm=llm,
    verbose=True,
    allow_delegation=False,
)


def create_crew(message: str, contact_id: str, name: str = "User") -> Crew:
    """Create and return a crew for processing the user message."""
    
    research_task = Task(
        description=f"""Research the user's question: {message}
        
        Steps:
        1. First search the knowledge base for relevant information
        2. If knowledge base doesn't have sufficient info, use web search
        3. Provide a summary of findings with sources""",
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
        - Be direct and assertive
        - Premium tone (confident, not arrogant)
        - No fluff or filler
        - Maximum 2-3 sentences
        - If info is not available, say so briefly""",
        expected_output="A single, premium response (2-3 sentences max)",
        agent=reply_crafter_agent,
    )
    
    crew = Crew(
        agents=[researcher_agent, memory_agent, reply_crafter_agent],
        tasks=[research_task, memory_task, craft_task],
        process=Process.sequential,
        verbose=True,
    )
    
    return crew


def run_crew(message: str, contact_id: str, name: str = "User") -> str:
    """Run the crew and return the response."""
    crew = create_crew(message, contact_id, name)
    result = crew.kickoff()
    return str(result)
