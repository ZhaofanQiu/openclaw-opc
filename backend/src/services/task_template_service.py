"""
任务模板服务
生成标准化的任务分配消息
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta


# ============ 任务模板定义 ============

BASE_TASK_TEMPLATE = """📋 **任务分配** | 任务ID: {task_id} | 优先级: {priority}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 任务要求
{task_description}

## 📊 输入数据
{input_data}

## 🔧 可用工具/资源
{tools_and_resources}

## 📤 输出要求
- **输出格式**: {output_format}
- **输出位置**: {output_location}
- **命名规范**: {naming_convention}

## ⏰ 限制条件
- **预计耗时**: {estimated_hours}小时
- **预算**: {budget} OC币
- **截止时间**: {deadline}

## ✅ 完成标准
{completion_criteria}

## 🔗 反馈方式
完成后请严格按以下格式回复：
```
STATUS: completed/failed
RESULT: [结果摘要或失败原因]
OUTPUT_PATH: [输出文件路径或数据库记录ID]
TOKEN_USED: [实际消耗token数]
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

DATABASE_QUERY_TEMPLATE = """📋 **数据库查询任务** | 任务ID: {task_id} | 优先级: {priority}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 任务目标
{task_description}

## 🔗 数据库连接信息
- **类型**: {db_type}
- **路径**: {db_path}
- **相关表**: {tables}

## 📊 可用查询函数
你可以使用以下函数执行查询：
```python
# 执行SQL查询
result = opc_query("SELECT * FROM {table} WHERE ...")

# 获取表结构
schema = opc_get_table_schema("{table}")
```

## 📝 具体查询要求
{query_requirements}

## 📤 输出要求
- **保存位置**: {output_path}
- **格式**: {output_format} (JSON/CSV/Markdown)
- **内容**: {output_content}

## ⏰ 限制条件
- **预算**: {budget} OC币
- **截止时间**: {deadline}

## ✅ 完成标准
- [ ] 查询逻辑正确
- [ ] 结果数据完整
- [ ] 输出格式符合要求
- [ ] 文件已保存到指定位置

## 🔗 反馈格式
```
STATUS: completed/failed
RESULT: [查询结果摘要，如"查询到15条记录，已生成report.json"或失败原因]
OUTPUT_PATH: [如 workspace/tasks/{task_id}/result.json]
TOKEN_USED: [数字]
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

FILE_PROCESSING_TEMPLATE = """📋 **文件处理任务** | 任务ID: {task_id} | 优先级: {priority}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📁 输入文件信息
- **路径**: {input_path}
- **格式**: {input_format}
- **描述**: {file_description}

## 🛠️ 处理要求
{processing_requirements}

## 📝 处理步骤
{processing_steps}

## 📤 输出要求
- **保存路径**: {output_path}
- **格式**: {output_format}
- **命名**: {naming_convention}
- **内容要求**: {content_requirements}

## ⏰ 限制条件
- **预算**: {budget} OC币
- **截止时间**: {deadline}

## ✅ 完成标准
{completion_criteria}

## 🔗 反馈格式
```
STATUS: completed/failed
RESULT: [处理结果摘要]
OUTPUT_PATH: [输出文件路径]
TOKEN_USED: [数字]
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

RESEARCH_TEMPLATE = """📋 **研究任务** | 任务ID: {task_id} | 优先级: {priority}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🔍 研究主题
{research_topic}

## 🎯 研究目标
{research_objectives}

## 🛠️ 可用工具
- **搜索**: web_search(query) - 搜索网络信息
- **获取网页**: web_fetch(url) - 获取网页内容
- **读取文件**: read_file(path) - 读取本地文件

## 📝 报告要求
- **结构**: {report_structure}
- **字数**: {word_count}
- **引用**: 需要标注数据来源
- **格式**: Markdown

## 📤 输出要求
- **保存位置**: {output_path}/research_{task_id}.md
- **必须包含**:
  - 执行摘要
  - 详细发现
  - 数据来源列表
  - 建议/结论

## ⏰ 限制条件
- **预算**: {budget} OC币
- **截止时间**: {deadline}

## ✅ 完成标准
- [ ] 信息来源可靠
- [ ] 分析逻辑清晰
- [ ] 报告格式规范
- [ ] 文件已保存

## 🔗 反馈格式
```
STATUS: completed/failed
RESULT: [研究报告摘要，如"完成关于XX的研究，共引用5个来源"]
OUTPUT_PATH: [报告文件路径]
TOKEN_USED: [数字]
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

CONTENT_GENERATION_TEMPLATE = """📋 **内容生成任务** | 任务ID: {task_id} | 优先级: {priority}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 生成目标
{generation_goal}

## 📝 内容要求
- **类型**: {content_type}
- **主题**: {topic}
- **风格**: {style}
- **长度**: {length}

## 📊 参考材料
{reference_materials}

## 📤 输出要求
- **格式**: {output_format}
- **保存位置**: {output_path}
- **命名**: {naming_convention}

## ⏰ 限制条件
- **预算**: {budget} OC币
- **截止时间**: {deadline}

## ✅ 质量标准
- [ ] 内容原创
- [ ] 符合主题要求
- [ ] 格式规范
- [ ] 无错别字

## 🔗 反馈格式
```
STATUS: completed/failed
RESULT: [内容生成摘要，如"已生成2000字技术文章"]
OUTPUT_PATH: [文件路径]
TOKEN_USED: [数字]
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

DATA_ANALYSIS_TEMPLATE = """📋 **数据分析任务** | 任务ID: {task_id} | 优先级: {priority}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 分析目标
{analysis_goal}

## 📊 数据源
- **位置**: {data_source}
- **格式**: {data_format}
- **描述**: {data_description}

## 🛠️ 分析要求
{analysis_requirements}

## 📈 输出要求
- **分析报告**: {output_path}/analysis_{task_id}.md
- **可视化**: {output_path}/charts/ (如需要)
- **数据结果**: {output_path}/data/ (处理后的数据)

## 📋 报告结构
1. 数据概况
2. 分析方法
3. 主要发现
4. 可视化图表
5. 结论与建议

## ⏰ 限制条件
- **预算**: {budget} OC币
- **截止时间**: {deadline}

## ✅ 完成标准
- [ ] 数据处理正确
- [ ] 分析方法合理
- [ ] 结论有据可依
- [ ] 可视化清晰

## 🔗 反馈格式
```
STATUS: completed/failed
RESULT: [分析结果摘要，如"完成数据分析，发现3个关键趋势"]
OUTPUT_PATH: [分析报告路径]
TOKEN_USED: [数字]
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# ============ 任务模板服务 ============

class TaskTemplateService:
    """任务模板生成服务"""
    
    TEMPLATES = {
        "base": BASE_TASK_TEMPLATE,
        "database_query": DATABASE_QUERY_TEMPLATE,
        "file_processing": FILE_PROCESSING_TEMPLATE,
        "research": RESEARCH_TEMPLATE,
        "content_generation": CONTENT_GENERATION_TEMPLATE,
        "data_analysis": DATA_ANALYSIS_TEMPLATE,
    }
    
    # 默认工具/资源描述
    DEFAULT_TOOLS = """- 文件操作: read_file, write_file, list_directory
- 代码执行: python代码执行环境
- 网络搜索: web_search(query)
- 网页获取: web_fetch(url)
- 数据查询: opc_query(sql)"""
    
    def __init__(self, workspace_base: str = "/root/.openclaw/workspace"):
        self.workspace_base = workspace_base
    
    def generate_task_message(
        self,
        task_type: str,
        task_id: str,
        description: str,
        priority: str = "normal",
        budget: float = 100.0,
        deadline_hours: int = 24,
        **kwargs
    ) -> str:
        """
        生成标准化的任务消息
        
        Args:
            task_type: 任务类型 (base/database_query/file_processing/research/content_generation/data_analysis)
            task_id: 任务ID
            description: 任务描述
            priority: 优先级 (low/normal/high/urgent)
            budget: 预算(OC币)
            deadline_hours: 截止小时数
            **kwargs: 额外参数根据任务类型不同
        
        Returns:
            格式化后的任务消息
        """
        template = self.TEMPLATES.get(task_type, BASE_TASK_TEMPLATE)
        
        # 计算截止时间
        deadline = (datetime.now() + timedelta(hours=deadline_hours)).strftime("%Y-%m-%d %H:%M")
        
        # 生成输出路径
        task_workspace = f"{self.workspace_base}/tasks/{task_id}"
        
        # 基础上下文
        context = {
            "task_id": task_id,
            "task_description": description,
            "priority": priority,
            "budget": budget,
            "deadline": deadline,
            "output_path": task_workspace,
            "tools_and_resources": kwargs.get("tools_and_resources", self.DEFAULT_TOOLS),
        }
        
        # 根据任务类型添加特定上下文
        if task_type == "database_query":
            context.update({
                "db_type": kwargs.get("db_type", "SQLite"),
                "db_path": kwargs.get("db_path", "./data/opc.db"),
                "tables": kwargs.get("tables", "见任务描述"),
                "query_requirements": kwargs.get("query_requirements", description),
                "output_format": kwargs.get("output_format", "JSON/Markdown"),
                "output_content": kwargs.get("output_content", "查询结果"),
                "table": kwargs.get("table", "tasks"),
            })
        
        elif task_type == "file_processing":
            context.update({
                "input_path": kwargs.get("input_path", "请指定输入文件"),
                "input_format": kwargs.get("input_format", "未知"),
                "file_description": kwargs.get("file_description", ""),
                "processing_requirements": kwargs.get("processing_requirements", description),
                "processing_steps": kwargs.get("processing_steps", "根据任务要求处理"),
                "output_format": kwargs.get("output_format", "根据任务要求"),
                "naming_convention": kwargs.get("naming_convention", f"{task_id}_output"),
                "content_requirements": kwargs.get("content_requirements", "符合任务要求"),
                "completion_criteria": kwargs.get("completion_criteria", "处理完成且结果正确"),
            })
        
        elif task_type == "research":
            context.update({
                "research_topic": kwargs.get("research_topic", description),
                "research_objectives": kwargs.get("research_objectives", "深入了解主题"),
                "report_structure": kwargs.get("report_structure", "背景/现状/趋势/建议"),
                "word_count": kwargs.get("word_count", "1000-2000字"),
            })
        
        elif task_type == "content_generation":
            context.update({
                "generation_goal": kwargs.get("generation_goal", description),
                "content_type": kwargs.get("content_type", "文章"),
                "topic": kwargs.get("topic", "见任务描述"),
                "style": kwargs.get("style", "专业"),
                "length": kwargs.get("length", "适中"),
                "reference_materials": kwargs.get("reference_materials", "无"),
                "output_format": kwargs.get("output_format", "Markdown"),
                "naming_convention": kwargs.get("naming_convention", f"{task_id}_content.md"),
            })
        
        elif task_type == "data_analysis":
            context.update({
                "analysis_goal": kwargs.get("analysis_goal", description),
                "data_source": kwargs.get("data_source", "请指定数据源"),
                "data_format": kwargs.get("data_format", "未知"),
                "data_description": kwargs.get("data_description", ""),
                "analysis_requirements": kwargs.get("analysis_requirements", description),
            })
        
        else:  # base template
            context.update({
                "input_data": kwargs.get("input_data", "见任务描述"),
                "output_format": kwargs.get("output_format", "根据任务要求"),
                "output_location": kwargs.get("output_location", task_workspace),
                "naming_convention": kwargs.get("naming_convention", f"{task_id}_*"),
                "estimated_hours": kwargs.get("estimated_hours", 2),
                "completion_criteria": kwargs.get("completion_criteria", "任务要求全部完成"),
            })
        
        return template.format(**context)
    
    def get_available_templates(self) -> list:
        """获取可用模板列表"""
        return [
            {"id": "base", "name": "基础任务", "description": "通用任务模板"},
            {"id": "database_query", "name": "数据库查询", "description": "查询数据库并生成报告"},
            {"id": "file_processing", "name": "文件处理", "description": "处理文件并生成输出"},
            {"id": "research", "name": "研究调研", "description": "网络调研并生成报告"},
            {"id": "content_generation", "name": "内容生成", "description": "生成文章、文档等内容"},
            {"id": "data_analysis", "name": "数据分析", "description": "分析数据并生成报告"},
        ]
