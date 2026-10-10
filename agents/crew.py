
import os

from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

import crewai.llms.cache as crew_cache
from services.search import web_search


# --------------------------------------------------
# Configuration
# --------------------------------------------------

load_dotenv()

# Preserve the workaround from your working setup
crew_cache.mark_cache_breakpoint = lambda msg: msg

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "groq/openai/gpt-oss-20b")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing. Add it to your .env file."
    )

llm = LLM(
    model=MODEL,
    api_key=GROQ_API_KEY,
    temperature=0.2,
)


# --------------------------------------------------
# AI Agents
# --------------------------------------------------

researcher = Agent(
    role="Senior Research Analyst",
    goal=(
        "Analyze supplied web-search results and identify relevant "
        "technology developments, findings, limitations, and sources."
    ),
    backstory=(
        "You are a technology research analyst. You evaluate evidence, "
        "compare sources, identify trends, and clearly distinguish "
        "verified information from uncertainty."
    ),
    llm=llm,
    verbose=False,
    allow_delegation=False,
    max_iter=3,
)

writer = Agent(
    role="Tech Content Writer",
    goal="Create engaging, clear, research-based blog posts.",
    backstory=(
        "You transform research reports into polished, readable articles "
        "for technology enthusiasts. You never invent sources or facts."
    ),
    llm=llm,
    verbose=False,
    allow_delegation=False,
    max_iter=3,
)


# --------------------------------------------------
# Research and Writing Workflow
# --------------------------------------------------

def generate_blog(topic: str, year: str) -> str:
    """Search the web, analyze results, and generate a blog article."""

    if not topic or not topic.strip():
        raise ValueError("Please enter a research topic.")

    topic = topic.strip()

    if len(topic) > 200:
        raise ValueError("Keep the research topic under 200 characters.")

    year = str(year).strip()

    # Step 1: Search directly in Python.
    # The LLM does not need to invoke a search tool.
    queries = [
        f"{topic} developments trends {year}",
        f"{topic} research applications limitations {year}",
        f"{topic} latest news reports {year}",
    ]

    search_results = []

    for query in queries:
        result = web_search.run(query)

        if result:
            search_results.append(
                f"Search query: {query}\n{result}"
            )

    research_material = "\n\n---\n\n".join(search_results)

    if not research_material.strip():
        research_material = (
            "Web search returned no usable results. "
            "Clearly disclose this limitation and do not invent citations."
        )

    # Step 2: Analyze the collected results.
    research_task = Task(
        description=(
            f"Research the topic '{topic}' for the year {year}.\n\n"
            "Use the supplied search results below as your evidence. "
            "Identify major developments, trends, applications, "
            "limitations, and uncertainties. Include source titles and "
            "URLs exactly as provided. Do not claim to have verified "
            "information that the results do not establish.\n\n"
            f"WEB SEARCH RESULTS:\n{research_material}"
        ),
        expected_output=(
            "A structured research report with key findings, explanations, "
            "source URLs, and explicit limitations."
        ),
        agent=researcher,
    )

    # Step 3: Write the article using the research report.
    writing_task = Task(
        description=(
            f"Write a polished technology blog post about '{topic}', "
            f"focused on {year}, using the research report from the "
            "previous task.\n\n"
            "Requirements:\n"
            "1. Create a compelling title.\n"
            "2. Write an engaging introduction.\n"
            "3. Include at least four informative body sections.\n"
            "4. Explain practical applications and limitations.\n"
            "5. Finish with a conclusion.\n"
            "6. Include a Sources section with URLs from the research.\n"
            "7. Never fabricate facts, quotations, or source URLs.\n"
            "8. Write the complete article in Markdown."
        ),
        expected_output="A complete, polished blog post in Markdown.",
        agent=writer,
        context=[research_task],
    )

    # Step 4: Execute the workflow.
    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, writing_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    return str(result)
