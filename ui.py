import html

import gradio as gr

from agent import MODEL_ID
from runtime import B13Runtime


CSS = r"""
html,
body {
    margin: 0 !important;
    padding: 0 !important;
    background: #07090d !important;
}

body {
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif !important;
}

footer {
    display: none !important;
}

.gradio-container {
    max-width: 100% !important;
    width: 100% !important;
    min-height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
    background:
        radial-gradient(
            650px 450px at 5% -10%,
            rgba(103,232,249,.055),
            transparent 65%
        ),
        radial-gradient(
            650px 450px at 95% -10%,
            rgba(139,92,246,.055),
            transparent 65%
        ),
        #07090d !important;
}

#b13-app {
    min-height: 100vh;
    color: #edf2f7;
}

#b13-header {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    box-sizing: border-box;
    border-bottom: 1px solid rgba(255,255,255,.065);
    background: rgba(7,9,13,.94);
}

.b13-brand {
    display: flex;
    align-items: center;
    gap: 10px;
}

.b13-mark {
    width: 31px;
    height: 31px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(103,232,249,.22);
    border-radius: 8px;
    color: #67e8f9;
    background: rgba(103,232,249,.045);
    font-size: 9px;
    font-weight: 800;
}

.b13-name {
    color: #f1f5f9;
    font-size: 15px;
    font-weight: 750;
}

.b13-subtitle {
    color: #596475;
    font-size: 9px;
}

.b13-ready {
    display: flex;
    align-items: center;
    gap: 7px;
    color: #8994a5;
    font-size: 9px;
    font-weight: 700;
}

.b13-ready-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #4ade80;
    box-shadow: 0 0 12px rgba(74,222,128,.45);
}

#b13-workspace {
    display: grid !important;
    grid-template-columns:
        235px
        minmax(0, 1fr)
        255px !important;
    min-height: calc(100vh - 60px);
}

.b13-side {
    min-width: 0 !important;
    padding: 22px 18px !important;
    border-right: 1px solid rgba(255,255,255,.055) !important;
    background: rgba(8,11,16,.42) !important;
}

.b13-right {
    border-right: 0 !important;
    border-left: 1px solid rgba(255,255,255,.055) !important;
}

.b13-label {
    margin-bottom: 18px;
    color: #4e5969;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: .17em;
}

.b13-heading {
    margin-bottom: 7px;
    color: #eef2f7;
    font-size: 18px;
    font-weight: 730;
}

.b13-muted {
    color: #697487;
    font-size: 10px;
    line-height: 1.65;
}

.b13-profile {
    padding: 14px 0;
    border-top: 1px solid rgba(255,255,255,.05);
}

.b13-profile-label {
    margin-bottom: 5px;
    color: #4c5767;
    font-size: 7px;
    font-weight: 800;
    letter-spacing: .15em;
}

.b13-profile-value {
    color: #b8c2d0;
    font-size: 10px;
    word-break: break-word;
}

.b13-tool {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 10px 0;
    color: #a7b2c1;
    font-size: 10px;
}

.b13-tool-dot {
    width: 5px;
    height: 5px;
    flex-shrink: 0;
    border-radius: 50%;
    background: #67e8f9;
}

#b13-center {
    min-width: 0 !important;
    display: flex !important;
    flex-direction: column !important;
}

#b13-center-header {
    height: 50px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 21px;
    border-bottom: 1px solid rgba(255,255,255,.05);
}

.b13-center-title {
    color: #8d98a9;
    font-size: 9px;
    font-weight: 750;
    letter-spacing: .12em;
}

.b13-center-meta {
    color: #505b6b;
    font-size: 9px;
}

#b13-chat {
    flex: 1 !important;
    min-height: 480px !important;
    border: 0 !important;
    background: transparent !important;
}

#b13-chat .wrap {
    border: 0 !important;
    background: transparent !important;
}

#b13-chat .message {
    border-color: rgba(255,255,255,.055) !important;
    border-radius: 13px !important;
}

#b13-chat .bot {
    background: rgba(15,19,27,.72) !important;
}

#b13-chat .user {
    background: rgba(103,232,249,.045) !important;
}

#b13-command {
    padding: 12px 16px 14px !important;
    border-top: 1px solid rgba(255,255,255,.065);
    background: rgba(7,9,13,.97);
}

#b13-prompt {
    width: 100% !important;
    border: 1px solid rgba(255,255,255,.10) !important;
    border-radius: 12px !important;
    background: #0d1118 !important;
}

#b13-prompt .wrap {
    border: 0 !important;
    background: transparent !important;
}

#b13-prompt textarea {
    display: block !important;
    width: 100% !important;
    min-height: 70px !important;
    padding: 14px !important;
    box-sizing: border-box !important;
    border: 0 !important;
    outline: none !important;
    background: transparent !important;
    color: #edf2f7 !important;
    font-size: 13px !important;
    line-height: 1.55 !important;
    resize: vertical !important;
    pointer-events: auto !important;
    user-select: text !important;
    cursor: text !important;
}

#b13-prompt textarea::placeholder {
    color: #505b6a !important;
}

#b13-prompt:focus-within {
    border-color: rgba(103,232,249,.22) !important;
}

#b13-actions {
    margin-top: 7px !important;
}

#b13-run button,
#b13-clear button {
    min-height: 40px !important;
    border-radius: 9px !important;
}

#b13-run button {
    background: rgba(103,232,249,.09) !important;
    border: 1px solid rgba(103,232,249,.22) !important;
    color: #a9eff8 !important;
    font-size: 10px !important;
    font-weight: 750 !important;
}

#b13-clear button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,.075) !important;
    color: #687386 !important;
    font-size: 9px !important;
}

#b13-quick {
    margin-top: 7px !important;
    overflow-x: auto !important;
}

#b13-quick button {
    min-height: 27px !important;
    border-radius: 999px !important;
    border: 1px solid rgba(255,255,255,.065) !important;
    background: rgba(255,255,255,.018) !important;
    color: #687386 !important;
    font-size: 9px !important;
    white-space: nowrap !important;
}

.b13-status {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 17px;
}

.b13-status-dot {
    width: 7px;
    height: 7px;
    flex-shrink: 0;
    border-radius: 50%;
}

.b13-status-name {
    color: #c8d1dd;
    font-size: 10px;
    font-weight: 750;
}

.b13-runtime {
    padding: 15px 0;
    border-top: 1px solid rgba(255,255,255,.05);
}

.b13-runtime-label {
    margin-bottom: 9px;
    color: #4d5868;
    font-size: 7px;
    font-weight: 800;
    letter-spacing: .15em;
}

.b13-runtime-value {
    color: #8f9bab;
    font-size: 9px;
    line-height: 1.55;
    word-break: break-word;
}

.b13-event {
    display: flex;
    gap: 8px;
    margin: 9px 0;
    color: #667285;
    font-size: 9px;
}

.b13-event.current {
    color: #aeb9c8;
}

.b13-event-dot {
    width: 5px;
    height: 5px;
    margin-top: 4px;
    flex-shrink: 0;
    border-radius: 50%;
    background: #303947;
}

.b13-event.current .b13-event-dot {
    background: #67e8f9;
    box-shadow: 0 0 8px rgba(103,232,249,.4);
}

@media (max-width: 1050px) {
    #b13-workspace {
        grid-template-columns:
            210px
            minmax(0,1fr) !important;
    }

    .b13-right {
        display: none !important;
    }
}

@media (max-width: 700px) {
    #b13-workspace {
        display: block !important;
    }

    .b13-side {
        display: none !important;
    }

    #b13-center {
        min-height: calc(100vh - 60px);
    }

    #b13-chat {
        min-height: 400px !important;
    }

    #b13-command {
        padding: 9px !important;
    }
}
"""


def _status(state, detail, color):
    return f"""
<div class="b13-status">
    <span
        class="b13-status-dot"
        style="
            background:{color};
            box-shadow:0 0 12px {color};
        "
    ></span>
    <span class="b13-status-name">
        {html.escape(state)}
    </span>
</div>

<div class="b13-runtime">
    <div class="b13-runtime-label">
        CURRENT ACTIVITY
    </div>

    <div class="b13-runtime-value">
        {html.escape(detail)}
    </div>
</div>
"""


def _timeline(events):
    return f"""
<div class="b13-runtime">
    <div class="b13-runtime-label">
        EXECUTION TIMELINE
    </div>

    {
        "".join(
            f'''
            <div class="b13-event{" current" if i == len(events)-1 else ""}">
                <span class="b13-event-dot"></span>
                <span>{html.escape(event)}</span>
            </div>
            '''
            for i, event in enumerate(events)
        )
    }
</div>
"""


def _session(run, elapsed=None):

    text = (
        f"RUN {run:02d} · HUGGING FACE INFERENCE"
    )

    if elapsed is not None:
        text += f" · {elapsed:.1f}s"

    return f"""
<div class="b13-runtime">
    <div class="b13-runtime-label">
        SESSION
    </div>

    <div class="b13-runtime-value">
        {html.escape(text)}
    </div>
</div>
"""


def _execute(
    task,
    history,
    runtime,
):

    history = list(history or [])

    if not (task or "").strip():
        return (
            history,
            "",
            runtime,
            _status(
                "READY",
                "Enter a task to begin.",
                "#4ade80",
            ),
            _timeline(["B13 ready"]),
            _session(
                runtime.run_count
            ),
        )

    task = task.strip()

    history.append(
        {
            "role": "user",
            "content": task,
        }
    )

    result = runtime.execute(task)

    if result["success"]:

        answer = result["answer"] or (
            "B13 completed the task without "
            "returning a textual result."
        )

        history.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        status = _status(
            "COMPLETE",
            "B13 returned a final response.",
            "#4ade80",
        )

    else:

        history.append(
            {
                "role": "assistant",
                "content": (
                    "B13 could not complete this run.\n\n"
                    f"Technical error: {result['error']}"
                ),
            }
        )

        status = _status(
            "ERROR",
            result["error"],
            "#ff6f91",
        )

    return (
        history,
        "",
        runtime,
        status,
        _timeline(result["events"]),
        _session(
            result["run"],
            result["elapsed"],
        ),
    )


def _clear():
    runtime = B13Runtime()

    return (
        [],
        "",
        runtime,
        _status(
            "READY",
            "Waiting for a task.",
            "#4ade80",
        ),
        _timeline(["B13 ready"]),
        _session(0),
    )


def make_app():

    runtime = gr.State(B13Runtime())

    with gr.Blocks(
        title="B13",
    ) as demo:

        with gr.Column(
            elem_id="b13-app"
        ):

            gr.HTML(
                """
<header id="b13-header">

    <div class="b13-brand">

        <div class="b13-mark">
            B13
        </div>

        <div class="b13-name">
            B13
        </div>

        <div class="b13-subtitle">
            Autonomous Intelligence
        </div>

    </div>

    <div class="b13-ready">
        <span class="b13-ready-dot"></span>
        SYSTEM READY
    </div>

</header>
"""
            )

            with gr.Row(
                elem_id="b13-workspace",
                equal_height=False,
            ):

                with gr.Column(
                    elem_classes=["b13-side"]
                ):

                    gr.HTML(
                        f"""
<div class="b13-label">
B13 CORE
</div>

<div class="b13-heading">
Agent runtime
</div>

<div class="b13-muted">
Code-based autonomous reasoning with configured
web capabilities.
</div>

<div class="b13-profile">
<div class="b13-profile-label">MODEL</div>
<div class="b13-profile-value">
{html.escape(MODEL_ID)}
</div>
</div>

<div class="b13-profile">
<div class="b13-profile-label">FRAMEWORK</div>
<div class="b13-profile-value">
smolagents
</div>
</div>

<div class="b13-profile">
<div class="b13-profile-label">AGENT</div>
<div class="b13-profile-value">
CodeAgent
</div>
</div>

<div class="b13-profile">
<div class="b13-profile-label">INFERENCE</div>
<div class="b13-profile-value">
Hugging Face
</div>
</div>

<div class="b13-profile">

<div class="b13-profile-label">
TOOLS
</div>

<div class="b13-tool">
<span class="b13-tool-dot"></span>
DuckDuckGo search
</div>

<div class="b13-tool">
<span class="b13-tool-dot"></span>
Webpage retrieval
</div>

<div class="b13-tool">
<span class="b13-tool-dot"></span>
Python execution
</div>

</div>
"""
                    )

                with gr.Column(
                    elem_id="b13-center"
                ):

                    gr.HTML(
                        """
<div id="b13-center-header">
    <div class="b13-center-title">
        AGENT WORKSPACE
    </div>

    <div class="b13-center-meta">
        Interactive session
    </div>
</div>
"""
                    )

                    chatbot = gr.Chatbot(
                        value=[],
                        show_label=False,
                        height=560,
                        elem_id="b13-chat",
                    )

                    with gr.Column(
                        elem_id="b13-command"
                    ):

                        prompt = gr.Textbox(
                            show_label=False,
                            placeholder=(
                                "Ask B13 to research, analyze, "
                                "compare, calculate, investigate "
                                "or explain…"
                            ),
                            lines=3,
                            max_lines=8,
                            autofocus=True,
                            interactive=True,
                            elem_id="b13-prompt",
                        )

                        with gr.Row(
                            elem_id="b13-actions"
                        ):

                            execute = gr.Button(
                                "EXECUTE",
                                variant="primary",
                                elem_id="b13-run",
                                scale=4,
                            )

                            clear = gr.Button(
                                "CLEAR SESSION",
                                variant="secondary",
                                elem_id="b13-clear",
                                scale=1,
                            )

                        with gr.Row(
                            elem_id="b13-quick"
                        ):

                            q1 = gr.Button("Research")
                            q2 = gr.Button("Analyze")
                            q3 = gr.Button("Compare")
                            q4 = gr.Button("Calculate")
                            q5 = gr.Button("Investigate")

                with gr.Column(
                    elem_classes=[
                        "b13-side",
                        "b13-right",
                    ]
                ):

                    gr.HTML(
                        '<div class="b13-label">RUN STATUS</div>'
                    )

                    status = gr.HTML(
                        _status(
                            "READY",
                            "Waiting for a task.",
                            "#4ade80",
                        )
                    )

                    timeline = gr.HTML(
                        _timeline(["B13 ready"])
                    )

                    gr.HTML(
                        f"""
<div class="b13-runtime">
<div class="b13-runtime-label">MODEL</div>
<div class="b13-runtime-value">
{html.escape(MODEL_ID)}
</div>
</div>

<div class="b13-runtime">
<div class="b13-runtime-label">PROVIDER</div>
<div class="b13-runtime-value">
Hugging Face Inference
</div>
</div>
"""
                    )

                    session = gr.HTML(
                        _session(0)
                    )

        outputs = [
            chatbot,
            prompt,
            runtime,
            status,
            timeline,
            session,
        ]

        execute.click(
            _execute,
            inputs=[
                prompt,
                chatbot,
                runtime,
            ],
            outputs=outputs,
        )

        prompt.submit(
            _execute,
            inputs=[
                prompt,
                chatbot,
                runtime,
            ],
            outputs=outputs,
        )

        clear.click(
            _clear,
            outputs=outputs,
        )

        q1.click(
            lambda: (
                "Research this topic and synthesize "
                "the relevant findings."
            ),
            outputs=prompt,
        )

        q2.click(
            lambda: (
                "Analyze this problem and identify "
                "the key findings, assumptions, "
                "and uncertainties."
            ),
            outputs=prompt,
        )

        q3.click(
            lambda: (
                "Compare the relevant alternatives "
                "and explain the trade-offs."
            ),
            outputs=prompt,
        )

        q4.click(
            lambda: (
                "Calculate this step by step and "
                "verify the result."
            ),
            outputs=prompt,
        )

        q5.click(
            lambda: (
                "Investigate this question and "
                "synthesize the available evidence."
            ),
            outputs=prompt,
        )

    return demo