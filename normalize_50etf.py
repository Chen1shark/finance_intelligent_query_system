import sys
import ollama
import config

def normalize_50etf_text(user_input):
    """
    调用本地 Ollama 模型规范化用户输入。
    仅保留 50ETF 相关核心信息，剔除无关内容。
    
    参数:
        user_input (str): 用户输入的原始文本
        
    返回:
        str: 规范化后的文本 或 "无有效50ETF相关信息"
    """
    
    # 检查输入是否为空
    if not user_input or not user_input.strip():
        return None

    # 定义系统提示词，严格约束模型行为
    system_prompt = """
    你是一个金融文本处理助手，专门负责提取“上证50ETF”相关的核心信息。
    
    请严格遵守以下规则处理用户输入：
    1. **保留内容**：仅保留与50ETF（上证50交易型开放式指数基金）及其期权相关的信息，包括价格、走势、买卖操作、持仓、费率、成分股、套利、申赎、时间/数值等。
    2. **剔除内容**：
       - 剔除所有闲聊（如“你好”、“在吗”）。
       - 剔除无关金融产品（如“股票”、“期货”、“沪深300ETF”等）。
       - 剔除情绪化表达（如“气死了”、“求大神”）。
       - 剔除无意义语气词（如“啊啊啊”、“嗯嗯”）。
    3. **输出格式**：
       - 直接输出规范化后的核心文本，不要包含任何解释、前缀或寒暄。
       - 如果输入中不包含任何50ETF相关有效信息，请直接返回“无有效50ETF相关信息”。
       
    示例：
    输入：“你好，请问50ETF期权现在的价格是多少啊？我都急死了”
    输出：“50ETF期权现在的价格是多少”
    
    输入：“沪深300最近怎么样？”
    输出：“无有效50ETF相关信息”
    
    输入：“明天50ETF会涨吗”
    输出：“明天50ETF会涨吗”
    """

    try:
        # 调用 Ollama 接口
        response = ollama.chat(
            model=config.OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_input},
            ],
            options={
                'temperature': 0.1,  # 低温度保证结果稳定
            },
            stream=False  # 关闭流式输出，一次性返回
        )
        
        # 获取并返回结果
        if 'message' in response and 'content' in response['message']:
             return response['message']['content'].strip()
        return "模型未返回有效内容"

    except ollama.ResponseError as e:
        print(f"\n错误: 模型调用失败 - {e.error}")
        return None
    except Exception as e:
        # 捕获连接错误（如服务未启动）或其他异常
        print(f"\n错误: 发生异常 - {str(e)}")
        return None

def main():
    """主程序循环"""
    print("="*50)
    print(f"50ETF 文本规范化工具 (基于本地 Ollama {config.OLLAMA_MODEL})")
    print("输入 'quit' 或 'exit' 退出程序")
    print("="*50)
    
    while True:
        try:
            # 获取用户输入
            user_text = input("\n请输入文本: ").strip()
            
            # 退出条件
            if user_text.lower() in ['quit', 'exit']:
                print("程序已退出。")
                break
            
            if not user_text:
                continue
                
            print("正在处理...", end="\r")
            
            # 调用处理函数
            result = normalize_50etf_text(user_text)
            
            # 输出结果
            if result:
                print(f"规范化结果: {result}")
                
        except KeyboardInterrupt:
            print("\n程序已强制退出。")
            break
        except Exception as e:
            print(f"\n运行时错误: {e}")

if __name__ == "__main__":
    main()
