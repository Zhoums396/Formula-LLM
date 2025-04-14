from argparse import ArgumentParser
import re
import time
import gradio as gr
import os
import warnings
from openai import OpenAI
import requests

from utils import KNOWLEDGE_BASE

# 忽视所有警告
warnings.filterwarnings("ignore")

API_KEY = "sk-9c701f6795fb48d09703f9b21ed47ce4"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen2.5-vl-7b-instruct"

ocr_client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)
IMAGE_BASE_URL = "http://image-server.s.webace-i3c.com"  # 根据你的服务器配置调整
if not os.path.exists(KNOWLEDGE_BASE):
    os.makedirs(KNOWLEDGE_BASE)


def get_args():
    parser = ArgumentParser()
    parser.add_argument(
        "--cpu-only", action="store_true", help="Run demo with CPU only"
    )
    parser.add_argument(
        "--share",
        action="store_true",
        default=False,
        help="Create a publicly shareable link for the interface.",
    )
    parser.add_argument(
        "--inbrowser",
        action="store_true",
        default=False,
        help="Automatically launch the interface in a new tab on the default browser.",
    )
    parser.add_argument(
        "--server-port", type=int, default=7863, help="Demo server port."
    )
    parser.add_argument(
        "--server-name", type=str, default="localhost", help="Demo server name."
    )

    args = parser.parse_args()
    return args


def upload_image(file_path):
    """上传图片并返回图片 ID"""
    upload_url = f"{IMAGE_BASE_URL}/upload"

    with open(file_path, "rb") as f:
        files = {"file": ("test_image.png", f, "image/png")}
        response = requests.post(upload_url, files=files)

    if response.status_code != 200:
        print(f"Upload failed with status code: {response.status_code}")
        print(f"Response: {response.text}")
        return

    image_id = response.json()
    return image_id


def replace_latex_delimiters(text: str):
    text = text.replace("<think>", "").replace("</think>", "").replace("&", "")
    # text = re.sub(r"<think>.*</think>", "", text, flags=re.DOTALL)

    patterns = [
        r"\\begin\{equation\}(.*?)\\end\{equation\}",  # \begin{equation} ... \end{equation}
        r"\\begin\{aligned\}(.*?)\\end\{aligned\}",  # \begin{aligned} ... \end{aligned}
        r"\\begin\{alignat\}(.*?)\\end\{alignat\}",  # \begin{alignat} ... \end{alignat}
        r"\\begin\{align\}(.*?)\\end\{align\}",  # \begin{align} ... \end{align}
        r"\\begin\{gather\}(.*?)\\end\{gather\}",  # \begin{gather} ... \end{gather}
        r"\\begin\{CD\}(.*?)\\end\{CD\}",  # \begin{CD} ... \end{CD}
    ]
    # 替换所有匹配的模式
    for pattern in patterns:
        text = re.sub(pattern, r" $$ \1 $$ ", text, flags=re.DOTALL)
    # 定义正则表达式模式
    patterns = [
        r"\\\[\n(.*?)\n\\\]",  # \[ ... \]
        r"\\\(\n(.*?)\n\\\)",  # \( ... \)
    ]
    # 替换所有匹配的模式
    for pattern in patterns:
        text = re.sub(pattern, r" $$ \1 $$ ", text, flags=re.DOTALL)
    # 定义正则表达式模式
    patterns = [
        r"\\\[(.*?)\\\]",  # \[ ... \]
        r"\\\((.*?)\\\)",  # \( ... \)
    ]
    # 替换所有匹配的模式
    for pattern in patterns:
        text = re.sub(pattern, r" $ \1 $ ", text, flags=re.DOTALL)
    return text


def get_ocr_response(image_path):
    image_id = upload_image(image_path)
    download_url = f"{IMAGE_BASE_URL}/download/{image_id}"

    # 调用Qwen2-VL-7B-Instruct模型处理图片
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful assistant."}],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Please extract the content in this image, ensuring that any LaTeX formulas are correctly transcribed, ensuring that any Tables are displayed in markdown format. Please do not reply to extra content and maintain the original language.",
                },
                {"type": "image_url", "image_url": {"url": f"{download_url}"}},
            ],
        },
    ]
    response = ocr_client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0,
    )

    content = response.choices[0].message.content
    content = replace_latex_delimiters(content)
    return content


def process_image(file_path: str):
    name = os.path.basename(file_path)
    name = name.split(".")[0]
    print(f"---- processing {name} ----")
    try:
        image_description = get_ocr_response(file_path)
        # 写入本地文件
        with open(f"{KNOWLEDGE_BASE}/{name}.md", "w",encoding='utf-8') as f:
            f.write(image_description)
        yield image_description

    except Exception as e:
        print(f"---- error ----\n{e}")
        yield str(e)


def vl_chat_bot(path):
    if not os.path.exists(path):
        return "input image folder path not exits."

    if os.path.isfile(path):
        # 如果是文件直接处理
        yield from process_image(path)
    elif os.path.isdir(path):
        image_files = [
            f for f in os.listdir(path) if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
        total_files = len(image_files)

        for index, file in enumerate(image_files):
            file_path = os.path.join(path, file)
            image_description = next(process_image(file_path))

            progress = (index + 1) / total_files * 100
            yield f"# Progress: {progress:.2f}% ({index + 1}/{total_files})\n\n" + image_description

        time.sleep(1)
        yield "All images processed."


css = """
#qwen-md .katex-display { display: inline; }
#qwen-md .katex-display>.katex { display: inline; }
#qwen-md .katex-display>.katex>.katex-html { display: inline; }
"""


def tabs_select(e: gr.SelectData, _state):
    _state["tab_index"] = e.index


# 创建Gradio接口
with gr.Blocks(css=css) as demo:
    gr.HTML(
        """\
<p align="center"><img src="https://modelscope.oss-cn-beijing.aliyuncs.com/resource/qwen.png" style="height: 60px"/><p>"""
        """<center><font size=8>📖 Qwen2.5-VL Demo</center>"""
        """\
<center><font size=3>This WebUI is based on Qwen2.5-VL for formula image OCR.</center>"""
    )
    state = gr.State({"tab_index": 0})
    with gr.Row():
        with gr.Row():
            with gr.Column():
                input_folder = gr.Textbox(
                    label="input your absolute image folder path",
                    value="images",
                    min_width=500,
                )
                with gr.Row():
                    with gr.Column():
                        clear_btn = gr.ClearButton([input_folder])
                    with gr.Column():
                        submit_btn = gr.Button("Submit", variant="primary")
        with gr.Column():
            output_md = gr.Markdown(
                label="answer",
                line_breaks=True,
                latex_delimiters=[
                    {
                        "left": "$$",
                        "right": "$$",
                        "display": True,
                    },
                    {
                        "left": "$",
                        "right": "$",
                        "display": True,
                    },
                ],
                elem_id="qwen-md",
            )
        submit_btn.click(
            fn=vl_chat_bot,
            inputs=[input_folder],
            outputs=output_md,
        )

if __name__ == "__main__":
    args = get_args()
    demo.launch(
        share=args.share,
        inbrowser=args.inbrowser,
        server_port=args.server_port,
        server_name=args.server_name,
    )
