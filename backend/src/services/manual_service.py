"""
Manual Generation Service (v2.0)

根据任务描述自动生成结构化手册
"""

import os
import re
from datetime import datetime
from typing import Dict, Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ManualGenerator:
    """手册生成器"""
    
    # 预置模板
    TEMPLATES = {
        "code_review": {
            "name": "代码审查",
            "keywords": ["代码", "review", "审查", "bug", "fix", "修复", "优化", "refactor"],
            "sections": [
                "## 审查范围",
                "- 代码位置: {target}",
                "- 审查重点: {focus}",
                "",
                "## 审查清单",
                "- [ ] 代码规范检查",
                "- [ ] 潜在 Bug 识别",
                "- [ ] 性能优化建议",
                "- [ ] 安全漏洞检查",
                "- [ ] 可读性评估",
                "",
                "## 输出格式",
                "```",
                "问题级别: [严重/警告/建议]",
                "位置: 文件名:行号",
                "描述: 具体问题",
                "建议: 修复方案",
                "```",
            ]
        },
        "research": {
            "name": "研究调研",
            "keywords": ["研究", "调研", "分析", "report", "报告", "调查", "趋势"],
            "sections": [
                "## 调研目标",
                "{target}",
                "",
                "## 调研维度",
                "- 背景与现状",
                "- 竞品分析",
                "- 技术方案对比",
                "- 风险评估",
                "",
                "## 输出要求",
                "- 结构化报告",
                "- 关键结论",
                "- 可执行建议",
            ]
        },
        "writing": {
            "name": "内容创作",
            "keywords": ["写作", "文档", "文章", "content", "文案", "博客", "readme"],
            "sections": [
                "## 写作任务",
                "{target}",
                "",
                "## 内容要求",
                "- 目标读者: {audience}",
                "- 风格: {style}",
                "- 字数: {length}",
                "",
                "## 结构建议",
                "- 引人入胜的开头",
                "- 清晰的逻辑结构",
                "- 有力的结论",
            ]
        },
        "data_analysis": {
            "name": "数据分析",
            "keywords": ["数据", "分析", "可视化", "图表", "统计", "analysis", "metrics"],
            "sections": [
                "## 分析目标",
                "{target}",
                "",
                "## 数据源",
                "- 数据来源: {source}",
                "- 时间范围: {time_range}",
                "",
                "## 分析步骤",
                "1. 数据清洗与验证",
                "2. 描述性统计",
                "3. 趋势分析",
                "4. 可视化呈现",
                "",
                "## 输出要求",
                "- 关键指标",
                "- 图表建议",
                "- 洞察结论",
            ]
        },
        "generic": {
            "name": "通用任务",
            "keywords": [],
            "sections": [
                "## 任务目标",
                "{target}",
                "",
                "## 执行步骤",
                "1. 理解需求",
                "2. 制定方案",
                "3. 执行实施",
                "4. 验证结果",
                "",
                "## 交付标准",
                "- 完整实现需求",
                "- 质量符合预期",
                "- 文档清晰",
            ]
        }
    }
    
    def __init__(self):
        self.manuals_dir = os.path.join(os.getcwd(), "data", "manuals")
        os.makedirs(self.manuals_dir, exist_ok=True)
    
    def detect_template(self, title: str, description: str) -> str:
        """根据任务内容检测最合适的模板"""
        text = f"{title} {description}".lower()
        
        scores = {}
        for template_id, template in self.TEMPLATES.items():
            if template_id == "generic":
                continue
            score = sum(1 for kw in template["keywords"] if kw in text)
            if score > 0:
                scores[template_id] = score
        
        if scores:
            return max(scores, key=scores.get)
        return "generic"
    
    def generate_manual(self,
                       task_id: str,
                       title: str,
                       description: str,
                       estimated_cost: float = 0) -> Dict:
        """
        生成任务手册
        
        Returns:
            {
                "template": "code_review",
                "manual_path": "data/manuals/task_xxx.md",
                "content": "手册内容..."
            }
        """
        # 1. 检测模板
        template_id = self.detect_template(title, description)
        template = self.TEMPLATES[template_id]
        
        logger.info(f"Generating manual for task {task_id} using template: {template_id}")
        
        # 2. 构建手册内容
        sections = []
        
        # 头部信息
        sections.extend([
            f"# {template['name']}手册",
            "",
            f"> 任务: {title}",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> 预估预算: {estimated_cost} tokens",
            "",
            "---",
            "",
        ])
        
        # 任务描述
        sections.extend([
            "## 任务描述",
            description or "（暂无详细描述）",
            "",
            "---",
            "",
        ])
        
        # 模板特定内容
        for section in template["sections"]:
            # 简单变量替换
            section = section.replace("{target}", title)
            section = section.replace("{focus}", "代码质量和潜在问题")
            section = section.replace("{audience}", "技术人员")
            section = section.replace("{style}", "专业、清晰")
            section = section.replace("{length}", "根据内容自然展开")
            section = section.replace("{source}", "待指定")
            section = section.replace("{time_range}", "待指定")
            sections.append(section)
        
        # 通用执行指南
        sections.extend([
            "",
            "---",
            "",
            "## 执行指南",
            "",
            "### 开始执行前",
            "1. 仔细阅读任务描述",
            "2. 确认预算充足",
            "3. 如有疑问，先询问澄清",
            "",
            "### 执行过程中",
            "1. 按步骤逐项完成",
            "2. 记录关键决策",
            "3. 遇到困难及时反馈",
            "",
            "### 完成交付",
            "1. 自查完成度",
            "2. 确保输出符合格式要求",
            "3. 调用 opc_report_task_result() 报告结果",
            "",
            "---",
            "",
            "## 约束条件",
            "",
            f"- 预算上限: {estimated_cost} tokens",
            "- 如预算不足，先报告再申请",
            "- 超时任务会自动提醒",
            "",
        ])
        
        content = "\n".join(sections)
        
        # 3. 保存文件
        manual_filename = f"{task_id}.md"
        manual_path = os.path.join(self.manuals_dir, manual_filename)
        
        with open(manual_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Manual saved to: {manual_path}")
        
        return {
            "template": template_id,
            "template_name": template["name"],
            "manual_path": manual_path,
            "relative_path": f"data/manuals/{manual_filename}",
            "content": content,
            "size": len(content)
        }
    
    def get_manual(self, task_id: str) -> Optional[Dict]:
        """获取已生成的手册"""
        manual_path = os.path.join(self.manuals_dir, f"{task_id}.md")
        
        if not os.path.exists(manual_path):
            return None
        
        with open(manual_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "task_id": task_id,
            "path": manual_path,
            "relative_path": f"data/manuals/{task_id}.md",
            "content": content,
            "size": len(content)
        }
    
    def regenerate_manual(self,
                         task_id: str,
                         title: str,
                         description: str,
                         estimated_cost: float = 0,
                         template: Optional[str] = None) -> Dict:
        """重新生成手册（可指定模板）"""
        if template and template in self.TEMPLATES:
            # 强制使用指定模板
            original_detect = self.detect_template
            self.detect_template = lambda t, d: template
            result = self.generate_manual(task_id, title, description, estimated_cost)
            self.detect_template = original_detect
            return result
        
        return self.generate_manual(task_id, title, description, estimated_cost)


# 全局实例
manual_generator = ManualGenerator()


# 便捷函数
def generate_task_manual(task_id: str,
                        title: str,
                        description: str,
                        estimated_cost: float = 0) -> Dict:
    """生成任务手册"""
    return manual_generator.generate_manual(task_id, title, description, estimated_cost)


def get_task_manual(task_id: str) -> Optional[Dict]:
    """获取任务手册"""
    return manual_generator.get_manual(task_id)