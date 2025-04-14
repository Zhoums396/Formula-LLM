from argparse import ArgumentParser
import re
import gradio as gr
import os
import secrets
from PIL import Image
import warnings
from openai import OpenAI
import requests

# 忽视所有警告
warnings.filterwarnings("ignore")

API_KEY = "sk-9c701f6795fb48d09703f9b21ed47ce4"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen2.5-vl-7b-instruct"

ocr_client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)
IMAGE_BASE_URL = "http://image-server.s.webace-i3c.com"  # 图片服务器 endpoint


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


def get_ocr_response(image, shouldConvert=False):
    # 获取上传文件的目录
    uploaded_file_dir = os.environ.get("GRADIO_TEMP_DIR", "/tmp/vl")
    os.makedirs(uploaded_file_dir, exist_ok=True)

    # 创建临时文件路径
    name = f"tmp{secrets.token_hex(20)}.jpg"
    filename = os.path.join(uploaded_file_dir, name)
    # 保存上传的图片
    if shouldConvert:
        new_img = Image.new(
            "RGB", size=(image.width, image.height), color=(255, 255, 255)
        )
        new_img.paste(image, (0, 0), mask=image)
        image = new_img
    image.save(filename)

    image_id = upload_image(filename)
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
    print("filename: {}".format(filename))
    response = ocr_client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0,
    )

    # 清理临时文件
    os.remove(filename)

    content = response.choices[0].message.content
    return content


def vl_chat_bot(image, sketchpad, state):
    current_tab_index = state["tab_index"]
    image_description = None
    # Upload
    if current_tab_index == 0:
        if image is not None:
            image_description = get_ocr_response(image)
    # Sketch
    elif current_tab_index == 1:
        # print(sketchpad)
        if sketchpad and sketchpad["composite"]:
            image_description = get_ocr_response(sketchpad["composite"], True)

    print("---- ocr response ----\n{}\n\n".format(image_description))
    image_description = replace_latex_delimiters(image_description)
    print("---- ocr response ----\n{}\n\n".format(image_description))
    yield image_description


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
        with gr.Column():
            with gr.Tabs() as input_tabs:
                with gr.Tab("Upload"):
                    input_image = (gr.Image(type="pil", label="Upload"),)
                with gr.Tab("Sketch"):
                    input_sketchpad = gr.Sketchpad(
                        type="pil", label="Sketch", layers=False
                    )
            input_tabs.select(fn=tabs_select, inputs=[state])
            with gr.Row():
                with gr.Column():
                    clear_btn = gr.ClearButton([*input_image, input_sketchpad])
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
            inputs=[*input_image, input_sketchpad, state],
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
