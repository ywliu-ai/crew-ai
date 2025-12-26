from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
from mysql.connector import pooling
import networkx as nx
from networkx.algorithms.community import k_clique_communities
import pymysql
from pymysql.cursors import DictCursor
import pandas as pd
from _pydatetime import timedelta, datetime
import re
import os


class LogRetrievalToolInput(BaseModel):
    """Input schema for MyCustomTool."""
    srcIp: str = Field(..., description="源IP")
    dstIp: str = Field(..., description="目标IP")

class LogRetrievalTool(BaseTool):
    name: str = "LogRetrievalTool"
    description: str = "基于输入告警的源IP和目的IP进行查询，然后把查询到告警的内容返回"
    args_schema: Type[BaseModel] = LogRetrievalToolInput

    def format_to_markdown(data_list):
        """将字典列表格式化为Markdown表格"""

        # 获取表头
        d1 = data_list[0]
        keys = d1.keys()
        headers = list(keys)

        # 构建表头行
        markdown = "| " + " | ".join(headers) + " |\n"

        # 构建分隔行
        markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"

        # 构建数据行
        for item in data_list:
            row = []
            for header in headers:
                value = item[header]
                # 处理datetime对象，转换为字符串
                # if isinstance(value, datetime.datetime):
                #     value = value.strftime("%Y-%m-%d %H:%M:%S")
                row.append(str(value))
            markdown += "| " + " | ".join(row) + " |\n"

        return markdown

    def _run(self, srcIp: str, dstIp: str) -> str:

        connection_pool = pooling.MySQLConnectionPool(
            host="159.226.16.192",
            port=3306,
            user="unified_monitoring",
            password="GYh5S2Xh#nEWeZwy",
            db="unified_monitoring",
            charset="utf8mb4",
            pool_name="unified_monitoring_pool",
            pool_size=5,    # 连接池大小
            ssl_disabled=True,
            time_zone="+08:00",  # 亚洲/上海时区
        )
        try:
            # 从池中获取连接
            connection = connection_pool.get_connection()

            conditions = []
            params = {}


            # 动态构建条件
            if srcIp :
                conditions.append("src_ip = %s")
                params['src_ip'] = srcIp

            if dstIp:
                conditions.append("dst_ip != %s") # SQL条件
                params['dst_ip'] = dstIp # 赋值

            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
            else:
                where_clause = ""

            exec_sql = f"SELECT start_time,src_ip,dst_ip,attack_class,invader_stage FROM znt_comprehensive_groupby_result {where_clause} ORDER BY start_time DESC LIMIT 5"
            if connection.is_connected():
                with connection.cursor() as cursor :
                    condition_values =   tuple(map(lambda x: x, params.values()))
                    cursor.execute(exec_sql,condition_values)
                    result = cursor.fetchall() 
                    format_list = []
                    for row in result:
                        entry = {}
                        entry["发生时间"] = row[0]
                        entry["源IP"] = row[1]
                        entry["目标IP"] = row[2]
                        entry["类型"] = row[3]
                        # 攻击阶段 去掉 前缀 “第几阶段”
                        attack_phase: str = row[4]
                        if attack_phase:
                            split_arr = attack_phase.split(" ",2)
                            if len(split_arr) == 2 :
                                entry["攻击阶段"] = split_arr[1]

                        format_list.append(entry)

                    if len(format_list) > 0:
                        md_list_str = self.format_to_markdown(format_list)

                        return   "## 二、全维度告警关联\n**告警日志关联**\n" + md_list_str

                    else:
                        return """## 二、全维度告警关联\n**告警日志关联**\n     无\n"""

        finally:
            # 将连接返回到池中
            if connection.is_connected():
                connection.close()



class Correlation_analysisToolInput(BaseModel):
    srcIp: str = Field(..., description="源IP")


class Correlation_analysisTool(BaseTool):

    name: str = "Correlation_analysisTool"
    description: str = "基于输入的源IP，对告警数据库进行派系聚类关联，查询该源IP是否还涉及其它告警，并输出带标题的 markdown 表格"
    args_schema: Type[BaseModel] = Correlation_analysisToolInput

    def _read_EDR_install_list(self) -> set[str]:
        """
        读取 EDR设备列表
        """
        set_tmp: set[str] = set()
        # 深信服的edr文件路径
        # 获取当前文件目录
        base_dir = os.path.dirname(os.path.abspath(__file__))

        # 拼接文件路径
        file_path_sangfor = os.path.join(base_dir, './EDR/深信服edr.xlsx')

        # 检查路径是否存在
        if not os.path.exists(file_path_sangfor) :
            #print(f"[edr]读取 深信服edr {file_path_sangfor} 不存在")
            pass
        else:
            df: DataFrame = pd.read_excel(
                file_path_sangfor,
            )
            for row in df.itertuples():
                # 访问列数据
                # print(row.Index, row.ColumnName)
                ip_list = row[7]

                if isinstance(ip_list, str) and ip_list not in "IP地址":
                    # 把IP切开后保持set中
                    for i in ip_list.split():
                        set_tmp.add(i)

        # 读取 深信服的CWPP文件路径
        file_path_CWPP = os.path.join(base_dir, './EDR/深信服CWPP.xls')

        if os.path.exists(file_path_sangfor):
            df1: DataFrame = pd.read_excel(file_path_CWPP, header=13)
            for row2 in df1.itertuples():
                ip_addr = row2[2]
                # print(f" {ip_addr} - {type(ip_addr)}")
                if ip_addr:
                    for y in ip_addr.split(","):
                        set_tmp.add(y)
            # print(f"[edr]读取 深信服CWPP ip 数量是 {len(set_tmp)}")
        else:
            # print(f"[edr]读取 深信服CWPP {file_path_CWPP} 不存在")
            pass

        # 读取 安全狗云眼
        file_path_anquangou =  os.path.join(base_dir, './EDR/安全狗云眼.xlsx')
        if os.path.exists(file_path_sangfor):
            df2: DataFrame = pd.read_excel(file_path_anquangou, header=0)
            for row3 in df2.itertuples():
                # 使用属性直接获取
                ip_row = row3.外网IP
                # index_1 = row3.Index
                # print(f" {index_1} - {ip_row}")
                if isinstance(ip_row, str):
                    set_tmp.add(ip_row)
            # print(f"[edr]读取 安全狗云眼 ip 数量是 {len(set_tmp)}")
        else:
            # print(f"[edr]读取 安全狗云眼 {file_path_anquangou} 不存在")
            pass

        return set_tmp
    

    def get_mysql_connection(self):
        """获取MySQL连接"""
        return pymysql.connect(
            host="159.226.16.192",
            port=3306,
            user="unified_monitoring",
            password="GYh5S2Xh#nEWeZwy",
            db="unified_monitoring",
            charset="utf8mb4",
            cursorclass=DictCursor
        )

    def step1(self, df: pd.DataFrame, k_common=2, k_clique=3) -> pd.DataFrame:
        """聚类分析第一步"""
        # 参数设置
        # arg:
        #   df: data
        #   k_common = 2   # 至少相同属性数量
        #   k_clique = 3   # 至少形成 3 个点的 clique 才能成为社区
        
        src_ip = "src_ip"
        dst_ip = "dst_ip"
        src_port = "src_country"
        dst_port = "dst_port"
        
        # 预提取字段，加速访问
        src_ips = df[src_ip].values
        dst_ips = df[dst_ip].values
        src_ports = df[src_port].values
        dst_ports = df[dst_port].values
        
        # 1. 构图
        G = nx.Graph()
        n = len(df)
        for i in range(n):
            G.add_node(i)
        
        # 2. 添加边（逐个判断是否有 > k_common 相似属性）
        for i in range(n):
            for j in range(i + 1, n):
                count = (
                    (src_ips[i] == src_ips[j]) +
                    (dst_ips[i] == dst_ips[j]) +
                    (src_ports[i] == src_ports[j]) +
                    (dst_ports[i] == dst_ports[j])
                )
                if count > k_common:
                    G.add_edge(i, j)
        
        # 3. CPM 聚类（传统方式，找 k 团）
        communities = list(k_clique_communities(G, k=k_clique))
        
        # 初始标签为 -1（表示未聚类）
        cluster_labels = [-1] * n
        
        for idx, community in enumerate(communities):
            for node in community:
                cluster_labels[node] = idx  # 注意可能重叠，后写会覆盖前写
        
        # 写回 DataFrame
        df['cluster'] = cluster_labels
        return df 
    
    def step2(self, df: pd.DataFrame, sim_threshold=0.2) -> pd.DataFrame:
        """聚类分析第二步"""
        src_ip = "src_ip"
        dst_ip = "dst_ip"

        # 遍历每个cluster的数据
        # 假设你的 DataFrame 叫 df，列名为 cluster_id
        df['tag'] = pd.Series(dtype='object') 
        
        cluster = pd.DataFrame({
            'A': pd.Series(dtype='object'),   # object 类型
            'T': pd.Series(dtype='object'),
            'tag': pd.Series(dtype='int64'),# 例如整数类型
        })
        
        As = []
        Ts = []
        tags = []
        cluster_ids = []  # 存储所有有效的cluster_id
        
        for cluster_id, group in df.groupby('cluster'):
            if cluster_id == -1:
                continue
            
            cluster_ids.append(cluster_id)  # 保存有效的cluster_id
            
            A = group[src_ip].nunique()
            T = group[dst_ip].nunique()
            V = A + T
          
            As.append(group[src_ip].unique().tolist())
            Ts.append(group[dst_ip].unique().tolist())
            
            OtO = 1/3*( (V-A)/(V-1) + (V-T)/(V-1) + (V-abs(A-T))/(V) )
            OtM = 1/3*( (V-A)/(V-1) + (T)/(V-1) + (abs(A-T))/(V) )
            try:
                MtO = 1/3*( (A)/(V-1) + (V-T)/(V-1) + (abs(A-T))/(V-2) )
            except:
                MtO = 0
            MtM = 1/3*( (A)/(V) + (T)/(V) + (V-abs(A-T))/(V) )
            
            tag = []
            tag.append(OtO)
            tag.append(OtM)
            tag.append(MtO)
            tag.append(MtM)
            
            index = tag.index(max(tag))
            
            tags.append(index)
            
            df.loc[group.index, 'tag'] = index
         
        # 如果没有有效的cluster，直接返回原DataFrame
        if not cluster_ids:
            df['group_id'] = -1
            return df
            
        cluster['A'] = As
        cluster['T'] = Ts
        cluster['tag'] = tags
        # 创建图
        G = nx.Graph()  # 创建一个空图（无向图）
        
        # 添加节点，使用实际的cluster_id
        G.add_nodes_from(cluster_ids)
        
        cluster_id_list = cluster_ids
            
        for i in range(len(cluster)):
            for j in range(i+1, len(cluster)):
                
                # 确保索引i和j在cluster的范围内
                if i >= len(cluster) or j >= len(cluster):
                    continue
                    
                # 获取实际的cluster_id
                actual_cluster_id_i = cluster_ids[i]
                actual_cluster_id_j = cluster_ids[j]
                
                list1 = cluster.loc[i,'A']
                list2 = cluster.loc[j,'A']
                
                # 交集
                intersection = list(set(list1) & set(list2))  # 或者用 set1.intersection(set2)
                
                # 并集
                union = list(set(list1) | set(list2))         # 或者用 set1.union(set2)
                
                if cluster.loc[i,'tag'] == cluster.loc[j,'tag']:
                    sim = len(intersection)/len(union)
                else:
                    sim = len(intersection)/len(list1)
                
                if sim >= sim_threshold:
                    G.add_edge(actual_cluster_id_i, actual_cluster_id_j, weight=sim)
                    
        # 找出所有连通分量（每个是一个簇集合）
        connected_components = list(nx.connected_components(G))  # G 是无向图
        
        # 建立 cluster_id 到 group_id 的映射字典
        cluster_to_group = {}
        for group_id, component in enumerate(connected_components):
            for cluster_id in component:
                cluster_to_group[cluster_id] = group_id
        df['group_id'] = df['cluster'].replace(cluster_to_group)  
        return df 

    def is_valid_ipv4(ip: str) -> bool:
        """验证IPv4地址格式"""
        pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        return re.match(pattern, ip) is not None

    def get_edr_list(self, ip: str = "", start_time: int = 0, end_time: int = 0):
        """获取edr日志的列表"""
        # 构建查询条件

        filter_conditions = []
        if self.is_valid_ipv4(ip):
            # 正常的IPV4
            filter_conditions.append({"term": {"iplist.keyword": {"value": ip}}})
        elif len(ip) > 0:
            # 有值并且 不是IPV4格式
            filter_conditions.append({"wildcard": {"iplist": "*" + ip + "*"}})
        else:
            filter_conditions.append({"term": {"iplist.keyword": {"value": ip}}})
        # 追加时间查询条件
        if start_time and end_time:
            filter_conditions.append({"range": {"@timestamp": {"gte": start_time, "lte": end_time}}})
        # 请求体
        search_body = {
            "size": 1,
            "query": {"bool": {"filter": filter_conditions}},
            "sort": [
                {"@timestamp": {"order": "desc"}},  # 主排序字段
                {"save_time": "asc"},  # 次排序字段确保唯一性
                {"_seq_no": "asc"},
            ],
        }

        # 执行ES查询
        response = self.es.search(index="sangfor_edr_*",body=search_body)
        total_value = response['hits']['total']['value']  # 命中总数
        if total_value > 0 :
            hits_arr = response["hits"]["hits"]
            list = []
            for i, item in enumerate(hits_arr,start=1):
                source =  item['_source']
                # 拼接告警详情
                details = source['details']
                alarm_details_str:str = ''
                for detail in details:
                    alarm_details_str += f"{detail['rule_name']} {detail['command']} {detail['rule_desc']}"

                list.append({"序号": i, "IP": source["iplist"], "告警详情": alarm_details_str, "告警条数": total_value})
            return list
        else :
            return []

    def has_been_installed(self,ip:str) -> bool:
        """这个IP是否安装过edr软件"""
        EDRInstallSet = self._read_EDR_install_list()
        return ip in EDRInstallSet

    def query_edr_log(self, ip_arr:str,time_str:str = "-") -> str:

        """
            Query EDR logs based on an IPv4 address.
            Returns a dictionary with the judgment results for the IP:
            1) IPs with unsuccessful attack investigation and no anomalies in EDR data,
            2) IPs with successful attack investigation and anomalies in EDR data,
            3) IPs where the EDR agent is not deployed.

            Args:
                ip_arr:IPv4 address or list to query. Required，Multiple separated by commas
                time_str: Time range to query. Optional

            Returns:
                dict: Judgment results as described above.
        """

        # 参数处理逻辑
        query_list = []

        if isinstance(ip_arr,str):
            if "," in ip_arr:
                query_list = ip_arr.split(",")
            else:
                query_list = [ip_arr]
        global start_time,end_time

        result_text = ""

        # 时间处理逻辑（# 11.27新需求，增加时间字段，按照时间+ip到es上查询告警数据条数（默认近7天，如果有值则按照前后加减3天范围查询））
        if time_str and len(time_str) == 19:
            # 根据time_str格式yyyy-MM-dd hh:mm:ss获取三天前和三天后的时间戳类型
            try:
                dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                start_time = dt - timedelta(days=3)
                start_time = int(start_time.timestamp() * 1000)
                end_time = dt + timedelta(days=3)
                end_time = int(end_time.timestamp() * 1000)
            except ValueError:
                print(f"{ValueError}")
                return "时间格式错误，请使用yyyy-MM-dd hh:mm:ss格式"

        else :
            # 否则获取当前时间的往前6天时间 结束时间就是当前时间
            dt = datetime.now()
            start_time = dt - timedelta(days=6)
            start_time = int(start_time.timestamp() * 1000)
            end_time = int(dt.timestamp() * 1000)



        for item_ip in query_list:
            # 是否安装了ip
            b:bool = self.has_been_installed(item_ip)
            if b :
                result_text += f"  {item_ip}，已安装EDR agent"
                # 安装了edr再进行查询日志
                list = self.get_edr_list(item_ip, start_time, end_time)
                if list and len(list) > 0:
                    detail_0 = list[0]
                    result_text += f",告警详情:{detail_0.get("告警详情")}.\n"

                else :
                    result_text += "。\n"
            else:
                result_text += f"  {item_ip},未安装EDR"

        return result_text

    def _run(self, srcIp:str) -> str:
        conn = None
        cursor = None
        try:
            # 获取数据库连接
            conn = self.get_mysql_connection()
            cursor = conn.cursor()

            # 查询数据
            sql = "SELECT * FROM znt_comprehensive_groupby_result"
            cursor.execute(sql)
            results = cursor.fetchall()
            df = pd.DataFrame(results)

            # 注释：需要聚合时取消注释
            df = self.step1(df)
            df = self.step2(df)

            # filtered_df = df[(df['src_ip'] == ip) | (df['dst_ip'] == ip)]
            filtered_df = df[(df['src_ip'] == srcIp)]

            days = (filtered_df["start_time"].iloc[-1] - filtered_df["start_time"].iloc[0]).days
            # 总条数
            total_count = len(filtered_df)
            # 不同目的 IP 的数量
            if len(filtered_df) > 0:
                unique_dest_ip = list(set(filtered_df['dst_ip'].tolist()))
                unique_dest_count = len(set(filtered_df['dst_ip'].tolist()))
                # 攻击类型列表（去重）
                attack_types = list(set(filtered_df['attack_class'].tolist()))
            else:
                unique_dest_ip = []
                unique_dest_count = 0
                attack_types = []

            # 检查是否存在judgement_progress_result列
            if 'judgement_progress_result' in filtered_df.columns and len(filtered_df) > 0:
                # 确保judgement_progress_result列是字符串类型，处理空值和非字符串值
                filtered_df = filtered_df.copy()  # 创建副本以避免修改原数据
                filtered_df['judgement_progress_result'] = filtered_df['judgement_progress_result'].astype(str)
                # 使用正确的pandas字符串匹配语法，使用pd.Series来确保类型
                judgement_series = pd.Series(filtered_df['judgement_progress_result'])
                success_mask = judgement_series.str.contains('成功', na=False)
                fail_mask = judgement_series.str.contains('失败', na=False)
                
                attack_success_df = filtered_df[success_mask]
                attack_success_dst_ip = list(set(attack_success_df['dst_ip'].tolist()))
                attack_success_ori_ip = list(set(attack_success_df['src_ip'].tolist()))
                attack_fail_df = filtered_df[fail_mask]
                attack_fail_dst_ip = list(set(attack_fail_df['dst_ip'].tolist()))
            else:
                # 如果列不存在或数据为空，设置默认值
                attack_success_dst_ip = []
                attack_success_ori_ip = []
                attack_fail_dst_ip = []

            edr_result = "无\n"
            dst_ip_list = filtered_df.get("dst_ip")
            if unique_dest_ip is not None and len(dst_ip_list) > 0:
                # dst_ip去重,再查询
                ip_addr = ",".join(set(dst_ip_list.tolist()) )
                edr_result = self.query_edr_log(ip_addr)

            ans = "## 三、告警攻击行为聚类分析\n"
            ans += f"### 1、聚类结果\n"
            if total_count != 0:
                ans += f"该安全告警与过去{days}天内的{total_count} 条告警行为特征高度相似，疑似来源于同一攻击者或攻击组织。"
            if unique_dest_count != 0:
                ans += f"攻击目标涉及{unique_dest_count}台资产，"
            if attack_types:
                ans += f"攻击类型包括 {attack_types}。" + "\n" + "### 2、告警详情\n"
            if attack_success_dst_ip:
                ans += f"已确认被攻击成功资产: {attack_success_dst_ip}, 攻击者可能会通过这些ip, 对内网其他主机进行横向渗透。" + "\n"
            if attack_fail_dst_ip:
                ans += f"潜在风险资产{attack_fail_dst_ip}: 暂未检测出现明显异常,但已被攻击探测,需要进一步核查Web日志、系统事件日志和应用层访问记录,以排除潜在安全隐患。" + "\n"
            if unique_dest_ip:
                ans += f"需要对{unique_dest_ip}开展持续观测与流量监控,"
            if attack_success_ori_ip:
                ans += f"建议在防火墙及安全策略中封禁攻击源IP:{attack_success_ori_ip}。" + "\n\n"
            ans += f"\n## 四、edr安全软件安装情况\n{edr_result}\n {srcIp}为高危恶意攻击源，对多项资产持续攻击，具备横向扩散特征，建议立即阻断，是否执行阻断操作？"
            return ans

        except Exception as e:
            return f"数据库错误：{e}"
        finally:
            # 确保资源关闭
            try:
                if cursor:
                    cursor.close()
            except:
                pass
            try:
                if conn and conn.open:
                    conn.close()
            except:
                pass



# def main():
#     srcIp = "202.122.32.254"
#     tool = Correlation_analysisTool()
#     resutl = tool.run(srcIp)
#     print(resutl)
# if __name__ == "__main__":
#     main()
