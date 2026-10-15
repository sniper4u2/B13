import gradio as gr
import sys
import os

# Add b13 module to path
sys.path.insert(0, os.path.dirname(__file__))

from b13.ui import CSS, make_app


demo = make_app()


if __name__ == "__main__":
    demo.launch(
        theme=gr.themes.Base(),
        css=CSS,
        show_error=True,
        server_name="0.0.0.0",
        server_port=7860,
    )