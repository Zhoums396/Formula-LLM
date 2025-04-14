from argparse import ArgumentParser
import json
import re
import time
import gradio as gr
import os
import warnings
from openai import OpenAI
import json_repair

# import pdfplumber
# from openai.types.chat import ChatCompletionChunk

# 忽视所有警告
warnings.filterwarnings("ignore")

API_KEY = "sk-9c701f6795fb48d09703f9b21ed47ce4"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen2.5-coder-7b-instruct"

coder_client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)
OUTPUT_DIR = "knowledge_base"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


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
        "--server-port", type=int, default=7862, help="Demo server port."
    )
    parser.add_argument(
        "--server-name", type=str, default="localhost", help="Demo server name."
    )

    args = parser.parse_args()
    return args


def extract_json_tool(text):
    pattern = r"```json\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        return json_str
    return None


def get_tool_response(formula_text, prompt):
    # 调用模型处理
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"""                
## Python Function 
{formula_text}

## Json Tool 
        """,
        },
    ]
    response = coder_client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0,
    )

    ans = response.choices[0].message.content
    return extract_json_tool(ans)


def process_md(file_path, prompt):
    name = os.path.basename(file_path)
    name = name.split(".")[0]
    print(f"---- processing {name} ----")
    try:
        with open(file_path, encoding="utf-8") as f:
            formula_text = f.read()
        json_tool = get_tool_response(formula_text, prompt)
        # 写入本地文件
        print(f"{OUTPUT_DIR}/{name}.json")
        with open(f"{OUTPUT_DIR}/{name}.json", "w") as f:
            json_object =  json_repair.repair_json(json_tool, ensure_ascii=False)
            f.write(f"{json_object}")
        yield json_tool

    except Exception as e:
        print(f"---- error ----\n{e}")
        yield str(e)


def code_chat(path, prompt):
    if not os.path.exists(path):
        return "input image folder path not exits."

    if os.path.isfile(path) and path.endswith(".md"):
        # 如果是文件直接处理
        yield from process_md(path, prompt)
    elif os.path.isdir(path):
        py_files = [
            f for f in os.listdir(path) if f.lower().endswith((".py", ".py3"))
        ]
        total_files = len(py_files)

        for index, file in enumerate(py_files):
            file_path = os.path.join(path, file)
            image_description = next(process_md(file_path, prompt))

            progress = (index + 1) / total_files * 100
            yield f"# Progress: {progress:.2f}% ({index + 1}/{total_files})\n\n" + image_description

        time.sleep(1)
        yield "All images processed."


system_prompt = r'''
Objective: Refer to the following example to generate Tool based on Function.
Requirements:
- Only generate Tool, do not provide unnecessary explanations.
- Generate corresponding "parameter" and "parameter_unit" fields for each Function parameter except that there is no unit. 
- Return in JSON format.

######################
-Example-
######################

# Python Function
```python
def calculate_overvoltage(I=None, h=None, d=None, k=9.18):
    """
    闪络时计算导线上产生的过电压

    参数：
    I : 雷电流 (单位：安培)，默认值为 None
    h : 导线离地高度 (单位：米)，默认值为 None
    d : 闪络点到导线的距离 (单位：米)，默认值为 None
    k : 系数，取决于雷电流反击的速率，默认值为 None

    返回：导线上产生的过电压 (单位：伏特)，如果任何输入为 None，则返回 None
    """
    if I is None:
        return ValueError("雷电流,不可以为空值。")
    elif h is None:
        return ValueError("导线离地高度,不可以为空值。")
    elif d is None:
        return ValueError("闪络点到导线的距离,不可以为空值。")
    elif k is None:
        return ValueError("系数(取决于雷电流反击的速率),不可以为空值。")
    else:
        # 计算过电压
        U = 30 * k * (h / d) * I
        return U
```

# Json Tool
```json
{
    "name": "calculate_overvoltage",
    "description": "闪络时计算导线上产生的过电压",
    "arguments": {
        "type": "object",
        "properties": {
            "I": {
                "type": "float",
                "description": "雷电流 (单位：安培)，默认值为 None",
            },
            "h": {
                "type": "float",
                "description": "导线离地高度 (单位：米)，默认值为 None",
            },
            "d": {
                "type": "float",
                "description": "闪络点到导线的距离 (单位：米)，默认值为 None",
            },
            "k": {
                "type": "float",
                "description": "系数，取决于雷电流反击的速率，默认值为 9.18",
            }
        },
        "required": ["I", "h", "d", "k"]
    }
}
```
'''

css = """
#qwen-md .katex-display { display: inline; }
#qwen-md .katex-display>.katex { display: inline; }
#qwen-md .katex-display>.katex>.katex-html { display: inline; }
"""

# 创建Gradio接口
with gr.Blocks(css=css) as demo:
    gr.HTML(
        """\
<p align="center"><img src="https://modelscope.oss-cn-beijing.aliyuncs.com/resource/qwen.png" style="height: 60px"/><p>"""
        """<center><font size=8>📖 Json Tool Demo</center>"""
        """\
<center><font size=3>This WebUI is based on Qwen2.5-Coder for json tool.</center>"""
    )
    state = gr.State({"tab_index": 0})
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="prompt", value=system_prompt)
            formula_path = gr.Textbox(
                label="Input Formulas Dir Path(Edit directly)",
                value=os.path.abspath(OUTPUT_DIR),
            )
            with gr.Row():
                with gr.Column():
                    clear_btn = gr.ClearButton([formula_path, prompt])
                with gr.Column():
                    submit_btn = gr.Button("Submit", variant="primary")
        with gr.Column():
            output_code = gr.Code(
                label="Generated Json Tool",
                language="json",
                elem_id="qwen-code",
            )
    submit_btn.click(
        fn=code_chat,
        inputs=[formula_path, prompt],
        outputs=output_code,
    )
    
if __name__ == "__main__":
    args = get_args()
    demo.launch(
        share=args.share,
        inbrowser=args.inbrowser,
        server_port=args.server_port,
        server_name=args.server_name,
    )
