# 员工头像系统重构方案

## 现状分析

### 当前 v3 实现 (问题版本)

| 维度 | 现状 |
|------|------|
| **数据模型** | `Employee.emoji` 字段，存储字符串如 `"🤖"` |
| **前端显示** | 直接渲染 `<span>{{ emp.emoji || '👤' }}</span>` |
| **问题** | 依赖系统字体，在缺少 emoji 字体的环境显示为空白方块 |

### v2 实现 (参考版本)

| 维度 | 实现 |
|------|------|
| **数据模型** | 独立 `employee_avatars` 表，支持三种来源 |
| **System** | SVG 像素艺术，8x8 网格，按职位着色 |
| **Uploaded** | 用户上传 PNG/JPG/SVG，5MB 限制 |
| **AI** | 通过 vivago-ai skill 生成 |
| **存储** | 本地文件系统 `/avatars` 目录 |

---

## 方案选型

我提供三个可选方案，按实现复杂度从低到高排列：

---

## 方案一：Emoji → SVG 图标映射 (推荐短期方案)

### 核心思路
保留现有 emoji 字段，但在前端映射为 SVG 图标显示。fallback 到 emoji。

### 实现细节

```javascript
// 职位 → SVG 图标映射
const POSITION_ICONS = {
  1: { icon: 'intern', color: '#87CEEB' },      // 实习生 - 浅蓝
  2: { icon: 'specialist', color: '#32CD32' }, // 专员 - 绿
  3: { icon: 'senior', color: '#4169E1' },     // 资深 - 蓝
  4: { icon: 'expert', color: '#FF69B4' },     // 专家 - 粉
  5: { icon: 'partner', color: '#DC143C' },    // 合伙人 - 红
}

// 或使用 emoji → icon 映射
const EMOJI_ICONS = {
  '🤖': { icon: 'robot', color: '#667eea' },
  '👤': { icon: 'person', color: '#764ba2' },
  '🦾': { icon: 'cyborg', color: '#f093fb' },
  // ...
}
```

### 技术实现

**选项 A：内联 SVG (推荐)**
```vue
<!-- EmployeeAvatar.vue -->
<template>
  <svg v-if="iconData" width="40" height="40" viewBox="0 0 40 40">
    <!-- 根据 iconData.icon 渲染不同 SVG 路径 -->
    <g v-if="iconData.icon === 'robot'">
      <rect x="10" y="5" width="20" height="15" :fill="iconData.color"/>
      <circle cx="15" cy="12" r="2" fill="white"/>
      <circle cx="25" cy="12" r="2" fill="white"/>
    </g>
    <g v-else-if="iconData.icon === 'person'">
      <!-- 人形图标 -->
    </g>
  </svg>
  <span v-else>{{ emoji }}</span>
</template>
```

**选项 B：图标字体 (如 Phosphor, Heroicons)**
```vue
<i :class="`ph ph-${iconName}`" :style="{ color: iconColor }"></i>
```

### 数据迁移
- 无需迁移，零成本
- 可选：将 emoji 映射到职位级别

### 优缺点
| 优点 | 缺点 |
|------|------|
| 实现简单，1-2 天完成 | 可定制性有限 |
| 无需后端改动 | 无法用户上传 |
| 不依赖系统字体 | 无法 AI 生成 |
| 文件体积小 | 风格统一但单一 |

---

## 方案二：复刻 v2 三模式系统 (推荐长期方案)

### 核心思路
完整实现 v2 的三模式头像系统：System + Upload + AI

### 数据模型

```python
# 新增 employee_avatars 表
class EmployeeAvatar(Base):
    __tablename__ = "employee_avatars"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String, ForeignKey("employees.id"), unique=True)
    
    # 来源类型: system | upload | ai
    source: Mapped[str] = mapped_column(String, default="system")
    
    # 存储路径或外部 URL
    storage_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # 系统生成参数 (JSON)
    style_params: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # AI 生成参数
    generation_prompt: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    skill_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # 上传文件原始名
    original_filename: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 文件存储结构
```
data/
├── opc.db
└── avatars/           # 新增头像存储目录
    ├── default.svg    # 默认头像
    ├── emp_001_system.svg
    ├── emp_002_upload.png
    └── emp_003_ai.jpg
```

### 后端 API

```python
# routers/avatars.py

@router.get("/employees/{employee_id}/avatar")
async def get_avatar(employee_id: str): ...

@router.post("/employees/{employee_id}/avatar/generate")
async def generate_system_avatar(
    employee_id: str,
    style: str = "humanoid"  # humanoid | robot | alien | spirit
): ...

@router.post("/employees/{employee_id}/avatar/upload")
async def upload_avatar(
    employee_id: str,
    file: UploadFile = File(...)
    # 限制: PNG/JPG/SVG, max 5MB
): ...

@router.post("/employees/{employee_id}/avatar/ai")
async def request_ai_avatar(
    employee_id: str,
    prompt: str,
    skill_name: str = "vivago-ai"
): ...

@router.delete("/employees/{employee_id}/avatar")
async def delete_avatar(employee_id: str): ...
```

### 前端组件

```vue
<!-- EmployeeAvatar.vue -->
<template>
  <div class="employee-avatar" :class="size">
    <!-- System / Upload: 本地文件 -->
    <img 
      v-if="avatar?.source !== 'ai' && avatarUrl" 
      :src="avatarUrl" 
      :alt="employee.name"
      @error="onImageError"
    />
    
    <!-- AI: 外部 URL -->
    <img 
      v-else-if="avatar?.source === 'ai' && avatar.external_url" 
      :src="avatar.external_url" 
      :alt="employee.name"
    />
    
    <!-- Fallback: emoji -->
    <span v-else class="emoji-fallback">{{ employee.emoji || '👤' }}</span>
  </div>
</template>
```

### 头像选择器组件

```vue
<!-- AvatarSelector.vue -->
<template>
  <el-dialog title="选择头像">
    <el-tabs>
      <el-tab-pane label="系统生成">
        <div class="pixel-styles">
          <div 
            v-for="style in pixelStyles" 
            :key="style"
            class="style-preview"
            @click="generateSystem(style)"
          >
            <!-- 预览 SVG -->
          </div>
        </div>
        <el-button @click="regenerateRandom">🎲 随机生成</el-button>
      </el-tab-pane>
      
      <el-tab-pane label="上传图片">
        <el-upload
          accept=".png,.jpg,.jpeg,.svg"
          :before-upload="validateFile"
          :http-request="uploadAvatar"
        >
          <el-button>选择文件</el-button>
          <template #tip>支持 PNG/JPG/SVG，最大 5MB</template>
        </el-upload>
      </el-tab-pane>
      
      <el-tab-pane label="AI 生成" v-if="hasVivagoSkill">
        <el-input 
          v-model="aiPrompt" 
          type="textarea" 
          placeholder="描述你想要的头像..."
        />
        <el-button @click="requestAIAvatar">生成头像</el-button>
        <p class="hint">需要配置 vivago-ai skill</p>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>
```

### 系统生成 SVG 像素艺术

复用 v2 的 `AvatarService` 实现：

```python
class AvatarService:
    PIXEL_TEMPLATES = {
        "humanoid": [...],  # 8x8 字符网格
        "robot": [...],
        "alien": [...],
        "spirit": [...],
    }
    
    COLOR_PALETTES = {
        PositionLevel.INTERN.value: ["#87CEEB", "#ADD8E6"],
        PositionLevel.SPECIALIST.value: ["#32CD32", "#00FF00"],
        PositionLevel.SENIOR.value: ["#4169E1", "#00BFFF"],
        PositionLevel.EXPERT.value: ["#FF69B4", "#DA70D6"],
        PositionLevel.PARTNER.value: ["#DC143C", "#B22222"],
    }
    
    def generate_system_avatar(self, employee_id: str, style: str, position: int):
        template = self.PIXEL_TEMPLATES[style]
        colors = self.COLOR_PALETTES.get(position, self.COLOR_PALETTES[5])
        svg = self._render_svg(template, colors)  # 80x80 SVG
        # 保存到 data/avatars/{employee_id}_{style}_{timestamp}.svg
```

### 迁移脚本

```python
# migrations/migrate_emoji_to_avatar.py
"""
将现有 emoji 映射到 system avatar
"""

def migrate():
    employees = db.query(Employee).all()
    
    for emp in employees:
        # 根据职位级别选择默认风格
        style = POSITION_TO_STYLE.get(emp.position_level, "humanoid")
        
        # 生成系统头像
        avatar_service.generate_system_avatar(
            employee_id=emp.id,
            style=style,
            position=emp.position_level
        )
```

### 工作量估算

| 模块 | 工作量 |
|------|--------|
| 数据库模型 + 迁移 | 半天 |
| AvatarService 后端 | 1-2 天 |
| API 路由 | 半天 |
| 前端 Avatar 组件 | 半天 |
| 头像选择器 UI | 1 天 |
| 文件上传/存储 | 半天 |
| 测试 | 半天 |
| **总计** | **4-5 天** |

### 优缺点
| 优点 | 缺点 |
|------|------|
| 完整功能，可扩展 | 实现周期长 |
| 用户可上传/AI生成 | 需要文件存储 |
| 不依赖系统字体 | 数据迁移成本 |
| 与 v2 架构一致 | 需要维护头像目录 |

---

## 方案三：混合方案 (Emoji + Gravatar + 可选上传)

### 核心思路
简化版的三模式：保留 emoji 作为 fallback，优先使用 Gravatar，可选上传

### 实现

```python
# Employee 模型扩展
class Employee(Base):
    # ... 现有字段 ...
    
    # 新增
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    avatar_source: Mapped[str] = mapped_column(String, default="emoji")  # emoji | gravatar | upload
    
    def get_avatar_url(self, size: int = 80) -> str:
        if self.avatar_source == "upload" and self.avatar_url:
            return self.avatar_url
        
        if self.avatar_source == "gravatar":
            import hashlib
            email_hash = hashlib.md5(self.email.lower().encode()).hexdigest()
            return f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d=identicon"
        
        # fallback: emoji
        return None  # 前端显示 emoji
```

### 优缺点
| 优点 | 缺点 |
|------|------|
| 简单快速 | 依赖外部服务 (Gravatar) |
| 无需存储文件 | 用户需注册 Gravatar |
| 自动头像 | 定制性有限 |

---

## 我的建议

### 短期 (本周内)：方案一
- 快速解决 emoji 显示问题
- 实现成本最低
- 风险最小

### 长期 (下个迭代)：方案二
- 完整功能满足用户需求
- 与 v2 架构保持一致
- 可扩展性强

### 需要确认的问题

1. **优先级**: 是否急需修复 emoji 显示？还是可以等待完整方案？

2. **用户上传**: 是否有真实需求让用户上传自定义头像？

3. **AI 生成**: 是否已配置 vivago-ai skill？是否需要 AI 头像功能？

4. **存储位置**: 头像文件存储在 `data/avatars/` 还是其他位置？

5. **默认风格**: 系统生成的像素头像，是否复用 v2 的模板，还是设计新的？

---

## 下一步

请告诉我你的选择：
- **A**: 先实现方案一 (快速修复)
- **B**: 直接实现方案二 (完整功能)
- **C**: 方案三 (Gravatar)
- **D**: 其他想法

以及上述需要确认的问题答案。
