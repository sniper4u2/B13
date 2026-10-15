"""
B13 UI Module - Interface and interaction layer
Extracted from HF space sofienehmz/gaia-agent-unit5
"""

CSS = """
.gradio-container {
    max-width: 1400px !important;
}
"""

def make_app():
    """Create and configure the Gradio application"""
    import gradio as gr
    from agent import create_agent
    from b13.runtime import AgentSession

    # Create agent + wrap in the session runtime (MYTHOS F5: single runtime path).
    agent = create_agent()
    session = AgentSession(agent)

    # Define interface
    with gr.Blocks(theme=gr.themes.Base(), css=CSS) as demo:
        gr.Markdown("# B13 - Autonomous AI Agent")
        gr.Markdown("Tool-enabled reasoning agent. Loads the trained B13 adapter when present (B13_ADAPTER_PATH).")

        with gr.Row():
            with gr.Column():
                input_task = gr.Textbox(label="Task Description", placeholder="Enter task...")
                submit_btn = gr.Button("Execute", variant="primary")

            with gr.Column():
                output_result = gr.Textbox(label="Result", lines=10)

        def run_task(task):
            import asyncio
            return asyncio.run(session.execute_task(task))

        submit_btn.click(
            fn=run_task,
            inputs=input_task,
            outputs=output_result
        )

    return demo
