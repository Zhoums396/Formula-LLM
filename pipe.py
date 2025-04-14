import os
import time
import warnings
import gradio as gr
from argparse import ArgumentParser
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量中读取配置
KNOWLEDGE_BASE = os.getenv("KNOWLEDGE_BASE", "knowledge_base")
API_KEY = os.getenv("API_KEY", "sk-9c701f6795fb48d09703f9b21ed47ce4")
BASE_URL = os.getenv("BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen-max")

from formula_from_images_dir import vl_chat_bot
from code_from_formulas_dir import code_chat
from json_from_codes_dir import code_chat as code_chat2
# prompt 引用原模块中的系统提示
from code_from_formulas_dir import system_prompt as prompt_md2code
from json_from_codes_dir import system_prompt as prompt_code2json

from inject2db import inject_to_knowledge_base
from search import search
from funcation_call import get_funcation_call_response
from funcation_call import system_prompt as prompt_function_call

warnings.filterwarnings("ignore")

coder_client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)


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
        "--server-port", type=int, default=7864, help="Demo server port."
    )
    parser.add_argument(
        "--server-name", type=str, default="localhost", help="Demo server name."
    )

    args = parser.parse_args()
    return args


def run_pipeline(image_folder, prompt_md2code, prompt_code2json):
    results = []
    
    # 检查路径是否存在
    if not os.path.exists(image_folder):
        return "错误：图像文件夹路径不存在，请检查路径是否正确。"
    
    try:
        # Step 1: 图片转 Markdown
        results.append("## 🖼️ Step 1: 图像转公式描述")
        image_count = len([f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        results.append(f"- 发现 {image_count} 个图像文件，开始处理...\n")
        
        for result in vl_chat_bot(image_folder):
            results.append(result)
        
        results.append("\n## 🧮 Step 2: 公式描述转 Python 代码")
        for result in code_chat(KNOWLEDGE_BASE, prompt_md2code):
            results.append(result)
        
        results.append("\n## 📦 Step 3: Python 代码转 JSON 工具描述")
        for result in code_chat2(KNOWLEDGE_BASE, prompt_code2json):
            results.append(result)
        
        results.append("\n## 🗄️ Step 4: 数据注入数据库")
        inject_to_knowledge_base()
        results.append("- 数据已成功注入到数据库")
        
        results.append("\n## ✅ 完整流程处理完成")
        results.append("知识库构建成功，现在可以进行公式问答！")
        
        return "\n".join(results)
    except Exception as e:
        return f"处理过程中发生错误：{str(e)}"

def query_formula(query):
    if not query.strip():
        return "请输入查询内容"
    
    # 调用函数回答查询
    response = get_funcation_call_response(query, prompt_function_call)
    return response

css = """
#qwen-md .katex-display { display: inline; }
#qwen-md .katex-display>.katex { display: inline; }
#qwen-md .katex-display>.katex>.katex-html { display: inline; }
"""

with gr.Blocks(css=css) as demo:
    gr.HTML(
        """\
<p align="center"><img src="https://modelscope.oss-cn-beijing.aliyuncs.com/resource/qwen.png" style="height: 60px"/><p>"""
        """<center><font size=6>📖 公式识别与问答系统</center>"""
        """\
<center><font size=3>基于Qwen2.5-VL和Qwen2.5-Coder的公式提取、代码生成与问答系统</center>"""
    )
    
    # 添加使用指南
    with gr.Accordion("📋 使用指南", open=True):
        gr.Markdown("""
        ### 系统功能概述
        
        本系统提供了完整的公式处理和问答流程：
        
        1. **公式提取**：上传数学公式图片，系统使用OCR提取图像中的公式并转为Markdown格式
        2. **公式代码化**：将提取的公式转换为Python函数代码
        3. **知识库构建**：将Python函数转换为JSON工具描述并构建向量数据库
        4. **公式问答**：输入查询，系统找到相关公式并计算结果
        5. **一键处理**：一次性完成上述所有步骤
        
        ### 使用流程
        
        * 建议按照标签页顺序操作，或直接使用"一键处理流程"标签页
        * 在"公式问答"环节，输入自然语言查询，系统会自动找到相关公式并进行计算
        """)
    
    with gr.Tabs() as tabs:
        with gr.TabItem("🖼️ 公式提取（图像→Markdown）"):
            with gr.Row():
                with gr.Column():
                    input_folder1 = gr.Textbox(label="📂 输入图像文件夹路径", value="images", min_width=500)
                    submit_vl = gr.Button("开始识别", variant="primary")
                with gr.Column():
                    output_md = gr.Markdown(label="📝 识别结果 Markdown", line_breaks=True, elem_id="qwen-md")
            
            submit_vl.click(fn=vl_chat_bot, inputs=[input_folder1], outputs=output_md)

        with gr.TabItem("🧮 公式代码化（Markdown→Python）"):
            with gr.Row():
                with gr.Column():
                    formula_path = gr.Textbox(label="📁 Markdown 公式描述文件夹路径", value=os.path.abspath(KNOWLEDGE_BASE))
                    prompt = gr.Textbox(label="🧾 系统提示词", value=prompt_md2code, lines=5)
                    submit_coder = gr.Button("生成代码", variant="primary")
                with gr.Column():
                    output_code = gr.Code(label="🔧 生成的 Python 代码", language="python", elem_id="qwen-code")
            
            submit_coder.click(fn=code_chat, inputs=[formula_path, prompt], outputs=output_code)

        with gr.TabItem("📦 知识库构建（Python→JSON+DB）"):
            with gr.Row():
                with gr.Column():
                    code_path = gr.Textbox(label="📁 Python 代码文件夹路径", value=os.path.abspath(KNOWLEDGE_BASE))
                    prompt2 = gr.Textbox(label="🧾 系统提示词", value=prompt_code2json, lines=5)
                    submit_json = gr.Button("生成 JSON 工具描述", variant="primary")
                with gr.Column():
                    output_json = gr.Code(label="📄 生成的 JSON 工具描述", language="json")
            
            submit_json.click(fn=code_chat2, inputs=[code_path, prompt2], outputs=output_json)
            
            with gr.Row():
                db_button = gr.Button("将数据注入到数据库", variant="primary")
                db_output = gr.Textbox(label="数据库操作结果")
            
            def inject_db_wrapper():
                inject_to_knowledge_base()
                return "数据已成功注入到数据库，知识库构建完成！"
                
            db_button.click(fn=inject_db_wrapper, inputs=[], outputs=db_output)

        with gr.TabItem("🔍 公式问答"):
            with gr.Row():
                with gr.Column():
                    query_input = gr.Textbox(label="输入查询", placeholder="例如：计算相对湿度，温度为25℃，湿球温度为20℃", lines=2)
                    query_button = gr.Button("提交查询", variant="primary")
                with gr.Column():
                    query_output = gr.Markdown(label="查询结果", elem_id="qwen-md")
            
            query_button.click(fn=query_formula, inputs=[query_input], outputs=query_output)

        with gr.TabItem("🚀 一键处理流程"):
            with gr.Row():
                with gr.Column():
                    pipeline_folder = gr.Textbox(label="📂 输入图像文件夹路径", value="images", min_width=500)
                    pipeline_button = gr.Button("启动完整流程", variant="primary", size="lg")
                with gr.Column():
                    pipeline_output = gr.Markdown(label="流程处理结果")
            
            def pipeline_wrapper(folder):
                return run_pipeline(folder, prompt_md2code, prompt_code2json)
                
            pipeline_button.click(
                fn=pipeline_wrapper, 
                inputs=[pipeline_folder], 
                outputs=pipeline_output
            )

if __name__ == "__main__":
    args = get_args()
    demo.launch(
        share=args.share,
        inbrowser=args.inbrowser,
        server_port=args.server_port,
        server_name=args.server_name,
    )