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


# Define flow state
class AlertReportState(BaseModel):
    data: Dict = Field(default_factory=dict)
    analysis: str | None = None
    _llm: CustomLLM | None = PrivateAttr(default=None)
    
    def set_llm(self, llm: CustomLLM):
        self._llm = llm
    
    def get_llm(self):
        return self._llm


# Create a flow class
class AlertReportFlow(Flow[AlertReportState]):
    def __init__(self, initial_data: Dict = None, **kwargs):
        super().__init__(**kwargs)
        # 在 super().__init__() 之后，state 应该已经创建，直接设置 data
        if initial_data is not None:
            self.state.data = initial_data.copy()  # 使用 copy() 避免引用问题
    
    @start()
    def initialize_flow(self) -> Dict[str, Any]:
        # 在 Flow 启动时注入自定义 LLM，确保后续所有 Agent 使用的是 CustomLLM 而不是默认 OpenAI LLM
        self.state.set_llm(llm)
        # 打印调试信息，确认 data 是否正确初始化
        print(f"State data initialized: {self.state.data}")
        print(f"Starting market research for {self.state.data.get('srcip','')}")
        # 不要返回会覆盖 data 的值，只返回其他需要更新的字段
        return {}

    @listen(initialize_flow)
    def IntentAnalysis(self) -> Dict[str, Any]:
        llm = self.state.get_llm()
        # 假设 intent_analysis 返回一个 Crew 对象
        AnalysisCrew = intent_analysis(llm, self.state.data.get("log",""))

        # 直接异步安全调用 kickoff_async
        result = AnalysisCrew.kickoff()
        print(f"Debug: IntentAnalysis result type = {type(result)}, length = {len(str(result)) if result else 0}")
        
        # 确保 result 是字符串类型
        analysis_value = str(result) if result else ""
        # 同时直接更新 state 和返回字典，确保状态更新
        self.state.analysis = analysis_value
        return {"analysis": analysis_value}

    @listen(IntentAnalysis)
    def LogSummary(self) -> Dict[str, Any]:
        llm = self.state.get_llm()
        # 调试：检查 IntentAnalysis 是否已经更新了 state.analysis
        print(f"Debug: state.analysis before LogSummary: {self.state.analysis}")
        LogSummaryCrew = log_summary(llm, self.state.data.get("srcip",""), self.state.data.get("dstip",""))
        result = LogSummaryCrew.kickoff()

        # 确保从 state 中读取最新的 analysis 值
        previous_analysis = self.state.analysis or ""
        print(f"Debug: previous_analysis = {previous_analysis}")
        # 确保 result 是字符串类型
        result_str = str(result) if result else ""
        combined_analysis = f"{previous_analysis}\n\n{result_str}" if previous_analysis else result_str
        print(f"Debug: combined_analysis length = {len(combined_analysis) if combined_analysis else 0}")
        
        # 同时直接更新 state 和返回字典，确保状态更新
        self.state.analysis = combined_analysis
        return {"analysis": combined_analysis}
   


def kickoff():
    with open("D:\\PythonIDE\\jupyter\\crewAI\\dataset\\query.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Loaded data from JSON: {data}")
    # 通过构造函数传递初始数据
    alert_report_flow = AlertReportFlow(initial_data=data)
    # 在创建 flow 后立即检查 state 是否正确初始化
    print(f"Flow state after initialization: {alert_report_flow.state.data}")
    alert_report_flow.plot("AlertReportFlowPlot.html")
    
    # kickoff() 返回最后一个方法的返回值，但状态也会更新
    final_output = alert_report_flow.kickoff()
    print(f"Debug: kickoff() returned: {type(final_output)}")
    if isinstance(final_output, dict):
        print(f"Debug: final_output keys: {final_output.keys()}")
        if "analysis" in final_output:
            print(f"Debug: final_output['analysis'] length: {len(str(final_output['analysis']))}")
    
    # 检查 state 是否已更新
    print(f"Flow state analysis: {alert_report_flow.state.analysis}")
    print(f"Flow state analysis type: {type(alert_report_flow.state.analysis)}")
    print(f"Flow state analysis length: {len(str(alert_report_flow.state.analysis)) if alert_report_flow.state.analysis else 0}")

# Run the flow
if __name__ == "__main__":
    kickoff()
