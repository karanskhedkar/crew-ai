from pathlib import Path
from datetime import datetime
import tempfile

import gradio as gr

from agents.crew import generate_blog
from services.database import (
    init_db,
    save_article,
    list_articles,
    get_article,
    get_article_count,
)

BASE_DIR = Path(__file__).resolve().parent
HTML_PATH = BASE_DIR / "templates" / "index.html"
CSS_PATH = BASE_DIR / "static" / "style.css"
JS_PATH = BASE_DIR / "static" / "script.js"

init_db()


def get_history_choices():
    """Return (visible label, database ID) choices for the history sidebar."""
    choices = []
    for item in list_articles(limit=50):
        title = (item["title"] or item["topic"] or "Untitled Research").strip()
        title = title.lstrip("# ").strip()

        # Clean truncation so title fits cleanly on one line without wrapping
        if len(title) > 28:
            truncated = title[:27].rsplit(" ", 1)[0]
            display_title = (truncated if truncated else title[:27]) + "…"
        else:
            display_title = title

        try:
            dt = datetime.fromisoformat(item["created_at"])
            date_label = dt.strftime("%b %d, %H:%M")
        except Exception:
            date_label = item["created_at"][:16].replace("T", " ")

        choices.append((f"{display_title}\n{date_label}", str(item["id"])))
    return choices


def load_history(article_id):
    if not article_id:
        return "Select an article from your history to read it.", "Choose an article from the sidebar."
    article = get_article(int(article_id))
    if not article:
        return "This article could not be found.", "The selected history item is unavailable."
    return article["content"], f"Loaded: {article['title']}"


def create_article(topic, year=None):
    if not topic or not topic.strip():
        raise gr.Error("Enter a research topic first.")

    current_year = str(year) if year else str(datetime.now().year)

    yield (
        "## ⏳ Conducting research...\n\nYour researcher agent is searching live web sources, exploring trends, and compiling findings. This usually takes 30–60 seconds…",
        gr.update(),
        "Preparing research…",
        None,
    )

    try:
        article_text = generate_blog(topic.strip(), current_year)
        title = next(
            (line.lstrip("# ").strip() for line in article_text.splitlines()
             if line.strip().startswith("#")),
            topic.strip()
        )
        article_id = save_article(
            topic=topic.strip(),
            year=current_year,
            title=title,
            content=article_text,
        )
        choices = get_history_choices()
        export_path = None
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".md",
            prefix="research_article_", delete=False
        ) as handle:
            handle.write(article_text)
            export_path = handle.name

        yield (
            article_text,
            gr.update(choices=choices, value=str(article_id)),
            f"Article saved to history · {datetime.now().strftime('%d %b %Y, %H:%M')}",
            export_path,
        )
    except gr.Error:
        raise
    except Exception as exc:
        print(f"Article generation failed: {exc}")
        raise gr.Error(
            "Article generation failed. Check the terminal for the detailed error."
        ) from exc


def refresh_history():
    choices = get_history_choices()
    selected = choices[0][1] if choices else None
    if selected:
        article = get_article(int(selected))
        return (
            gr.update(choices=choices, value=selected),
            article["content"],
            "History refreshed.",
        )
    return (
        gr.update(choices=[], value=None),
        "No saved articles yet.",
        "Your saved articles will appear here.",
    )


def get_saved_card_html(count):
    return f"""
    <div class="metric-card-inner">
        <div class="metric-header">
            <span class="metric-label">SAVED ARTICLES</span>
            <span class="metric-icon">📚</span>
        </div>
        <div class="metric-value">{count}</div>
        <div class="metric-sub">Stored locally in SQLite</div>
    </div>
    """


def dashboard_stats():
    count = get_article_count()
    return str(count), "SQLite history enabled"


with open(HTML_PATH, "r", encoding="utf-8") as file:
    header_html = file.read()
with open(CSS_PATH, "r", encoding="utf-8") as file:
    css_content = file.read()
with open(JS_PATH, "r", encoding="utf-8") as file:
    js_content = file.read()

initial_choices = get_history_choices()
initial_selected = initial_choices[0][1] if initial_choices else None
initial_article = get_article(int(initial_selected)) if initial_selected else None

with gr.Blocks(
    title="ResearchOS — AI Research Workspace",
    fill_height=True,
) as demo:
    with gr.Row(elem_id="app-layout"):
        # Sidebar
        with gr.Column(scale=0, min_width=0, elem_id="sidebar"):
            gr.HTML("""
                <div class="brand">
                    <div class="brand-info">
                        <div class="brand-mark">R</div>
                        <div>
                            <div class="brand-name">ResearchOS</div>
                            <div class="brand-caption">AI RESEARCH WORKSPACE</div>
                        </div>
                    </div>
                    <button id="close-drawer-btn" class="drawer-close-btn" aria-label="Close sidebar" type="button">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            """)

            new_research_btn = gr.Button("＋   New research", elem_id="new-research-btn", variant="primary")
            gr.HTML('<div class="sidebar-section-label history-label">RECENT HISTORY</div>')

            history_radio = gr.Radio(
                choices=initial_choices,
                value=initial_selected,
                label=None,
                container=False,
                elem_id="history-list",
                info="",
            )
            refresh_btn = gr.Button("↻   Refresh history", elem_id="refresh-history-btn")
            gr.HTML("""
                <div class="sidebar-bottom">
                    <div class="sidebar-divider"></div>
                    <div class="connection-row">
                        <span class="connection-dot"></span>
                        <span>AI engine configured</span>
                    </div>
                    <div class="sidebar-footnote">CrewAI · Groq · DuckDuckGo</div>
                </div>
            """)

        # Main workspace
        with gr.Column(scale=1, min_width=0, elem_id="workspace"):
            with gr.Row(elem_id="topbar"):
                gr.HTML("""
                    <div class="topbar-left">
                        <button id="mobile-menu-btn" class="hamburger-btn" aria-label="Toggle history menu" type="button" aria-expanded="false">
                            <span class="hamburger-box">
                                <span class="hamburger-line line-1"></span>
                                <span class="hamburger-line line-2"></span>
                                <span class="hamburger-line line-3"></span>
                            </span>
                        </button>
                        <div class="mobile-brand-title">
                            <span class="mobile-brand-mark">R</span>
                            <span class="mobile-brand-text">ResearchOS</span>
                        </div>
                        <div class="breadcrumb desktop-breadcrumb">
                            <span>WORKSPACE</span><span class="breadcrumb-slash">/</span>
                            <strong>Research studio</strong>
                        </div>
                    </div>
                """)
                status = gr.Markdown("`READY`  ·  Workspace online", elem_id="top-status")

            gr.HTML(header_html)

            with gr.Column(elem_classes=["surface-card"], elem_id="research-card", min_width=0):
                gr.HTML("""
                    <div class="card-heading-row">
                        <div>
                            <div class="eyebrow-label">CREATE A PROJECT</div>
                            <h2 class="card-title">What are we researching today?</h2>
                            <p class="card-subtitle">Define a topic and your AI research team will turn its findings into a structured article.</p>
                        </div>
                        <div class="step-chip">01 <span>INPUT</span></div>
                    </div>
                """)

                topic_input = gr.Textbox(
                    label="Research topic",
                    placeholder="e.g. Agentic AI in financial technology, Autonomous robotics in healthcare...",
                    lines=3,
                    max_lines=5,
                    max_length=200,
                    elem_id="topic-input",
                )

                with gr.Row(elem_id="generate-row"):
                    gr.HTML("""
                        <div class="workflow-note">
                            <span class="workflow-dot"></span>
                            <span class="stage-tag">Live Web Search</span>
                            <span class="workflow-arrow">→</span>
                            <span class="stage-tag">AI Researcher</span>
                            <span class="workflow-arrow">→</span>
                            <span class="stage-tag">AI Writer</span>
                        </div>
                    """)
                    generate_btn = gr.Button("Generate article  ↗", variant="primary", elem_id="generate-btn")

            with gr.Row(elem_id="metrics-row"):
                with gr.Column(elem_classes=["metric-card"], min_width=0):
                    saved_count = gr.HTML(
                        get_saved_card_html(get_article_count()),
                        elem_id="saved-count-card",
                    )
                with gr.Column(elem_classes=["metric-card"], min_width=0):
                    gr.HTML("""
                        <div class="metric-card-inner">
                            <div class="metric-header">
                                <span class="metric-label">PIPELINE</span>
                                <span class="metric-icon">⚡</span>
                            </div>
                            <div class="metric-value">Research → Write</div>
                            <div class="metric-sub">CrewAI 2-Stage Sequential</div>
                        </div>
                    """)
                with gr.Column(elem_classes=["metric-card"], min_width=0):
                    gr.HTML("""
                        <div class="metric-card-inner">
                            <div class="metric-header">
                                <span class="metric-label">ENGINE & SEARCH</span>
                                <span class="metric-icon">🌐</span>
                            </div>
                            <div class="metric-value">Groq + DuckDuckGo</div>
                            <div class="metric-sub">Fast Llama 3 Inference</div>
                        </div>
                    """)

            with gr.Column(elem_id="article-section", min_width=0):
                with gr.Row(elem_id="article-header-row"):
                    with gr.Column(scale=1, min_width=0):
                        gr.HTML("""
                            <div class="eyebrow-label">02 / OUTPUT</div>
                            <h2 class="article-heading">Article workspace</h2>
                            <p class="article-subheading">Review, copy, or export your generated research article.</p>
                        """)
                    with gr.Row(scale=0, elem_id="article-actions"):
                        copy_btn = gr.Button("📋  Copy article", elem_id="copy-btn")
                        export_file = gr.DownloadButton(
                            "↓  Download Markdown",
                            value=None,
                            elem_id="download-btn",
                        )

                article_status = gr.Markdown(
                    "Choose an article from the sidebar or generate a new one.",
                    elem_id="article-status",
                )
                article_output = gr.Markdown(
                    value=initial_article["content"] if initial_article else
                    "### Your article will appear here\n\nStart a new research project or select an item from Recent History.",
                    elem_id="article-output",
                )

            gr.HTML("""
                <div class="app-footer">
                    <span>RESEARCHOS</span><span>Built with CrewAI + Groq</span>
                </div>
            """)

    generate_btn.click(
        fn=create_article,
        inputs=[topic_input],
        outputs=[article_output, history_radio, article_status, export_file],
        show_progress="full",
    ).then(
        fn=lambda: get_saved_card_html(get_article_count()),
        inputs=None,
        outputs=saved_count,
    )

    history_radio.change(
        fn=load_history,
        inputs=history_radio,
        outputs=[article_output, article_status],
    )

    refresh_btn.click(
        fn=refresh_history,
        inputs=None,
        outputs=[history_radio, article_output, article_status],
    ).then(
        fn=lambda: get_saved_card_html(get_article_count()),
        inputs=None,
        outputs=saved_count,
    )

    new_research_btn.click(
        fn=lambda: ("", "Ready for a new research project. Type your topic above."),
        inputs=None,
        outputs=[topic_input, article_status],
    )

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1)
    demo.launch(
        theme=gr.themes.Base(
            primary_hue="violet",
            secondary_hue="cyan",
            neutral_hue="slate",
        ),
        css=css_content,
        js=js_content,
    )
