import os
from sentence_transformers import SentenceTransformer
from utils import KNOWLEDGE_BASE
import sqlite3
import numpy as np

def read_all_md_files_from_knowledge_base():
    result = {}
    knowledge_base_path = KNOWLEDGE_BASE

    if not os.path.exists(knowledge_base_path):
        print(f"Error: The directory {knowledge_base_path} does not exist.")
        return result

    for filename in os.listdir(knowledge_base_path):
        if filename.endswith(".md"):
            file_path = os.path.join(knowledge_base_path, filename)
            content = None
            try:
                # 尝试 UTF-8
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
            except UnicodeDecodeError:
                try:
                    # 尝试 GBK（常用于 Windows 中文环境）
                    with open(file_path, "r", encoding="gbk") as file:
                        content = file.read()
                except Exception as e:
                    print(f"Error reading file {filename}: {str(e)}")
                    continue  # 如果两种都失败就跳过

            except Exception as e:
                print(f"Error reading file {filename}: {str(e)}")
                continue

            # 移除文件扩展名
            base_name = os.path.splitext(filename)[0]
            result[base_name] = content

    return result
'''
def read_all_md_files_from_knowledge_base():
    result = {}
    knowledge_base_path = KNOWLEDGE_BASE

    # Check if the KNOWLEDGE_BASE directory exists
    if not os.path.exists(knowledge_base_path):
        print(f"Error: The directory {knowledge_base_path} does not exist.")
        return result

    # Iterate through all files in the KNOWLEDGE_BASE directory
    for filename in os.listdir(knowledge_base_path):
        if filename.endswith(".md"):
            file_path = os.path.join(knowledge_base_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                    filename = os.path.basename(filename)[:-3]
                    result[filename] = content
            except Exception as e:
                print(f"Error reading file {filename}: {str(e)}")

    return result
'''
def inject_to_knowledge_base():
    # 连接到数据库
    conn = sqlite3.connect(f"{KNOWLEDGE_BASE}/knowledge_base.db")
    cursor = conn.cursor()

    # 创建表（如果不存在）
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        embedding BLOB NOT NULL
    )
    """
    )
    # 清空表
    cursor.execute(
        """
    DELETE FROM embeddings;
    """
    )

    os.environ['HF_ENDPOINT'] = "https://hf-mirror.com"

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    # 处理 Markdown 文件
    mds = read_all_md_files_from_knowledge_base()
    for filename, content in mds.items():  # 迭代 md 字典的 items() 方法获取键值对
        embeddings = model.encode(content)
        # 将 embeddings 转换为 bytes 以存储在 SQLite 中
        embedding_bytes = np.array(embeddings).tobytes()

        # 插入数据
        cursor.execute(
            "INSERT INTO embeddings (filename, embedding) VALUES (?, ?)",
            (filename, embedding_bytes),
        )
        print(f"Stored {filename} in the database.")

    # 提交更改并关闭连接
    conn.commit()
    conn.close()

    print("Embeddings have been successfully stored in the database.")
