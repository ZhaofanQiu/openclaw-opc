"""
Employee Manual Service

员工手册管理
"""

import os
from typing import Dict, Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)


# 默认员工手册模板
DEFAULT_EMPLOYEE_MANUAL_TEMPLATE = """# 员工手册：{employee_name}

## 基本信息

- **姓名**：{employee_name}
- **职位级别**：Level {position_level}
- **入职时间**：{join_date}

## 工作风格

### 沟通偏好
- 喜欢清晰、直接的沟通
- 有疑问会主动询问
- 重要决策需要确认

### 工作习惯
- 注重代码/文档质量
- 习惯先规划再执行
- 及时同步工作进展

### 技能特长
- （待补充：根据工作积累自动更新）

## 经验积累

### 擅长领域
- （待补充：根据完成的任务自动总结）

### 待提升领域
- （待补充：根据反馈自动识别）

## 用户要求

（这里记录用户对该员工提出的具体要求和期望）

---

*本手册由 Partner 在员工入职时创建*
*员工会根据工作反馈自动更新此手册*
*用户可以通过与员工聊天来修改此手册*
*最后更新：{update_time}*
"""


class EmployeeManualService:
    """员工手册服务"""
    
    def __init__(self):
        self.manuals_dir = os.path.join(os.getcwd(), "data", "manuals", "employees")
        os.makedirs(self.manuals_dir, exist_ok=True)
    
    def create_manual(self,
                     employee_id: str,
                     employee_name: str,
                     position_level: int,
                     employee_description: str = "") -> Dict:
        """
        创建员工手册（员工入职时由 Partner 调用）
        
        Args:
            employee_description: Partner 对员工的初始描述
        """
        from datetime import datetime
        
        manual_path = os.path.join(self.manuals_dir, f"{employee_id}.md")
        
        # 构建初始内容
        sections = [
            f"# 员工手册：{employee_name}",
            "",
            "## 基本信息",
            "",
            f"- **姓名**：{employee_name}",
            f"- **职位级别**：Level {position_level}",
            f"- **入职时间**：{datetime.now().strftime('%Y-%m-%d')}",
            "",
        ]
        
        if employee_description:
            sections.extend([
                "## Partner 初始描述",
                "",
                employee_description,
                "",
            ])
        
        sections.extend([
            "## 工作风格",
            "",
            "### 沟通偏好",
            "- 喜欢清晰、直接的沟通",
            "- 有疑问会主动询问",
            "- 重要决策需要确认",
            "",
            "### 工作习惯",
            "- 注重代码/文档质量",
            "- 习惯先规划再执行",
            "- 及时同步工作进展",
            "",
            "### 技能特长",
            "- （待补充：根据工作积累自动更新）",
            "",
            "## 经验积累",
            "",
            "### 擅长领域",
            "- （待补充：根据完成的任务自动总结）",
            "",
            "### 待提升领域",
            "- （待补充：根据反馈自动识别）",
            "",
            "## 用户要求",
            "",
            "（这里记录用户对该员工提出的具体要求和期望）",
            "",
            "---",
            "",
            "*本手册由 Partner 在员工入职时创建*",
            "*员工会根据工作反馈自动更新此手册*",
            "*用户可以通过与员工聊天来修改此手册*",
            f"*最后更新：{datetime.now().strftime('%Y-%m-%d')}*",
        ])
        
        content = "\n".join(sections)
        
        with open(manual_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Employee manual created: {manual_path}")
        
        return {
            "employee_id": employee_id,
            "path": manual_path,
            "relative_path": f"data/manuals/employees/{employee_id}.md",
            "content": content,
            "size": len(content)
        }
    
    def get_manual(self, employee_id: str) -> Optional[Dict]:
        """获取员工手册"""
        manual_path = os.path.join(self.manuals_dir, f"{employee_id}.md")
        
        if not os.path.exists(manual_path):
            return None
        
        with open(manual_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "employee_id": employee_id,
            "path": manual_path,
            "relative_path": f"data/manuals/employees/{employee_id}.md",
            "content": content,
            "size": len(content)
        }
    
    def update_manual(self, employee_id: str, content: str) -> Dict:
        """更新员工手册（用户通过聊天修改）"""
        from datetime import datetime
        
        manual_path = os.path.join(self.manuals_dir, f"{employee_id}.md")
        
        # 更新最后更新时间
        if "*最后更新：" in content:
            # 替换现有时间戳
            content = content.rsplit("*最后更新：", 1)[0].rstrip()
            content = content + f"\n*最后更新：{datetime.now().strftime('%Y-%m-%d')}*"
        else:
            # 添加时间戳
            content = content.rstrip() + f"\n\n*最后更新：{datetime.now().strftime('%Y-%m-%d')}*"
        
        with open(manual_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Employee manual updated: {manual_path}")
        
        return {
            "employee_id": employee_id,
            "path": manual_path,
            "content": content,
            "size": len(content)
        }
    
    def auto_update_from_feedback(self,
                                  employee_id: str,
                                  feedback: str,
                                  task_type: str = "") -> bool:
        """
        根据任务反馈自动更新员工手册
        
        员工收到反馈后，分析反馈内容并更新手册中的：
        - 擅长领域（正面反馈）
        - 待提升领域（改进建议）
        - 工作风格调整
        
        Args:
            feedback: 反馈内容
            task_type: 任务类型（用于分类经验）
        """
        manual = self.get_manual(employee_id)
        if not manual:
            logger.warning(f"Employee manual not found: {employee_id}")
            return False
        
        content = manual["content"]
        
        # TODO: 实现更智能的 NLP 分析
        # 目前使用简单的关键词匹配
        
        # 检测正面反馈（添加到擅长领域）
        positive_keywords = ["做得好", "优秀", "出色", "完美", "高质量", "专业"]
        if any(kw in feedback for kw in positive_keywords):
            # 在擅长领域添加经验
            skill_entry = f"- {task_type or '任务'}：获得正面评价（{feedback[:30]}...）"
            
            if "### 擅长领域" in content:
                # 在擅长领域后添加（如果还不存在）
                if skill_entry not in content:
                    content = content.replace(
                        "### 擅长领域\n- （待补充：根据完成的任务自动总结）",
                        f"### 擅长领域\n{skill_entry}"
                    )
        
        # 检测改进建议（添加到待提升领域）
        improvement_keywords = ["建议", "改进", "不足", "需要", "应该"]
        if any(kw in feedback for kw in improvement_keywords):
            # 在待提升领域添加
            improve_entry = f"- {task_type or '任务'}：{feedback[:50]}..."
            
            if "### 待提升领域" in content:
                if improve_entry not in content:
                    content = content.replace(
                        "### 待提升领域\n- （待补充：根据反馈自动识别）",
                        f"### 待提升领域\n{improve_entry}"
                    )
        
        # 保存更新
        self.update_manual(employee_id, content)
        
        logger.info(f"Employee manual auto-updated from feedback: {employee_id}")
        return True
    
    def add_user_requirement(self,
                            employee_id: str,
                            requirement: str) -> bool:
        """
        添加用户要求（用户与员工聊天时提出）
        
        将用户要求记录到员工手册的"用户要求"部分
        """
        manual = self.get_manual(employee_id)
        if not manual:
            return False
        
        content = manual["content"]
        
        from datetime import datetime
        requirement_entry = f"\n- [{datetime.now().strftime('%Y-%m-%d')}] {requirement}"
        
        # 在"用户要求"部分添加
        if "## 用户要求" in content:
            # 找到用户要求部分并在其后添加
            lines = content.split('\n')
            user_req_idx = None
            for i, line in enumerate(lines):
                if line.startswith("## 用户要求"):
                    user_req_idx = i
                    break
            
            if user_req_idx is not None:
                # 找到该部分的结束位置（下一个 ## 或文件结束）
                insert_idx = len(lines)
                for i in range(user_req_idx + 1, len(lines)):
                    if lines[i].startswith("## "):
                        insert_idx = i
                        break
                
                # 插入要求
                if "（这里记录用户对该员工提出的具体要求和期望）" in content:
                    # 替换占位符
                    content = content.replace(
                        "（这里记录用户对该员工提出的具体要求和期望）",
                        requirement_entry.strip()
                    )
                else:
                    # 添加新要求
                    lines.insert(insert_idx, requirement_entry)
                    content = '\n'.join(lines)
        
        self.update_manual(employee_id, content)
        
        logger.info(f"User requirement added to employee manual: {employee_id}")
        return True


# 全局实例
employee_manual_service = EmployeeManualService()


# 便捷函数
def create_employee_manual(employee_id: str,
                          employee_name: str,
                          position_level: int,
                          description: str = "") -> Dict:
    """创建员工手册"""
    return employee_manual_service.create_manual(
        employee_id, employee_name, position_level, description
    )


def get_employee_manual(employee_id: str) -> Optional[Dict]:
    """获取员工手册"""
    return employee_manual_service.get_manual(employee_id)


def update_employee_manual(employee_id: str, content: str) -> Dict:
    """更新员工手册"""
    return employee_manual_service.update_manual(employee_id, content)


def add_user_requirement_to_employee(employee_id: str, requirement: str) -> bool:
    """添加用户要求"""
    return employee_manual_service.add_user_requirement(employee_id, requirement)