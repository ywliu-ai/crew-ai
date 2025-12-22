from crewai import LLM

def main():
    from model import CustomLLM
    import os
    from dotenv import load_dotenv
    load_dotenv()
    # 从环境变量获取 API 密钥，如果不存在则使用默认值
    api_key = os.environ.get("OPENAI_API_KEY", "bd4e0cd0cd0b49e4ca7ad1767baadf3a09cbab24f7aa6a9a8486cd7e3b9d9eaf")
    model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
    endpoint = os.environ.get("OPENAI_ENDPOINT", "https://api.openai.com/v1/chat/completions")
    print(api_key)
    print(model_name)
    print(endpoint)
    llm = CustomLLM(api_key=api_key, model=model_name, endpoint=endpoint)    

    from crewai import Agent, Task, Crew

    email_assistant = Agent(
        role="Email Agent",
        goal="Improve emails and make them sound professional and clear",
        backstory="A highly experienced communication expert skilled in professional email writing",
        verbose=True,
        llm=llm,
    )

    original_email = """
    hey team, just wanted to tell u that demo is kind of ready, but there's still stuff left.
    Maybe we can show what we have and say rest is WIP.
    Let me know what u think. thanks
    """

    email_task = Task(
        description=f"""Take the following rough email and rewrite it into a professional and polished version.
        Expand abbreviations:
        '''{original_email}'''""",
        agent=email_assistant,
        expected_output="A professional written email with proper formatting and content",
    )

    crew = Crew(
        agents=[email_assistant],
        tasks=[email_task],
        verbose=True,
        )

    result = crew.kickoff()
    print(result)


if __name__ == "__main__":
    main()
