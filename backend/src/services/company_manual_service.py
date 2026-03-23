"""
Company Manual Service

公司手册管理
"""

import os
from typing import Dict, Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)


# 默认公司手册模板
DEFAULT_COMPANY_MANUAL = """# 公司手册

## 公司愿景

（待填写：描述公司的长期目标和愿景）

## 工作风格

### 沟通规范
- 清晰、简洁、及时
- 有疑问先询问，避免假设
- 重要决策需要确认

### 质量标准
- 代码/文档需要自查
- 关键逻辑需要测试验证
- 交付前确认完成度

### 协作原则
- 尊重他人时间
- 主动同步进展
- 遇到问题及时上报

## 文化价值观

1. **务实** - 解决实际问题，避免过度设计
2. **高效** - 合理分配资源，追求效率
3. **成长** - 持续学习，积累经验

## 通用规范

### 代码规范
- 遵循项目既定代码风格
- 关键函数添加注释
- 复杂逻辑需要说明

### 文档规范
- 结构化呈现
- 关键结论突出
- 可追溯、可验证

---

*本手册由公司管理层制定，所有员工需遵循*
*最后更新：{update_time}*
"""


class CompanyManualService:
    """公司手册服务"""
    
    def __init__(self):
        self.manuals_dir = os.path.join(os.getcwd(), "data", "manuals")
        self.manual_path = os.path.join(self.manuals_dir, "company.md")
        os.makedirs(self.manuals_dir, exist_ok=True)
    
    def initialize_default(self) -> str:
        """初始化默认公司手册"""
        if os.path.exists(self.manual_path):
            logger.info("Company manual already exists")
            return self.manual_path
        
        from datetime import datetime
        content = DEFAULT_COMPANY_MANUAL.format(
            update_time=datetime.now().strftime('%Y-%m-%d')
        )
        
        with open(self.manual_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Default company manual created: {self.manual_path}")
        return self.manual_path
    
    def get_manual(self) -> Optional[Dict]:
        """获取公司手册"""
        if not os.path.exists(self.manual_path):
            # 自动初始化
            self.initialize_default()
        
        with open(self.manual_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "type": "company",
            "path": self.manual_path,
            "relative_path": "data/manuals/company.md",
            "content": content,
            "size": len(content)
        }
    
    def update_manual(self, content: str) -> Dict:
        """更新公司手册（用户修改）"""
        from datetime import datetime
        
        # 添加更新标记
        if "---" in content:
            # 替换最后更新时间
            content = content.rsplit("*最后更新：", 1)[0]
            content = content.rstrip() + f"\n\n---\n\n*最后更新：{datetime.now().strftime('%Y-%m-%d')}*"
        
        with open(self.manual_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("Company manual updated")
        
        return {
            "type": "company",
            "path": self.manual_path,
            "content": content,
            "size": len(content)
        }
    
    def append_from_feedback(self, feedback: str) -> bool:
        """
        根据任务反馈自动补充公司手册（可选功能）
        
        检测反馈中的全局要求，自动添加到公司手册
        """
        # TODO: 实现 NLP 检测全局要求
        # 目前仅记录，不自动修改
        logger.info(f"Feedback received for potential company manual update: {feedback[:100]}...")
        return False


# 全局实例
company_manual_service = CompanyManualService()


# 便捷函数
def get_company_manual() -> Optional[Dict]:
    """获取公司手册"""
    return company_manual_service.get_manual()


def update_company_manual(content: str) -> Dict:
    """更新公司手册"""
    return company_manual_service.update_manual(content)


def initialize_company_manual() -> str:
    """初始化公司手册"""
    return company_manual_service.initialize_default()