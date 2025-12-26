from crewai import Agent, Crew, Task, Process
from tools import LogRetrievalTool, Correlation_analysisTool



def collabrative_agent(llm):
    researcher = Agent(
    role="Research Specialist",
    goal="Find accurate, up-to-date information on any topic",
    backstory="""You're a meticulous researcher with expertise in finding 
    reliable sources and fact-checking information across various domains.""",
    allow_delegation=True,
    verbose=True,
    llm=llm
    )

    writer = Agent(
        role="Content Writer",
        goal="Create engaging, well-structured content",
        backstory="""You're a skilled content writer who excels at transforming 
        research into compelling, readable content for different audiences.""",
        allow_delegation=True,
        verbose=True,
        llm=llm
    )

    editor = Agent(
        role="Content Editor",
        goal="Ensure content quality and consistency",
        backstory="""You're an experienced editor with an eye for detail, 
        ensuring content meets high standards for clarity and accuracy.""",
        allow_delegation=True,
        verbose=True,
        llm=llm
    )

    # Create a task that encourages collaboration
    article_task = Task(
        description="""Write a comprehensive 1000-word article about 'The Future of AI in Healthcare'.
        
        The article should include:
        - Current AI applications in healthcare
        - Emerging trends and technologies  
        - Potential challenges and ethical considerations
        - Expert predictions for the next 5 years
        
        Collaborate with your teammates to ensure accuracy and quality.""",
        expected_output="A well-researched, engaging 1000-word article with proper structure and citations",
        agent=writer  # Writer leads, but can delegate research to researcher
    )

    # Create collaborative crew
    crew = Crew(
        agents=[researcher, writer, editor],
        tasks=[article_task],
        process=Process.sequential,
        verbose=True
    )

    return crew


def email_agent(llm):

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

    return crew


def intent_analysis(llm, log_data: str):
    analysis = Agent(
        role="Web Traffic Attack Intent Analysis Agent",
        goal=(
            "根据提供的流量日志数据，识别并分析攻击者的攻击意图，并按照系统要求格式输出。"
            "重点基于 URL、请求头、请求体、源IP、目标IP进行判断，并输出可读结构化结果。"
        ),
        backstory=(
            "你是一名网络安全分析专家，长期处理攻防演练与APT检测，熟悉Web攻击手法与MITRE ATT&CK框架。"
            "你能根据请求流量行为、特征参数、敏感字段判断攻击企图，并提供证据链式说明。"
            "对于缺失字段，你不会猜测或输出不存在的信息。"
        ),
        verbose=True,
        llm=llm
    )
    analysis_task = Task(
        description=(
            "基于提供的 Web 流量日志数据，全面分析攻击者的攻击意图。\n"
            "日志重点字段包括：请求URL(requrl)、请求头(reqheaders)、请求体(reqbodys)、源IP(src_ip)、目标IP(dst_ip)。\n"
            "日志数据：\n"
            f"{log_data}\n"
            "分析要求：\n"
            "1️⃣ 展示判断攻击意图的依据（必须结合真实字段，不允许凭空推断）\n"
            "2️⃣ 按 MITRE ATT&CK 框架进行简要攻击意图分类\n"
            "⚠️ 日志中如缺失部分字段，不分析、不输出、不猜测"
        ),
        expected_output=(
            "必须严格输出以下结构：\n\n"
            "## 一、流量日志漏攻击意图分析\n"
            "### 1.攻击意图\n"
            "| 风险等级 | 攻击意图 | 具体依据 |\n"
            "|----------|----------|----------|\n"
            "(根据日志实际内容动态生成多行)\n\n"
            "### 2.ATT&CK\n"
            "基于已有日志内容简要说明对应的 ATT&CK 技术或战术类别"
        ),
        agent=analysis,  # 调用你刚定义的 Intent Analysis Agent
        allow_delegation=False
    )
    crew = Crew(
        agents=[analysis],
        tasks=[analysis_task],
        process=Process.sequential,
        verbose=True
    )
    return crew


def log_summary(llm, srcIp: str, dstIp: str):
    alarm_link_agent = Agent(
        role="告警日志检索后总结 Agent",
        goal=(
            "根据输入的 src_ip，对告警数据库进行检索，查询该源IP是否还涉及其它告警，"
            "并输出带标题的 markdown 表格作为报告内容。如果无数据则返回 None。"
        ),
        backstory=(
            "你是一名安全运营分析专家，擅长关联分析告警数据，并根据源IP追踪潜在攻击活动。"
            "你会调用告警查询工具（如 MySQL 查询工具）来获取数据，并将结果转化为结构化输出。"
        ),
        instructions=(
            "✔ 必须基于工具返回的真实数据生成内容\n"
            "✔ 输出格式必须为：带标题的 markdown 表格\n"
            "✔ 如果没有关联告警必须返回 'None'（不要补充多余内容）\n"
            "✔ 查询条件：src_ip 匹配输入源IP；过滤掉 dst_ip == src_ip 的数据\n"
            "⚠️ 不允许猜测结果，不允许虚构告警内容"
        ),
        allow_delegation=False,
        verbose=True,
        llm=llm,
        tools=[LogRetrievalTool()]
    )
    alarm_task = Task(
        description=f"根据输入源IP {srcIp}和目标IP {dstIp}，总结告警日志，并输出带标题的 markdown 表格",
        expected_output="### 告警结果\n|...markdown table...| 或 None",
        agent=alarm_link_agent
    )

    crew = Crew(
        agents=[alarm_link_agent],
        tasks=[alarm_task],
        process=Process.sequential,
        verbose=True
    )
    return crew


def Correlation_analysis(llm, srcIp: str):
    correlation_agent = Agent(
        role="告警派系聚类关联分析智能体，调用<Correlation_analysisTool>工具得到派系聚类关联结果，并根据结果进行告警分析",
        goal=(
            "基于派系聚类关联的结果，进行分析，识别潜在的攻击派系/攻击活动归属，"
            "根据字段src_ip和dst_ip分析攻击是否属于同一攻击者、同一攻击链、"
            "并输出分析结果。"
        ),
        backstory=(
            "你是一名精准攻防对抗专家，擅长从大规模告警数据中识别攻击组织模式、推测攻击者行为链，"
            "能根据派系聚类关联的结果给出证据链说明。"
        ),

        allow_delegation=False,
        verbose=True,
        llm=llm,
        tools=[Correlation_analysisTool()]
    )
    correlation_task = Task(
        description=(
            "对以下源ip或者目的ip执行派系聚类关联分析并给出 markdown 表格结果：\n"
            f"{srcIp}"
        ),
        expected_output=(
            "🧠## 三、告警攻击行为聚类分析\n"
            "### 1、聚类结果\n"
            "... ...\n"
            "## 四、edr安全软件安装情况\n"
            "... ..."
        ),
        agent=correlation_agent
    )

    crew = Crew(
        agents=[correlation_agent],
        tasks=[correlation_task],
        process=Process.sequential,
        verbose=True
    )

    return crew

