# OPC 员工任务分配系统设计

## 核心方法论

1. **单向通信**: OPC主动发送任务，员工被动接收
2. **聊天形式**: 所有交互通过异步消息完成
3. **自包含任务**: 任务消息包含所有必要信息（数据库访问、工具调用等）
4. **结果导向**: 员工只返回完成结果或失败原因

---

## 任务消息模板

### 1. 基础任务模板

```
📋 **任务分配** | 任务ID: {task_id} | 优先级: {priority}

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
完成后请回复：
```
STATUS: completed/failed
RESULT: [结果摘要或失败原因]
OUTPUT_PATH: [输出文件路径或数据库记录ID]
TOKEN_USED: [实际消耗token数]
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2. 数据库访问任务模板

```
📋 **数据库查询任务** | 任务ID: {task_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 任务目标
{task_goal}

## 🔗 数据库连接信息
- **类型**: SQLite
- **路径**: /data/opc.db
- **表**: {table_name}

## 📊 可用查询
你可以使用 opc_query(sql) 函数执行查询：
```python
# 示例查询
result = opc_query("SELECT * FROM tasks WHERE status = 'pending'")
```

## 📝 任务要求
{specific_requirements}

## 📤 输出要求
将结果保存到: {output_path}
格式: JSON/CSV/Markdown

## ✅ 完成标准
- 数据查询正确
- 结果格式符合要求
- 输出文件已生成

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 3. 文件处理任务模板

```
📋 **文件处理任务** | 任务ID: {task_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📁 输入文件
- **路径**: {input_path}
- **格式**: {file_format}

## 🛠️ 处理要求
{processing_requirements}

## 📤 输出要求
- **路径**: {output_path}
- **格式**: {output_format}
- **命名**: {naming_rule}

## ✅ 完成标准
{completion_criteria}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 4. 研究/搜索任务模板

```
📋 **研究任务** | 任务ID: {task_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🔍 研究主题
{research_topic}

## 🛠️ 可用工具
- 搜索: 使用 web_search(query) 函数
- 获取网页: 使用 web_fetch(url) 函数

## 📝 报告要求
- **结构**: 背景/现状/趋势/建议
- **字数**: {word_count}
- **引用**: 需要标注来源

## 📤 输出
保存到: {output_path}/research_report_{task_id}.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 前端界面改装方案

### 员工详情页改版

```
┌─────────────────────────────────────────────────────┐
│ 👤 员工名称                    [状态: 在线] [💰预算]  │
├─────────────────────────────────────────────────────┤
│  📋 任务列表  |  💬 聊天历史  |  ⚙️ 技能配置        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ 🆕 快速任务分配                              │   │
│  │                                             │   │
│  │  任务类型: [搜索▼] [查询▼] [分析▼] [生成▼]   │   │
│  │  任务描述: [______________________________]   │   │
│  │  输出位置: [workspace/tasks/_____________]   │   │
│  │  预估预算: [____] OC币    优先级: [高▼]      │   │
│  │                                             │   │
│  │  [📋 使用高级模板]  [🚀 立即分配]            │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ 💬 任务执行对话                              │   │
│  │                                             │   │
│  │  OPC: 📋 任务分配 | 任务ID: task_001        │   │
│  │       请帮我分析最近一周的任务完成情况...   │   │
│  │                                             │   │
│  │  👤: ✅ STATUS: completed                   │   │
│  │      RESULT: 分析报告已完成                 │   │
│  │      OUTPUT_PATH: /tasks/report_001.md      │   │
│  │      TOKEN_USED: 1250                       │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 后端增强

### 1. 任务模板服务

```python
class TaskTemplateService:
    """任务模板生成服务"""
    
    TEMPLATES = {
        "database_query": DATABASE_QUERY_TEMPLATE,
        "file_processing": FILE_PROCESSING_TEMPLATE,
        "research": RESEARCH_TEMPLATE,
        "content_generation": CONTENT_GENERATION_TEMPLATE,
        "analysis": ANALYSIS_TEMPLATE,
    }
    
    def generate_task_message(
        self,
        task_type: str,
        task_id: str,
        description: str,
        resources: Dict,
        output_config: Dict,
        constraints: Dict
    ) -> str:
        """生成标准化的任务消息"""
        template = self.TEMPLATES.get(task_type, DEFAULT_TEMPLATE)
        return template.format(
            task_id=task_id,
            task_description=description,
            resources=resources,
            output_path=output_config.get("path"),
            budget=constraints.get("budget"),
            deadline=constraints.get("deadline"),
            # ...
        )
```

### 2. 任务解析器

```python
class TaskResponseParser:
    """解析员工任务完成反馈"""
    
    def parse_response(self, response_text: str) -> Dict:
        """
        解析员工回复，提取:
        - STATUS: completed/failed
        - RESULT: 结果摘要
        - OUTPUT_PATH: 输出路径
        - TOKEN_USED: token消耗
        """
        result = {
            "status": None,
            "result_summary": None,
            "output_path": None,
            "token_used": 0,
            "error_reason": None,
        }
        
        # 解析 STATUS
        if "STATUS: completed" in response_text:
            result["status"] = "completed"
        elif "STATUS: failed" in response_text:
            result["status"] = "failed"
        
        # 解析其他字段...
        
        return result
```

### 3. 增强的异步消息处理

```python
# 消息类型扩展
class AsyncMessageType(str, Enum):
    CHAT = "chat"           # 普通聊天
    TASK_ASSIGN = "task"    # 任务分配
    TASK_RESULT = "result"  # 任务结果
    SYSTEM = "system"       # 系统消息

# 在 process_message_async 中增加任务解析
if message.message_type == "task":
    # 解析员工回复作为任务结果
    parser = TaskResponseParser()
    task_result = parser.parse_response(result.get("text", ""))
    
    # 更新关联任务状态
    if message.related_task_id:
        task_service.update_task_result(
            task_id=message.related_task_id,
            result=task_result
        )
```

---

## 完整任务流程

### 流程图

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│ 创建任务  │────▶│ 生成任务消息  │────▶│ 异步发送给员工│
└──────────┘     └──────────────┘     └──────┬───────┘
                                             │
                              ┌──────────────▼──────────────┐
                              │ 员工处理中                   │
                              │ - 使用提供的工具/资源         │
                              │ - 按模板要求生成输出          │
                              └──────┬──────────────────────┘
                                     │
                              ┌──────▼──────────────┐
                              │ 员工返回结果         │
                              │ STATUS: completed   │
                              │ OUTPUT_PATH: xxx    │
                              └──────┬──────────────┘
                                     │
┌──────────┐     ┌──────────────┐   │
│ 任务完成  │◀────│ 解析结果并更新│◀──┘
└──────────┘     │ 任务状态      │
                 └──────────────┘
```

---

## 实施计划

### Phase 1: 后端增强
1. [ ] 创建 task_template_service.py
2. [ ] 创建 task_response_parser.py
3. [ ] 扩展 AsyncMessageType 枚举
4. [ ] 修改 process_message_async 支持任务解析

### Phase 2: 前端改装
1. [ ] 员工详情页添加快速任务分配面板
2. [ ] 任务模板选择器
3. [ ] 任务结果解析显示
4. [ ] 任务历史时间线

### Phase 3: 集成测试
1. [ ] 测试各类型任务分配
2. [ ] 测试任务完成反馈解析
3. [ ] 测试输出文件生成

---

*设计时间: 2026-03-23*
*版本: v1.0*
