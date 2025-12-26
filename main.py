from model import CustomLLM
import os
from dotenv import load_dotenv
from CustomCrew import collabrative_agent, email_agent, intent_analysis, log_summary, Correlation_analysis
import json


load_dotenv()
# 从环境变量获取 API 密钥，如果不存在则使用默认值
api_key = os.environ.get("OPENAI_API_KEY", "bd4e0cd0cd0b49e4ca7ad1767baadf3a09cbab24f7aa6a9a8486cd7e3b9d9eaf")
model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
endpoint = os.environ.get("OPENAI_ENDPOINT", "https://api.openai.com/v1/chat/completions")
llm = CustomLLM(api_key=api_key, model=model_name, endpoint=endpoint)  




def main():
    with open("D:\PythonIDE\jupyter\crewAI\dataset\query.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print(data)
    # srcIp = "202.122.32.254"
    # dstIp = "123.56.102.90"
    # crew = Correlation_analysis(llm, srcIp)


    # result = crew.kickoff()
    # print(result)

    # from crewai.flow.flow import Flow, listen, start
    # from pydantic import BaseModel

    # class ExampleState(BaseModel):
    #     counter: int = 0
    #     message: str = ""

    # class StateExampleFlow(Flow[ExampleState]):

    #     @start()
    #     def first_method(self):
    #         self.state.message = "Hello from first_method"
    #         self.state.counter += 1

    #     @listen(first_method)
    #     def second_method(self):
    #         self.state.message += " - updated by second_method"
    #         self.state.counter += 1
    #         return self.state.message

    # flow = StateExampleFlow()
    # flow.plot("my_flow_plot.html")
    # final_output = flow.kickoff()
    # print(f"Final Output: {final_output}")
    # print("Final State:")
    # print(flow.state)


if __name__ == "__main__":
    main()
