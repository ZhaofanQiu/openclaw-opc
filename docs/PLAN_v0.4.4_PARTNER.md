# v0.4.4 Partner Agent 功能规划

## 版本信息
- **版本**: v0.4.4
- **代号**: Partner Intelligence
- **目标**: 引入合伙人员工作为智能管理助手

---

## 核心设计理念

### Partner 定位
Partner（合伙人）是一个特殊的员工（position_level = 5），具备以下特性：
1. **完整员工功能** - 可被分配任务，执行 Bridge Skill
2. **全局悬浮框** - 跨所有页面存在的交互入口
3. **智能辅助** - 在关键流程中隐式介入，减少用户工作量

### 交互模式
```
┌─────────────────────────────────────────────────────────────────┐
│                     Partner 交互架构                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   用户输入    │────▶│  Partner Chat │────▶│   OPC Core   │    │
│  │  (悬浮框/页面)│     │   (悬浮框 UI) │     │  (API/Service)│    │
│  └──────────────┘     └──────────────┘     └──────┬───────┘    │
│                                                   │             │
│                           ┌───────────────────────┘             │
│                           ▼                                     │
│                    ┌──────────────┐                            │
│                    │ Partner Agent│                            │
│                    │ (OpenClaw)   │                            │
│                    └──────┬───────┘                            │
│                           │                                     │
│                           ▼                                     │
│                    ┌──────────────┐                            │
│                    │  解析回复    │                            │
│                    │ 检测OPC-ACTION│                            │
│                    └──────┬───────┘                            │
│                           │                                     │
│              ┌────────────┼────────────┐                       │
│              ▼            ▼            ▼                       │
│        ┌─────────┐ ┌──────────┐ ┌──────────┐                  │
│        │直接回复  │ │执行操作  │ │返回结果  │                  │
│        │(纯文本) │ │(创建任务等)│ │给用户    │                  │
│        └─────────┘ └──────────┘ └──────────┘                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四模块详细规划

### 1. opc-database 模块

#### 1.1 数据模型

**文件**: `packages/opc-database/src/opc_database/models/partner_message.py`

```python
class PartnerMessage(Base):
    """Partner 聊天记录
    
    存储用户与 Partner 的对话历史，支持上下文理解
    """
    __tablename__ = "partner_messages"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    partner_id: Mapped[str] = mapped_column(String, index=True)
    
    # 消息角色: user(用户) | partner(合伙人) | system(系统)
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    
    # 操作指令记录
    has_action: Mapped[bool] = mapped_column(default=False)
    action_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    action_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    action_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 元数据
    context_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 对话时的公司状态快照
    created_at: Mapped[datetime] = mapped_column(default_factory=datetime.utcnow)
    
    # 索引
    __table_args__ = (
        Index('idx_partner_created', 'partner_id', 'created_at'),
    )
```

#### 1.2 Repository

**文件**: `packages/opc-database/src/opc_database/repositories/partner_message_repository.py`

```python
class PartnerMessageRepository(BaseRepository[PartnerMessage]):
    async def get_recent_messages(
        self, 
        partner_id: str, 
        limit: int = 20,
        before_id: Optional[str] = None
    ) -> List[PartnerMessage]:
        """获取最近聊天记录"""
        
    async def get_messages_by_date_range(
        self,
        partner_id: str,
        start: datetime,
        end: datetime
    ) -> List[PartnerMessage]:
        """按时间范围查询"""
        
    async def clear_history_before(
        self,
        partner_id: str,
        before: datetime
    ) -> int:
        """清理历史记录，返回删除数量"""
```

---

### 2. opc-openclaw 模块

复用现有组件，无需新增文件。

**复用组件**:
- `CLIMessenger` - 发送消息给 Partner Agent
- `ResponseParser` - 可扩展解析 `OPC-ACTION` 块

**可选扩展** (`parser.py`):
```python
@dataclass
class ParsedAction:
    action: str           # create_task, create_workflow, etc.
    params: dict
    is_valid: bool
    raw_text: str

class ResponseParser:
    @classmethod
    def parse_action(cls, text: str) -> Optional[ParsedAction]:
        """解析 OPC-ACTION 块"""
        pattern = r'---OPC-ACTION---\n(.*?)\n---END-ACTION---'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                return ParsedAction(
                    action=data.get('action'),
                    params=data.get('params', {}),
                    is_valid=True,
                    raw_text=match.group(0)
                )
            except json.JSONDecodeError:
                pass
        return None
```

---

### 3. opc-core 模块

#### 3.1 API 路由

**文件**: `packages/opc-core/src/opc_core/api/partner.py`

```python
router = APIRouter(prefix="/partner", tags=["partner"])

# ========== 基础聊天 ==========

@router.post("/chat")
async def chat_with_partner(
    request: ChatRequest,
    partner_service: PartnerService = Depends(get_partner_service)
) -> ChatResponse:
    """
    与 Partner 对话
    
    流程:
    1. 保存用户消息
    2. 构建上下文（历史记录 + 系统提示）
    3. 发送给 Partner Agent
    4. 解析回复，检测操作指令
    5. 执行指令（如有）
    6. 保存 Partner 回复
    7. 返回结果
    """

@router.get("/history")
async def get_chat_history(
    partner_id: str,
    limit: int = Query(20, ge=1, le=100),
    message_repo: PartnerMessageRepository = Depends(get_partner_message_repo)
) -> List[MessageHistoryItem]:
    """获取聊天历史"""

@router.delete("/history/{partner_id}")
async def clear_chat_history(
    partner_id: str,
    message_repo: PartnerMessageRepository = Depends(get_partner_message_repo)
) -> ClearHistoryResponse:
    """清空聊天记录"""

# ========== 智能辅助 ==========

@router.post("/assist/create-employee")
async def assist_create_employee(
    request: EmployeeAssistRequest,
    partner_service: PartnerService = Depends(get_partner_service)
) -> EmployeeAssistResponse:
    """
    智能辅助创建员工
    
    Partner 会：
    1. 阅读公司手册和 Partner 手册
    2. 根据用户意图设计员工背景、性格、行事风格
    3. 生成员工手册内容
    4. 返回完整设计方案
    """

@router.post("/assist/create-task")
async def assist_create_task(
    request: TaskAssistRequest,
    partner_service: PartnerService = Depends(get_partner_service)
) -> TaskAssistResponse:
    """
    智能辅助创建任务
    
    Partner 会：
    1. 阅读相关手册
    2. 细化任务需求和验收标准
    3. 拆分执行步骤
    4. 预估成本（基于 OC币/Token 换算策略）
    5. 推荐执行员工
    6. 生成任务手册
    """

@router.post("/assist/create-workflow")
async def assist_create_workflow(
    request: WorkflowAssistRequest,
    partner_service: PartnerService = Depends(get_partner_service)
) -> WorkflowAssistResponse:
    """
    一句话创建工作流
    
    用户输入: "帮我做一个内容创作流程，从选题到发布"
    
    Partner 会：
    1. 阅读公司手册了解业务背景
    2. 拆分为合理步骤（3-5步）
    3. 为每步匹配最佳员工
    4. 预估每步成本
    5. 返回可预览的工作流配置
    """

@router.post("/assist/update-company-manual")
async def assist_update_company_manual(
    request: UpdateManualRequest,
    partner_service: PartnerService = Depends(get_partner_service)
) -> UpdateManualResponse:
    """
    智能修改公司手册
    
    Partner 会：
    1. 阅读现有公司手册
    2. 根据用户请求修改内容
    3. 返回更新后的完整手册
    """
```

#### 3.2 Partner Service

**文件**: `packages/opc-core/src/opc_core/services/partner_service.py`

```python
class PartnerService:
    """Partner 业务逻辑服务"""
    
    def __init__(
        self,
        message_repo: PartnerMessageRepository,
        employee_repo: EmployeeRepository,
        task_repo: TaskRepository,
        manual_service: ManualService,
        messenger: Optional[CLIMessenger] = None
    ):
        self.message_repo = message_repo
        self.employee_repo = employee_repo
        self.task_repo = task_repo
        self.manual_service = manual_service
        self.messenger = messenger or CLIMessenger()
    
    # ========== 系统提示词 ==========
    
    PARTNER_SYSTEM_PROMPT = """你是 OpenClaw OPC 的 Partner（合伙人），是用户的智能管理助手。

## 你的职责
1. 帮助用户快速完成管理任务
2. 通过对话理解用户需求并执行操作
3. 在辅助决策时提供专业的预算评估

## OC 币与 Token 换算策略
- 1 OC币 ≈ 1000 Tokens（经验换算）
- 任务成本预估参考：
  * 简单任务（研究、查询）：50-100 OC币 ≈ 5万-10万 Tokens
  * 中等任务（分析、写作）：100-300 OC币 ≈ 10万-30万 Tokens
  * 复杂任务（代码开发、多步骤分析）：300-800 OC币 ≈ 30万-80万 Tokens
  * 工作流任务：每个步骤按上述标准累加
- 创建任务时必须给出合理的成本预估

## 操作指令格式
当你需要执行操作时，在回复末尾使用：

---OPC-ACTION---
{
    "action": "create_task",
    "params": {
        "title": "任务标题",
        "description": "任务描述",
        "employee_id": "emp_xxx",
        "estimated_cost": 100
    }
}
---END-ACTION---

支持的操作：
- create_task: 创建任务
- create_workflow: 创建工作流
- write_employee_manual: 编写员工手册
- write_task_manual: 编写任务手册
- update_company_manual: 更新公司手册
- get_company_status: 获取公司状态

## 正常回复
如果只是对话，直接回复即可，无需添加 OPC-ACTION 块。
"""
    
    # ========== 基础聊天 ==========
    
    async def chat(self, user_message: str) -> ChatResult:
        """
        与 Partner 对话
        
        流程：
        1. 查找 Partner 员工
        2. 获取历史记录
        3. 构建消息（系统提示 + 历史 + 用户输入）
        4. 发送给 Agent
        5. 解析回复
        6. 执行操作（如有）
        7. 保存记录
        """
        # 1. 查找 Partner
        partner = await self._get_partner_employee()
        if not partner:
            raise PartnerNotFoundError("未找到 Partner 员工，请先创建")
        
        # 2. 获取历史记录
        history = await self.message_repo.get_recent_messages(
            partner.id, limit=10
        )
        
        # 3. 构建消息
        full_message = self._build_chat_message(
            history=history,
            user_message=user_message
        )
        
        # 4. 发送给 Agent
        response = await self.messenger.send(
            agent_id=partner.openclaw_agent_id,
            message=full_message,
            timeout=60
        )
        
        # 5. 保存用户消息
        await self.message_repo.create(PartnerMessage(
            id=generate_id(),
            partner_id=partner.id,
            role="user",
            content=user_message
        ))
        
        # 6. 解析回复
        reply_content = response.content
        action = self._parse_action(reply_content)
        
        # 7. 执行操作
        action_result = None
        if action:
            action_result = await self._execute_action(action)
            # 移除操作指令，只保留可读部分给用户
            reply_content = self._remove_action_block(reply_content)
            reply_content += f"\n\n✅ 已执行: {action['action']}"
        
        # 8. 保存 Partner 回复
        await self.message_repo.create(PartnerMessage(
            id=generate_id(),
            partner_id=partner.id,
            role="partner",
            content=response.content,
            has_action=bool(action),
            action_type=action['action'] if action else None,
            action_params=action.get('params') if action else None,
            action_result=action_result
        ))
        
        return ChatResult(
            reply=reply_content,
            action_executed=action['action'] if action else None,
            action_result=action_result
        )
    
    # ========== 智能辅助 ==========
    
    async def assist_create_employee(
        self,
        name: str,
        job_type: str,
        user_intent: str
    ) -> EmployeeAssistResult:
        """
        智能辅助创建员工
        
        Partner 会阅读手册后设计员工形象
        """
        partner = await self._get_partner_employee()
        
        # 读取手册
        company_manual = await self.manual_service.read_company_manual()
        partner_manual = await self.manual_service.read_employee_manual(partner.id)
        
        prompt = f"""{self.PARTNER_SYSTEM_PROMPT}

## 当前任务：设计新员工
用户想要创建一名新员工：
- 姓名: {name}
- 岗位: {job_type}
- 意图/需求: {user_intent}

## 参考信息

### 公司手册（了解公司文化和规范）
{company_manual}

### 你的员工手册（了解你的职责）
{partner_manual}

## 请提供
请以 JSON 格式返回：
{{
    "background": "员工背景故事（200字左右）",
    "personality": "性格特点（100字左右）",
    "working_style": "行事风格和工作习惯（100字左右）",
    "skills": ["技能1", "技能2", "技能3"],
    "suggested_avatar_emoji": "推荐头像emoji",
    "manual_content": "完整的员工手册内容（Markdown格式）"
}}
"""
        
        response = await self.messenger.send(
            agent_id=partner.openclaw_agent_id,
            message=prompt,
            timeout=90
        )
        
        # 解析 JSON 响应
        design = self._parse_json_response(response.content)
        
        return EmployeeAssistResult(
            name=name,
            job_type=job_type,
            background=design["background"],
            personality=design["personality"],
            working_style=design["working_style"],
            skills=design["skills"],
            suggested_avatar_emoji=design.get("suggested_avatar_emoji", "👤"),
            manual_content=design["manual_content"]
        )
    
    async def assist_create_task(
        self,
        title: str,
        description: str,
        employee_id: Optional[str] = None
    ) -> TaskAssistResult:
        """
        智能辅助创建任务
        
        Partner 阅读手册后细化任务需求
        """
        partner = await self._get_partner_employee()
        
        # 获取上下文
        company_manual = await self.manual_service.read_company_manual()
        employees = await self.employee_repo.get_all_active()
        
        # 如果指定了员工，读取其手册
        employee_manual = ""
        if employee_id:
            employee = await self.employee_repo.get_by_id(employee_id)
            if employee:
                employee_manual = await self.manual_service.read_employee_manual(employee_id)
        
        prompt = f"""{self.PARTNER_SYSTEM_PROMPT}

## 当前任务：细化任务需求
用户想要创建任务：
- 标题: {title}
- 描述: {description}
{f"- 指定员工: {employee.name}" if employee_id else "- 未指定员工，请推荐"}

## 参考信息

### 公司手册
{company_manual}

{f"### 执行员工手册\n{employee_manual}\n" if employee_manual else ""}

### 可用员工列表
{self._format_employees_list(employees)}

## 请提供
请以 JSON 格式返回：
{{
    "refined_title": "优化后的标题",
    "refined_description": "细化后的详细描述（包含验收标准）",
    "execution_steps": ["步骤1", "步骤2", "步骤3"],
    "estimated_cost": 150,
    "cost_reasoning": "成本估算理由",
    "suggested_employee_id": "推荐员工ID",
    "employee_reasoning": "推荐理由",
    "manual_content": "任务手册内容（Markdown格式）"
}}

注意：estimated_cost 请基于 OC币/Token 换算策略给出合理预估。
"""
        
        response = await self.messenger.send(
            agent_id=partner.openclaw_agent_id,
            message=prompt,
            timeout=90
        )
        
        result = self._parse_json_response(response.content)
        
        return TaskAssistResult(**result)
    
    async def assist_create_workflow(
        self,
        natural_language_description: str
    ) -> WorkflowAssistResult:
        """
        一句话创建工作流
        
        示例输入："帮我做一个内容创作流程，从选题到发布"
        """
        partner = await self._get_partner_employee()
        
        # 获取上下文
        company_manual = await self.manual_service.read_company_manual()
        employees = await self.employee_repo.get_all_active()
        
        prompt = f"""{self.PARTNER_SYSTEM_PROMPT}

## 当前任务：设计工作流
用户用自然语言描述：
"{natural_language_description}"

## 参考信息

### 公司手册（了解业务背景）
{company_manual}

### 可用员工列表（为每步选择最合适的）
{self._format_employees_list(employees)}

## 请提供
请以 JSON 格式返回：
{{
    "name": "工作流名称（简洁）",
    "description": "工作流描述",
    "steps": [
        {{
            "title": "步骤标题",
            "description": "详细描述",
            "assigned_to": "员工ID",
            "estimated_cost": 100,
            "cost_reasoning": "成本理由"
        }}
    ],
    "total_estimated_cost": 500,
    "workflow_reasoning": "整体设计思路"
}}

注意：
1. 拆分为 3-5 个合理步骤
2. 为每步选择最适合的员工
3. 每步成本基于 OC币/Token 换算策略
4. 总成本为各步骤之和
"""
        
        response = await self.messenger.send(
            agent_id=partner.openclaw_agent_id,
            message=prompt,
            timeout=120
        )
        
        result = self._parse_json_response(response.content)
        
        return WorkflowAssistResult(**result)
    
    async def assist_update_company_manual(
        self,
        user_request: str
    ) -> UpdateManualResult:
        """
        智能修改公司手册
        """
        partner = await self._get_partner_employee()
        
        # 读取现有手册
        current_manual = await self.manual_service.read_company_manual()
        
        prompt = f"""{self.PARTNER_SYSTEM_PROMPT}

## 当前任务：修改公司手册

### 现有公司手册
{current_manual}

### 用户修改请求
{user_request}

## 请提供
请修改公司手册，返回完整的更新后内容（Markdown格式）。
如果用户请求是添加新章节，请保持在合适的位置。
如果是修改现有内容，请保持其他部分不变。

请直接返回完整的更新后手册内容，不需要 JSON 格式。
"""
        
        response = await self.messenger.send(
            agent_id=partner.openclaw_agent_id,
            message=prompt,
            timeout=90
        )
        
        return UpdateManualResult(
            updated_content=response.content,
            changes_summary="根据用户请求更新了手册"
        )
    
    # ========== 内部方法 ==========
    
    async def _get_partner_employee(self) -> Optional[Employee]:
        """获取 Partner 员工（position_level = 5）"""
        return await self.employee_repo.get_by_position_level(
            PositionLevel.PARTNER
        )
    
    def _build_chat_message(
        self,
        history: List[PartnerMessage],
        user_message: str
    ) -> str:
        """构建聊天消息"""
        sections = [self.PARTNER_SYSTEM_PROMPT]
        
        # 添加上下文信息
        context = await self._get_company_context()
        sections.append(f"\n## 当前公司状态\n{context}\n")
        
        # 添加历史记录
        if history:
            sections.append("## 对话历史")
            for msg in history:
                role_name = "用户" if msg.role == "user" else "Partner"
                sections.append(f"{role_name}: {msg.content}")
        
        # 添加用户输入
        sections.append(f"\n用户: {user_message}")
        sections.append("\nPartner: ")
        
        return "\n\n".join(sections)
    
    def _parse_action(self, text: str) -> Optional[dict]:
        """解析 OPC-ACTION 块"""
        # 使用 ResponseParser 或正则表达式
        pattern = r'---OPC-ACTION---\n(.*?)\n---END-ACTION---'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None
    
    def _remove_action_block(self, text: str) -> str:
        """移除操作指令块，保留可读内容"""
        pattern = r'\n?---OPC-ACTION---.*?---END-ACTION---\n?'
        return re.sub(pattern, '', text, flags=re.DOTALL).strip()
    
    async def _execute_action(self, action: dict) -> dict:
        """执行操作指令"""
        action_type = action.get('action')
        params = action.get('params', {})
        
        if action_type == 'create_task':
            task = await self.task_service.create_task(**params)
            return {
                'success': True,
                'task_id': task.id,
                'message': f"任务 '{task.title}' 已创建"
            }
        
        elif action_type == 'create_workflow':
            workflow = await self.workflow_service.create_workflow(**params)
            return {
                'success': True,
                'workflow_id': workflow.id,
                'message': f"工作流 '{workflow.name}' 已创建"
            }
        
        elif action_type == 'write_employee_manual':
            manual = await self.manual_service.generate_employee_manual(**params)
            return {
                'success': True,
                'manual_path': manual.path,
                'message': "员工手册已生成"
            }
        
        elif action_type == 'update_company_manual':
            await self.manual_service.update_company_manual(**params)
            return {
                'success': True,
                'message': "公司手册已更新"
            }
        
        elif action_type == 'get_company_status':
            status = await self._get_company_context()
            return {
                'success': True,
                'status': status
            }
        
        else:
            return {
                'success': False,
                'error': f"未知操作: {action_type}"
            }
```

---

### 4. opc-ui 模块

#### 4.1 全局悬浮框

**文件**: `packages/opc-ui/src/components/partner/PartnerWidget.vue`

```vue
<template>
  <div class="partner-widget" :class="{ 'expanded': isOpen }">
    <!-- 头部（点击展开/收起） -->
    <div class="partner-widget-header" @click="toggleChat">
      <div class="partner-avatar">👑</div>
      <div class="partner-info">
        <div class="partner-name">Partner</div>
        <div class="partner-status">
          {{ isOpen ? '在线 - 点击收起' : '点击展开对话' }}
        </div>
      </div>
      <div class="partner-toggle">
        {{ isOpen ? '▼' : '▲' }}
      </div>
    </div>
    
    <!-- 聊天窗口 -->
    <div v-show="isOpen" class="partner-chat-container">
      <!-- 快捷操作栏 -->
      <div class="quick-actions-bar">
        <button 
          v-for="action in quickActions" 
          :key="action.id"
          @click.stop="handleQuickAction(action)"
          :title="action.description"
        >
          <span class="icon">{{ action.icon }}</span>
          <span class="label">{{ action.label }}</span>
        </button>
      </div>
      
      <!-- 消息列表 -->
      <div class="partner-chat-messages" ref="messagesContainer">
        <div 
          v-for="(msg, index) in messages" 
          :key="index"
          :class="['chat-message', msg.role]"
        >
          <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
          <div v-if="msg.action" class="message-action">
            ✅ 已执行: {{ msg.action }}
          </div>
        </div>
        
        <!-- 加载状态 -->
        <div v-if="loading" class="chat-message partner loading">
          <span class="dot-flashing"></span>
        </div>
      </div>
      
      <!-- 输入框 -->
      <div class="partner-chat-input-area">
        <input 
          ref="inputRef"
          v-model="inputMessage" 
          @keyup.enter="sendMessage"
          placeholder="输入消息，或点击上方快捷按钮..."
          :disabled="loading"
        />
        <button 
          @click="sendMessage" 
          :disabled="!inputMessage.trim() || loading"
        >
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { usePartnerStore } from '@/stores/partner'
import { marked } from 'marked'

const partnerStore = usePartnerStore()
const isOpen = ref(false)
const inputMessage = ref('')
const loading = ref(false)
const messagesContainer = ref(null)
const inputRef = ref(null)

// 快捷操作
const quickActions = [
  { 
    id: 'create_task', 
    icon: '📝', 
    label: '任务',
    description: '快速创建任务',
    handler: () => openCreateTaskDialog()
  },
  { 
    id: 'create_workflow', 
    icon: '🔄', 
    label: '工作流',
    description: '一句话创建工作流',
    handler: () => openCreateWorkflowDialog()
  },
  { 
    id: 'create_employee', 
    icon: '👤', 
    label: '员工',
    description: '智能创建员工',
    handler: () => openCreateEmployeeDialog()
  },
  { 
    id: 'update_manual', 
    icon: '📖', 
    label: '手册',
    description: '修改公司手册',
    handler: () => openUpdateManualDialog()
  },
  { 
    id: 'view_status', 
    icon: '📊', 
    label: '状态',
    description: '查看公司状态',
    handler: () => viewCompanyStatus()
  }
]

const toggleChat = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    nextTick(() => {
      scrollToBottom()
      inputRef.value?.focus()
    })
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return
  
  const message = inputMessage.value
  inputMessage.value = ''
  loading.value = true
  
  try {
    const result = await partnerStore.sendMessage(message)
    // result 包含 reply, action_executed, action_result
  } finally {
    loading.value = false
    nextTick(scrollToBottom)
  }
}

const handleQuickAction = (action) => {
  action.handler()
}

// 快捷操作对话框
const openCreateWorkflowDialog = () => {
  // 打开对话框，让用户输入自然语言描述
  // 调用 partnerStore.assistCreateWorkflow(description)
  // 显示预览，确认后创建
}

const openCreateEmployeeDialog = () => {
  // 类似流程...
}

const openUpdateManualDialog = () => {
  // 打开手册编辑对话框
  // 显示当前手册内容
  // 用户输入修改请求
  // 调用 partnerStore.assistUpdateManual(request)
  // 显示 diff/预览，确认后更新
}

const renderMarkdown = (text) => {
  return marked.parse(text, { breaks: true })
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

onMounted(() => {
  partnerStore.loadHistory()
})
</script>

<style scoped>
.partner-widget {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 60px;
  height: 60px;
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 30px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  z-index: 1000;
  overflow: hidden;
  transition: all 0.3s ease;
}

.partner-widget.expanded {
  width: 380px;
  height: 500px;
  border-radius: 16px;
}

.partner-widget-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
  cursor: pointer;
  height: 60px;
}

.partner-avatar {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.partner-info {
  flex: 1;
  min-width: 0;
}

.partner-name {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.partner-status {
  font-size: 12px;
  color: #888;
}

.partner-toggle {
  font-size: 12px;
  color: #888;
  transition: transform 0.3s;
}

.partner-chat-container {
  height: 440px;
  display: flex;
  flex-direction: column;
  background: #141425;
}

.quick-actions-bar {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid #2a2a4a;
  overflow-x: auto;
}

.quick-actions-bar button {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid #667eea;
  background: transparent;
  color: #667eea;
  border-radius: 16px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.quick-actions-bar button:hover {
  background: #667eea20;
}

.partner-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-message {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
}

.chat-message.user {
  align-self: flex-end;
  background: #667eea;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-message.partner {
  align-self: flex-start;
  background: #2a2a4a;
  color: #e0e0e0;
  border-bottom-left-radius: 4px;
}

.chat-message.loading {
  background: transparent;
}

.partner-chat-input-area {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #2a2a4a;
  background: #1a1a2e;
}

.partner-chat-input-area input {
  flex: 1;
  background: #252542;
  border: 1px solid #3a3a5a;
  color: #fff;
  padding: 10px 14px;
  border-radius: 20px;
  font-size: 14px;
  outline: none;
}

.partner-chat-input-area input:focus {
  border-color: #667eea;
}

.partner-chat-input-area button {
  padding: 10px 20px;
  background: #667eea;
  border: none;
  color: #fff;
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.partner-chat-input-area button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 加载动画 */
.dot-flashing {
  position: relative;
  width: 10px;
  height: 10px;
  border-radius: 5px;
  background-color: #667eea;
  color: #667eea;
  animation: dot-flashing 1s infinite linear alternate;
  animation-delay: 0.5s;
}

@keyframes dot-flashing {
  0% { background-color: #667eea; }
  50%, 100% { background-color: #2a2a4a; }
}
</style>
```

#### 4.2 全局挂载

**文件**: `packages/opc-ui/src/App.vue`

```vue
<template>
  <div class="app">
    <AppHeader />
    <div class="main-layout">
      <AppSidebar />
      <main class="content">
        <router-view />
      </main>
    </div>
    
    <!-- Partner Widget - 全局存在 -->
    <Suspense>
      <template #default>
        <PartnerWidget v-if="hasPartner" />
        <PartnerOnboarding v-else-if="showOnboarding" />
      </template>
      <template #fallback>
        <div class="partner-loading">加载中...</div>
      </template>
    </Suspense>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { usePartnerStore } from '@/stores/partner'
import PartnerWidget from '@/components/partner/PartnerWidget.vue'
import PartnerOnboarding from '@/components/partner/PartnerOnboarding.vue'

const partnerStore = usePartnerStore()

const hasPartner = computed(() => partnerStore.hasPartner)
const showOnboarding = computed(() => partnerStore.showOnboarding)

onMounted(() => {
  partnerStore.initialize()
})
</script>
```

#### 4.3 Partner Store

**文件**: `packages/opc-ui/src/stores/partner.js`

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/utils/api'

export const usePartnerStore = defineStore('partner', () => {
  // State
  const partnerId = ref(null)
  const messages = ref([])
  const isLoading = ref(false)
  const isInitialized = ref(false)
  
  // Getters
  const hasPartner = computed(() => !!partnerId.value)
  const showOnboarding = computed(() => isInitialized.value && !hasPartner.value)
  
  // Actions
  async function initialize() {
    // 查找 Partner 员工
    const employees = await api.get('/employees')
    const partner = employees.find(e => e.position_level === 5)
    
    if (partner) {
      partnerId.value = partner.id
      await loadHistory()
    }
    
    isInitialized.value = true
  }
  
  async function loadHistory() {
    if (!partnerId.value) return
    
    const history = await api.get(`/partner/history?partner_id=${partnerId.value}&limit=50`)
    messages.value = history
  }
  
  async function sendMessage(content) {
    if (!partnerId.value || isLoading.value) return
    
    // 乐观更新：立即显示用户消息
    messages.value.push({ role: 'user', content })
    isLoading.value = true
    
    try {
      const result = await api.post('/partner/chat', {
        partner_id: partnerId.value,
        message: content
      })
      
      // 添加 Partner 回复
      messages.value.push({
        role: 'partner',
        content: result.reply,
        action: result.action_executed
      })
      
      return result
    } finally {
      isLoading.value = false
    }
  }
  
  // 智能辅助方法
  async function assistCreateEmployee(data) {
    return await api.post('/partner/assist/create-employee', data)
  }
  
  async function assistCreateTask(data) {
    return await api.post('/partner/assist/create-task', data)
  }
  
  async function assistCreateWorkflow(data) {
    return await api.post('/partner/assist/create-workflow', data)
  }
  
  async function assistUpdateManual(data) {
    return await api.post('/partner/assist/update-company-manual', data)
  }
  
  return {
    partnerId,
    messages,
    isLoading,
    hasPartner,
    showOnboarding,
    initialize,
    loadHistory,
    sendMessage,
    assistCreateEmployee,
    assistCreateTask,
    assistCreateWorkflow,
    assistUpdateManual
  }
})
```

---

## 实施计划

### Phase 1: 基础架构 (P0)
| 模块 | 任务 | 文件 |
|------|------|------|
| opc-database | PartnerMessage 模型 | `models/partner_message.py` |
| opc-database | Repository | `repositories/partner_message_repository.py` |
| opc-core | PartnerService 框架 | `services/partner_service.py` |
| opc-core | 基础聊天 API | `api/partner.py` |
| opc-ui | PartnerWidget 组件 | `components/partner/PartnerWidget.vue` |
| opc-ui | Partner Store | `stores/partner.js` |
| opc-ui | 全局挂载 | `App.vue` |

### Phase 2: 智能辅助 (P1)
| 功能 | API | UI 集成 |
|------|-----|---------|
| 辅助创建员工 | `POST /partner/assist/create-employee` | EmployeeCreateModal 添加按钮 |
| 辅助创建任务 | `POST /partner/assist/create-task` | TaskCreateModal 添加按钮 |
| 一句话工作流 | `POST /partner/assist/create-workflow` | 悬浮框快捷按钮 + 预览对话框 |

### Phase 3: 手册管理 (P2)
| 功能 | API | UI 集成 |
|------|-----|---------|
| 修改公司手册 | `POST /partner/assist/update-company-manual` | 悬浮框快捷按钮 + 手册编辑对话框 |

### Phase 4: 优化 (P3)
- 消息搜索
- 历史记录分页
- 快捷操作自定义

---

## 关键设计决策

1. **不新增 Skill**: Partner 使用现有 Bridge Skill，差异化通过 Prompt 实现
2. **全局悬浮框**: PartnerWidget 挂载在 App.vue，跨所有页面存在
3. **手册注入**: 所有辅助功能都先读取公司手册和员工手册
4. **OC币策略**: 在 System Prompt 中明确定义 OC币/Token 换算关系
5. **操作指令**: 使用 `OPC-ACTION` 块让 Partner 能执行具体操作

---

*规划版本: v0.4.4-PARTNER*
*最后更新: 2026-03-27*
