"""
手册模板引擎

根据任务生成规范的手册，用于 Agent 行为控制
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from jinja2 import Template, Environment, BaseLoader

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TaskManual:
    """任务手册数据结构"""
    task_id: str
    task_title: str
    task_description: str
    template_id: str
    content: str
    constraints: List[str]
    expected_output: str
    output_format: str
    output_sections: List[str]
    reference_files: List[str]
    related_memories: List[str]


class ManualTemplate:
    """手册模板基类"""
    
    def __init__(self, template_id: str, name: str, description: str, template_text: str):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.template = Template(template_text)
    
    def render(self, context: Dict[str, Any]) -> str:
        """渲染模板"""
        return self.template.render(**context)


# 预置模板定义
TEMPLATES = {
    "code_review": ManualTemplate(
        template_id="code_review",
        name="代码审查",
        description="对代码进行审查，发现潜在问题",
        template_text="""# 任务手册: {{task_title}}

## 任务描述
{{task_description}}

## 审查范围
请对以下代码/文件进行审查：
{{files_list}}

## 审查要点
- [ ] 代码风格和规范性
- [ ] 潜在的 Bug 和错误处理
- [ ] 性能优化建议
- [ ] 安全问题
- [ ] 可维护性和可读性

## 输出格式
请以以下 JSON 格式输出审查结果：

```json
{
  "summary": "整体评价摘要",
  "issues": [
    {
      "severity": "critical|warning|suggestion",
      "location": "文件路径和行号",
      "description": "问题描述",
      "suggestion": "改进建议"
    }
  ],
  "positive_findings": ["发现的优点"],
  "overall_score": 85
}
```

## 约束条件
{{constraints_text}}

## 预计工作量
{{estimated_hours}} 小时
"""
    ),
    
    "research": ManualTemplate(
        template_id="research",
        name="研究调研",
        description="对特定主题进行研究和信息收集",
        template_text="""# 任务手册: {{task_title}}

## 研究主题
{{task_description}}

## 研究目标
1. 全面了解主题背景
2. 收集相关资料和数据
3. 分析当前现状和趋势
4. 形成结构化报告

## 研究范围
{{scope}}

## 输出格式
请以以下 Markdown 格式输出研究报告：

```markdown
# {{task_title}} 研究报告

## 执行摘要
（200字以内的核心发现）

## 背景介绍
（主题背景和相关概念）

## 研究方法
（资料来源和研究方法）

## 主要发现
### 发现1
（详细描述）

### 发现2
（详细描述）

## 数据来源
| 来源 | 类型 | 可靠性 | 链接/引用 |
|------|------|--------|-----------|
| ... | ... | ... | ... |

## 结论与建议
（总结和建议）
```

## 约束条件
{{constraints_text}}

## 质量要求
- 引用来源必须可靠
- 数据需要交叉验证
- 区分事实和观点
"""
    ),
    
    "writing": ManualTemplate(
        template_id="writing",
        name="内容创作",
        description="创作文档、文章或其他内容",
        template_text="""# 任务手册: {{task_title}}

## 创作任务
{{task_description}}

## 内容要求
- **目标受众**: {{target_audience}}
- **风格**: {{style}}
- **字数**: {{word_count}}
- **语言**: {{language}}

## 必须包含的章节
{{sections_list}}

## 输出格式
请直接输出完整的文章内容，使用 Markdown 格式。

## 质量标准
- [ ] 内容准确无误
- [ ] 逻辑清晰连贯
- [ ] 语言流畅自然
- [ ] 格式规范统一

## 约束条件
{{constraints_text}}

## 参考资源
{{references_list}}
"""
    ),
    
    "data_analysis": ManualTemplate(
        template_id="data_analysis",
        name="数据分析",
        description="对数据进行分析和可视化",
        template_text="""# 任务手册: {{task_title}}

## 分析任务
{{task_description}}

## 数据源
{{data_sources}}

## 分析目标
1. 理解数据特征和分布
2. 发现趋势和模式
3. 识别异常和问题
4. 生成可视化图表

## 分析步骤
- [ ] 数据清洗和预处理
- [ ] 描述性统计分析
- [ ] 探索性数据分析
- [ ] 生成图表和可视化
- [ ] 形成分析结论

## 输出格式
请以以下结构输出分析结果：

```json
{
  "summary": "分析摘要",
  "data_overview": {
    "total_records": 1000,
    "fields": ["字段列表"],
    "quality_issues": ["发现的数据质量问题"]
  },
  "key_findings": [
    {
      "finding": "发现描述",
      "evidence": "数据支持",
      "chart_ref": "相关图表文件名"
    }
  ],
  "charts": ["生成的图表文件名列表"],
  "recommendations": ["基于数据的建议"]
}
```

## 约束条件
{{constraints_text}}

## 技术栈
{{tech_stack}}
"""
    ),
    
    "generic": ManualTemplate(
        template_id="generic",
        name="通用任务",
        description="适用于大多数任务的通用模板",
        template_text="""# 任务手册: {{task_title}}

## 任务描述
{{task_description}}

## 预期成果
{{expected_output}}

## 执行步骤
{{execution_steps}}

## 输出格式
{{output_format}}

## 质量标准
- [ ] 符合任务要求
- [ ] 输出完整准确
- [ ] 按时完成交付

## 约束条件
{{constraints_text}}

## 注意事项
{{notes}}
"""
    ),
}


class ManualTemplateEngine:
    """
    手册模板引擎
    
    根据任务选择模板并生成手册
    """
    
    def __init__(self):
        self.templates = TEMPLATES
        logger.info("ManualTemplateEngine initialized", template_count=len(self.templates))
    
    def get_template(self, template_id: str) -> Optional[ManualTemplate]:
        """获取指定模板"""
        return self.templates.get(template_id)
    
    def list_templates(self) -> List[Dict[str, str]]:
        """列出所有可用模板"""
        return [
            {
                "id": t.template_id,
                "name": t.name,
                "description": t.description,
            }
            for t in self.templates.values()
        ]
    
    def select_template_for_task(self, task_title: str, task_description: str) -> str:
        """
        根据任务内容自动选择最合适的模板
        
        Args:
            task_title: 任务标题
            task_description: 任务描述
        
        Returns:
            模板 ID
        """
        text = (task_title + " " + task_description).lower()
        
        # 关键词匹配
        if any(kw in text for kw in ["代码", "review", "bug", "fix", "refactor", "优化"]):
            return "code_review"
        elif any(kw in text for kw in ["研究", "调研", "分析", "report", "research", "调查"]):
            return "research"
        elif any(kw in text for kw in ["写作", "文档", "文章", "content", "write", "blog"]):
            return "writing"
        elif any(kw in text for kw in ["数据", "可视化", "图表", "data", "analysis", "统计"]):
            return "data_analysis"
        else:
            return "generic"
    
    def generate_manual(
        self,
        task_id: str,
        task_title: str,
        task_description: str,
        template_id: Optional[str] = None,
        **kwargs
    ) -> TaskManual:
        """
        生成任务手册
        
        Args:
            task_id: 任务 ID
            task_title: 任务标题
            task_description: 任务描述
            template_id: 模板 ID，None 则自动选择
            **kwargs: 额外参数
        
        Returns:
            TaskManual 对象
        """
        # 自动选择模板
        if template_id is None:
            template_id = self.select_template_for_task(task_title, task_description)
            logger.info("Auto-selected template", task_id=task_id, template_id=template_id)
        
        template = self.get_template(template_id)
        if not template:
            logger.warning("Template not found, using generic", template_id=template_id)
            template = self.templates["generic"]
        
        # 准备上下文
        context = {
            "task_id": task_id,
            "task_title": task_title,
            "task_description": task_description,
            "estimated_hours": kwargs.get("estimated_hours", "2-4"),
            "files_list": kwargs.get("files_list", "待审查的文件列表"),
            "scope": kwargs.get("scope", "全面的调研范围"),
            "target_audience": kwargs.get("target_audience", "技术人员"),
            "style": kwargs.get("style", "专业、简洁"),
            "word_count": kwargs.get("word_count", "1000-2000"),
            "language": kwargs.get("language", "中文"),
            "sections_list": kwargs.get("sections_list", "- 引言\n- 正文\n- 结论"),
            "data_sources": kwargs.get("data_sources", "数据源说明"),
            "tech_stack": kwargs.get("tech_stack", "Python, pandas, matplotlib"),
            "expected_output": kwargs.get("expected_output", "完成指定的任务目标"),
            "execution_steps": kwargs.get("execution_steps", "1. 理解需求\n2. 执行任务\n3. 验证结果"),
            "output_format": kwargs.get("output_format", "根据任务要求输出"),
            "constraints_text": self._format_constraints(kwargs.get("constraints", [])),
            "references_list": kwargs.get("references_list", "- 无"),
            "notes": kwargs.get("notes", "如有疑问请及时沟通"),
        }
        
        # 渲染内容
        content = template.render(context)
        
        # 构建手册对象
        manual = TaskManual(
            task_id=task_id,
            task_title=task_title,
            task_description=task_description,
            template_id=template_id,
            content=content,
            constraints=kwargs.get("constraints", []),
            expected_output=kwargs.get("expected_output", ""),
            output_format=kwargs.get("output_format", "text"),
            output_sections=kwargs.get("output_sections", []),
            reference_files=kwargs.get("reference_files", []),
            related_memories=kwargs.get("related_memories", []),
        )
        
        logger.info("Manual generated", task_id=task_id, template_id=template_id)
        return manual
    
    def _format_constraints(self, constraints: List[str]) -> str:
        """格式化约束条件"""
        if not constraints:
            return "- 遵守公司规范\n- 按时完成任务"
        return "\n".join(f"- {c}" for c in constraints)


# 单例实例
template_engine = ManualTemplateEngine()
