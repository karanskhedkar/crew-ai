import os
import time
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
    delete_article,
    clear_all_articles,
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
        raw_title = (item["title"] or item["topic"] or "Untitled Research").strip()
        raw_title = raw_title.lstrip("# ").strip()
        # Clean up whitespace and keep a clean single line title
        clean_title = " ".join(raw_title.split())
        if len(clean_title) > 60:
            truncated = clean_title[:59].rsplit(" ", 1)[0]
            display_title = (truncated if truncated else clean_title[:59]) + "…"
        else:
            display_title = clean_title

        try:
            dt = datetime.fromisoformat(item["created_at"])
            date_label = dt.strftime("%b %d, %H:%M")
        except Exception:
            date_label = item["created_at"][:16].replace("T", " ")

        choices.append((f"{display_title}\n{date_label}", str(item["id"])))
    return choices


def load_history(article_id):
    if not article_id:
        return (
            "### Your article will appear here\n\nStart a new research project or select an item from Recent History.",
            "Choose an article from the sidebar or generate a new one.",
            None,
        )
    article = get_article(int(article_id))
    if not article:
        return "This article could not be found.", "The selected history item is unavailable.", None

    export_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".md",
            prefix="research_article_", delete=False
        ) as handle:
            handle.write(article["content"])
            export_path = handle.name
    except Exception:
        export_path = None

    return article["content"], f"Loaded: {article['title']}", export_path


def delete_history_item(article_id_to_delete, current_selected_id):
    if not article_id_to_delete:
        choices = get_history_choices()
        return (
            gr.update(choices=choices),
            gr.update(),
            gr.update(),
            get_saved_card_html(get_article_count()),
            gr.update(),
        )

    try:
        del_id = int(str(article_id_to_delete).strip())
        delete_article(del_id)
    except Exception as exc:
        print(f"Error deleting article {article_id_to_delete}: {exc}")

    choices = get_history_choices()
    new_count = get_article_count()

    # If the deleted article was currently selected or loaded, reset view
    is_current = (
        current_selected_id is not None
        and str(article_id_to_delete).strip() == str(current_selected_id).strip()
    )

    if is_current:
        new_selected = None
        new_content = "### Your article will appear here\n\nStart a new research project or select an item from Recent History."
        new_status = "Article deleted from history."
        new_export = None
    else:
        new_selected = current_selected_id
        new_content = gr.update()
        new_status = "Article deleted from history."
        new_export = gr.update()

    return (
        gr.update(choices=choices, value=new_selected),
        new_content,
        new_status,
        get_saved_card_html(new_count),
        new_export,
    )


def delete_current_article(current_selected_id):
    if not current_selected_id:
        return (
            gr.update(),
            gr.update(),
            "No article currently selected to delete.",
            get_saved_card_html(get_article_count()),
            gr.update(),
        )
    return delete_history_item(current_selected_id, current_selected_id)


def create_article(topic, year=None):
    if not topic or not topic.strip():
        yield (
            "### Please enter a research topic\n\nType your topic above and click Generate article to begin.",
            gr.update(),
            "Enter a research topic first.",
            None,
        )
        return

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

        # Stream research article generation with smooth real-time typewriter progression
        words = article_text.split(" ")
        total_words = len(words)
        chunk_step = max(3, min(6, total_words // 65)) if total_words > 0 else 4

        accumulated = []
        for i in range(0, total_words, chunk_step):
            accumulated.extend(words[i : i + chunk_step])
            stream_chunk = " ".join(accumulated)
            yield (
                stream_chunk,
                gr.update(),
                "✍️ Synthesizing research text…",
                None,
            )
            time.sleep(0.02)

        # Final yield with full article, updated history choices, status, and download file
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
    return (
        gr.update(choices=choices, value=None),
        "### Your article will appear here\n\nStart a new research project or select an item from Recent History.",
        "History refreshed.",
        None,
    )


def clear_all_history_action():
    clear_all_articles()
    choices = get_history_choices()
    return (
        gr.update(choices=choices, value=None),
        "### Your article will appear here\n\nStart a new research project or select an item from Recent History.",
        "All research history cleared.",
        get_saved_card_html(0),
        None,
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
initial_selected = None
initial_article = None

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
                value=None,
                label=None,
                container=False,
                elem_id="history-list",
                info="",
            )
            with gr.Row(elem_id="history-actions-row"):
                refresh_btn = gr.Button("↻   Refresh", elem_id="refresh-history-btn")
                clear_all_btn = gr.Button("🗑   Clear all", elem_id="clear-all-history-btn")

            # Hidden delete controls (hidden via CSS to preserve DOM presence)
            with gr.Row(elem_id="hidden-history-controls"):
                delete_target_id = gr.Textbox(elem_id="delete-target-id")
                delete_action_btn = gr.Button(elem_id="delete-action-btn")
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
                    generate_btn = gr.Button("Generate article  ↗", variant="primary", elem_id="generate-btn", interactive=False)

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
                        delete_article_btn = gr.Button("🗑  Delete article", elem_id="delete-article-btn")
                        export_file = gr.DownloadButton(
                            "↓  Download Markdown",
                            value=None,
                            elem_id="download-btn",
                        )

                article_status = gr.Markdown(
                    "Choose an article from the sidebar or generate a new one.",
                    elem_id="article-status",
                )
                research_loader = gr.HTML(
                    """
                    <div id="research-loader" class="research-loader" style="display: none;">
                        <!-- Flowing Top Neon Progress Beam -->
                        <div class="loader-beam-track">
                            <div class="loader-beam-fill"></div>
                        </div>

                        <div class="loader-backdrop-glow"></div>

                        <div class="loader-header">
                            <div class="reactor-container">
                                <div class="loader-reactor">
                                    <div class="reactor-ring outer">
                                        <span class="orbit-spark s1"></span>
                                        <span class="orbit-spark s2"></span>
                                    </div>
                                    <div class="reactor-ring middle"></div>
                                    <div class="reactor-ring inner"></div>
                                    <div class="reactor-core">
                                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                                        </svg>
                                    </div>
                                </div>
                                <!-- Audio-Visual AI Spectrum Equalizer -->
                                <div class="ai-equalizer" title="Autonomous LLM Inference Stream">
                                    <span class="eq-bar eq-1"></span>
                                    <span class="eq-bar eq-2"></span>
                                    <span class="eq-bar eq-3"></span>
                                    <span class="eq-bar eq-4"></span>
                                    <span class="eq-bar eq-5"></span>
                                    <span class="eq-bar eq-6"></span>
                                    <span class="eq-bar eq-7"></span>
                                    <span class="eq-bar eq-8"></span>
                                    <span class="eq-bar eq-9"></span>
                                </div>
                            </div>

                            <div class="loader-titles">
                                <div class="loader-badge">
                                    <span class="loader-pulse-dot"></span>
                                    <span class="loader-badge-text">AUTONOMOUS MULTI-AGENT INTELLIGENCE</span>
                                </div>
                                <h3 class="loader-heading">Synthesizing research article...</h3>
                                <p class="loader-sub">Researcher & writer agents searching live sources, analyzing insights, and formatting publication.</p>
                            </div>

                            <div class="loader-timer-pill" id="loader-timer">
                                <span class="timer-dot"></span>
                                <span class="timer-label">ELAPSED</span>
                                <span id="loader-timer-text">00:00</span>
                            </div>
                        </div>

                        <!-- 4-Stage Agent Timeline -->
                        <div class="loader-stages">
                            <div class="loader-stage active" id="stage-1" data-stage="1">
                                <div class="stage-radar"></div>
                                <div class="stage-top">
                                    <div class="stage-icon-wrap">
                                        <span class="stage-num">1</span>
                                        <span class="stage-check">✓</span>
                                    </div>
                                    <div class="stage-status-tag">Searching...</div>
                                </div>
                                <div class="stage-info">
                                    <div class="stage-name">Live Web Search</div>
                                    <div class="stage-desc">Scanning web for real-time sources & facts</div>
                                </div>
                            </div>

                            <div class="loader-stage" id="stage-2" data-stage="2">
                                <div class="stage-radar"></div>
                                <div class="stage-top">
                                    <div class="stage-icon-wrap">
                                        <span class="stage-num">2</span>
                                        <span class="stage-check">✓</span>
                                    </div>
                                    <div class="stage-status-tag">Pending</div>
                                </div>
                                <div class="stage-info">
                                    <div class="stage-name">AI Researcher</div>
                                    <div class="stage-desc">Extracting insights & key trends</div>
                                </div>
                            </div>

                            <div class="loader-stage" id="stage-3" data-stage="3">
                                <div class="stage-radar"></div>
                                <div class="stage-top">
                                    <div class="stage-icon-wrap">
                                        <span class="stage-num">3</span>
                                        <span class="stage-check">✓</span>
                                    </div>
                                    <div class="stage-status-tag">Pending</div>
                                </div>
                                <div class="stage-info">
                                    <div class="stage-name">AI Writer</div>
                                    <div class="stage-desc">Synthesizing comprehensive article</div>
                                </div>
                            </div>

                            <div class="loader-stage" id="stage-4" data-stage="4">
                                <div class="stage-radar"></div>
                                <div class="stage-top">
                                    <div class="stage-icon-wrap">
                                        <span class="stage-num">4</span>
                                        <span class="stage-check">✓</span>
                                    </div>
                                    <div class="stage-status-tag">Pending</div>
                                </div>
                                <div class="stage-info">
                                    <div class="stage-name">Final Polish</div>
                                    <div class="stage-desc">Formatting executive summary & markdown</div>
                                </div>
                            </div>
                        </div>

                        <!-- Skeleton Shimmer Document Preview -->
                        <div class="loader-skeleton">
                            <div class="skeleton-header-line">
                                <div class="skeleton-line s-title"></div>
                                <div class="skeleton-pill"></div>
                            </div>
                            <div class="skeleton-line s-line-1"></div>
                            <div class="skeleton-line s-line-2"></div>
                            <div class="skeleton-line s-line-3"></div>
                        </div>
                    </div>
                    """,
                    elem_id="loader-html-box",
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
        outputs=[article_output, article_status, export_file],
    )

    refresh_btn.click(
        fn=refresh_history,
        inputs=None,
        outputs=[history_radio, article_output, article_status, export_file],
    ).then(
        fn=lambda: get_saved_card_html(get_article_count()),
        inputs=None,
        outputs=saved_count,
    )

    clear_all_btn.click(
        fn=clear_all_history_action,
        inputs=None,
        outputs=[history_radio, article_output, article_status, saved_count, export_file],
    )

    delete_action_btn.click(
        fn=delete_history_item,
        inputs=[delete_target_id, history_radio],
        outputs=[history_radio, article_output, article_status, saved_count, export_file],
    )

    delete_article_btn.click(
        fn=delete_current_article,
        inputs=[history_radio],
        outputs=[history_radio, article_output, article_status, saved_count, export_file],
    )

    topic_input.input(
        fn=lambda t: gr.update(interactive=bool(t and t.strip())),
        inputs=[topic_input],
        outputs=[generate_btn],
        queue=False,
        show_progress="hidden",
    )

    new_research_btn.click(
        fn=lambda: (
            "",
            gr.update(interactive=False),
            gr.update(value=None),
            "### Your article will appear here\n\nStart a new research project or select an item from Recent History.",
            "Choose an article from the sidebar or generate a new one.",
            None,
        ),
        inputs=None,
        outputs=[topic_input, generate_btn, history_radio, article_output, article_status, export_file],
    )


def api_delete_article(article_id: int):
    try:
        success = delete_article(int(article_id))
        return {"success": success, "count": get_article_count()}
    except Exception as exc:
        return {"success": False, "error": str(exc), "count": get_article_count()}


def api_clear_all_articles():
    try:
        deleted_count = clear_all_articles()
        return {"success": True, "count": 0, "deleted": deleted_count}
    except Exception as exc:
        return {"success": False, "error": str(exc), "count": get_article_count()}


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1)
    app, local_url, _ = demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        theme=gr.themes.Base(
            primary_hue="violet",
            secondary_hue="cyan",
            neutral_hue="slate",
        ),
        css=css_content,
        js=js_content,
        prevent_thread_lock=True,
    )
    # Attach direct REST endpoints for instant, reliable history deletion
    app.add_api_route("/api/articles/{article_id}/delete", api_delete_article, methods=["POST"])
    app.add_api_route("/api/articles/clear-all", api_clear_all_articles, methods=["POST"])
    demo.block_thread()
