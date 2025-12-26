import asyncio
from typing import Any, Dict, List
from pydantic import BaseModel, Field, PrivateAttr
from crewai.flow.flow import Flow, listen, start

from CustomCrew import collabrative_agent, email_agent, intent_analysis, log_summary, Correlation_analysis
import json
import os
from model import CustomLLM
from dotenv import load_dotenv

load_dotenv()
# 从环境变量获取 API 密钥，如果不存在则使用默认值
api_key = os.environ.get("OPENAI_API_KEY", "bd4e0cd0cd0b49e4ca7ad1767baadf3a09cbab24f7aa6a9a8486cd7e3b9d9eaf")
model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
endpoint = os.environ.get("OPENAI_ENDPOINT", "https://api.openai.com/v1/chat/completions")
llm = CustomLLM(api_key=api_key, model=model_name, endpoint=endpoint, timeout=120, max_retries=3)



# Define a structured output format
class MarketAnalysis(BaseModel):
    key_trends: List[str] = Field(description="List of identified market trends")
    market_size: str = Field(description="Estimated market size")
    competitors: List[str] = Field(description="Major competitors in the space")


# Define flow state
class AlertReportState(BaseModel):
    data: Dict = {}
    analysis: MarketAnalysis | None = None
    _llm: CustomLLM | None = PrivateAttr(default=None)
    
    def set_llm(self, llm: CustomLLM):
        self._llm = llm
    
    def get_llm(self):
        return self._llm


# Create a flow class
class AlertReportFlow(Flow[AlertReportState]):
    @start()
    def initialize_flow(self) -> Dict[str, Any]:
        # 在 Flow 启动时注入自定义 LLM，确保后续所有 Agent 使用的是 CustomLLM 而不是默认 OpenAI LLM
        self.state.set_llm(llm)
        print(f"Starting market research for {self.state.data.get('srcip','')}")
        return {"data": self.state.data.get("srcip","")}

    @listen(initialize_flow)
    def IntentAnalysis(self) -> Dict[str, Any]:
        llm = self.state.get_llm()
        # 假设 intent_analysis 返回一个 Crew 对象
        AnalysisCrew = intent_analysis(llm, self.state.data.get("log",""))

        # 直接异步安全调用 kickoff_async
        result = AnalysisCrew.kickoff()


        return {"analysis": result}
    # @listen(analyze_market)
    # def present_results(self, analysis) -> None:
    #     print("\nMarket Analysis Results")
    #     print("=====================")

    #     if isinstance(analysis, dict):
    #         # If we got a dict with 'analysis' key, extract the actual analysis object
    #         market_analysis = analysis.get("analysis")
    #     else:
    #         market_analysis = analysis

    #     if market_analysis and isinstance(market_analysis, MarketAnalysis):
    #         print("\nKey Market Trends:")
    #         for trend in market_analysis.key_trends:
    #             print(f"- {trend}")

    #         print(f"\nMarket Size: {market_analysis.market_size}")

    #         print("\nMajor Competitors:")
    #         for competitor in market_analysis.competitors:
    #             print(f"- {competitor}")
    #     else:
    #         print("No structured analysis data available.")
    #         print("Raw analysis:", analysis)


# Usage example


def kickoff():
    with open("D:\\PythonIDE\\jupyter\\crewAI\\dataset\\query.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    alert_report_flow = AlertReportFlow(inputs={"data": data})
    alert_report_flow.plot("AlertReportFlowPlot.html")
    alert_report_flow.kickoff()

# Run the flow
if __name__ == "__main__":
    kickoff()
