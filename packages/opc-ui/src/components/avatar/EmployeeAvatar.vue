<template>
  <div class="employee-avatar" :class="[size, { interactive }]" :style="containerStyle">
    <svg 
      :width="svgSize" 
      :height="svgSize" 
      :viewBox="`0 0 ${viewBoxSize} ${viewBoxSize}`"
      xmlns="http://www.w3.org/2000/svg"
      class="avatar-svg"
    >
      <!-- 背景 -->
      <rect 
        :width="viewBoxSize" 
        :height="viewBoxSize" 
        :fill="bgColor"
        rx="4"
        ry="4"
      />
      
      <!-- 根据不同类型渲染不同头像 -->
      <g :transform="`translate(${padding}, ${padding})`">
        <!-- 实习生/专员: 基础人形 -->
        <g v-if="avatarType === 'basic'">
          <!-- 身体 -->
          <rect x="20" y="50" width="40" height="35" :fill="colors.body" rx="3"/>
          <!-- 头部 -->
          <circle cx="40" cy="30" r="18" :fill="colors.skin"/>
          
          <!-- 头发 -->
          <path 
            v-if="gender === 'female'"
            d="M22 25 Q40 10 58 25 L58 35 Q40 25 22 35 Z" 
            :fill="colors.hair"
          />
          <path 
            v-else
            d="M22 28 Q40 8 58 28 L55 22 Q40 5 25 22 Z" 
            :fill="colors.hair"
          />
          
          <!-- 眼睛 -->
          <circle cx="33" cy="32" r="3" fill="#333"/>
          <circle cx="47" cy="32" r="3" fill="#333"/>
          
          <!-- 嘴巴 -->
          <path d="M35 40 Q40 43 45 40" stroke="#333" stroke-width="1.5" fill="none"/>
          
          <!-- 职业道具 -->
          <g v-if="hasProp">
            <!-- 研究员: 试管 -->
            <g v-if="positionTitle.includes('研究')">
              <rect x="8" y="45" width="6" height="20" fill="#87CEEB" stroke="#4169E1" stroke-width="1"/>
              <rect x="8" y="55" width="6" height="8" fill="#32CD32" opacity="0.6"/>
            </g>
            
            <!-- 分析师: 图表 -->
            <g v-else-if="positionTitle.includes('分析')">
              <rect x="10" y="55" width="4" height="10" fill="#FF6B6B"/>
              <rect x="16" y="50" width="4" height="15" fill="#4ECDC4"/>
              <rect x="22" y="58" width="4" height="7" fill="#45B7D1"/>
            </g>
            
            <!-- 审查员: 放大镜 -->
            <g v-else-if="positionTitle.includes('审查')">
              <circle cx="12" cy="52" r="8" stroke="#FFD93D" stroke-width="3" fill="none"/>
              <line x1="17" y1="57" x2="22" y2="62" stroke="#FFD93D" stroke-width="3" stroke-linecap="round"/>
            </g>
          </g>
          
          <!-- 级别徽章 -->
          <g v-if="level >= 4">
            <polygon 
              points="70,5 73,12 80,12 75,17 77,24 70,20 63,24 65,17 60,12 67,12" 
              :fill="levelStarColor"
            />
          </g>
        </g>
        
        <!-- 资深/专家: 更专业的形象 -->
        <g v-else-if="avatarType === 'advanced'">
          <!-- 身体 -->
          <rect x="18" y="48" width="44" height="38" :fill="colors.body" rx="4"/>
          
          <!-- 领带/领结 -->
          <g v-if="gender === 'male'">
            <polygon points="40,48 36,62 40,66 44,62" fill="#DC143C"/>
            <rect x="38" y="48" width="4" height="10" fill="#8B0000"/>
          </g>
          <g v-else>
            <ellipse cx="40" cy="52" rx="6" ry="4" fill="#FF69B4"/>
            <rect x="38" y="50" width="4" height="3" fill="#C71585"/>
          </g>
          
          <!-- 头部 -->
          <circle cx="40" cy="28" r="20" :fill="colors.skin"/>
          
          <!-- 头发 (更复杂) -->
          <path 
            v-if="gender === 'female'"
            d="M20 25 Q40 5 60 25 L62 45 Q40 35 18 45 Z" 
            :fill="colors.hair"
          />
          <path 
            v-else
            d="M20 30 Q40 2 60 30 L58 18 Q40 -5 22 18 Z" 
            :fill="colors.hair"
          />
          
          <!-- 眼镜 (专家特有) -->
          <g v-if="level >= 4">
            <rect x="26" y="26" width="10" height="8" rx="2" fill="none" stroke="#333" stroke-width="1.5"/>
            <rect x="44" y="26" width="10" height="8" rx="2" fill="none" stroke="#333" stroke-width="1.5"/>
            <line x1="36" y1="30" x2="44" y2="30" stroke="#333" stroke-width="1.5"/>
          </g>
          
          <!-- 眼睛 -->
          <circle cx="31" cy="32" r="3" fill="#333"/>
          <circle cx="49" cy="32" r="3" fill="#333"/>
          
          <!-- 嘴巴 -->
          <path d="M35 40 Q40 44 45 40" stroke="#333" stroke-width="2" fill="none"/>
          
          <!-- 专业道具 -->
          <g v-if="hasProp">
            <!-- 笔记本电脑 -->
            <rect x="55" y="55" width="20" height="14" fill="#4A5568" rx="2"/>
            <rect x="57" y="57" width="16" height="10" fill="#68D391" rx="1"/>
            <line x1="59" y1="60" x2="71" y2="60" stroke="#333" stroke-width="0.5"/>
            <line x1="59" y1="63" x2="71" y2="63" stroke="#333" stroke-width="0.5"/>
          </g>
          
          <!-- 级别徽章 -->
          <g v-if="level >= 4">
            <circle cx="68" cy="12" r="8" :fill="levelStarColor"/>
            <text x="68" y="16" text-anchor="middle" fill="white" font-size="10" font-weight="bold">E</text>
          </g>
          <g v-else-if="level === 3">
            <circle cx="68" cy="12" r="6" fill="#C0C0C0"/>
            <text x="68" y="15" text-anchor="middle" fill="white" font-size="8" font-weight="bold">S</text>
          </g>
        </g>
        
        <!-- 合伙人: 特殊形象 -->
        <g v-else-if="avatarType === 'partner'">
          <!-- 光环 -->
          <ellipse cx="40" cy="10" rx="25" ry="6" fill="#FFD700" opacity="0.5"/>
          
          <!-- 身体 -->
          <rect x="15" y="48" width="50" height="40" :fill="colors.body" rx="5"/>
          
          <!-- 皇冠 -->
          <polygon points="40,10 35,20 25,18 30,28 40,32 50,28 55,18 45,20" fill="#FFD700" stroke="#FFA500" stroke-width="1"/>
          <circle cx="40" cy="22" r="3" fill="#FF6347"/>
          
          <!-- 披风 -->
          <path d="M15 55 L5 88 L75 88 L65 55 Z" :fill="colors.cape || '#DC143C'" opacity="0.8"/>
          
          <!-- 头部 -->
          <circle cx="40" cy="32" r="22" :fill="colors.skin"/>
          
          <!-- 头发 -->
          <path 
            d="M18 30 Q40 0 62 30 L65 40 Q40 25 15 40 Z" 
            :fill="colors.hair"
          />
          
          <!-- 眼睛 -->
          <circle cx="32" cy="35" r="3.5" fill="#333"/>
          <circle cx="48" cy="35" r="3.5" fill="#333"/>
          
          <!-- 微笑 -->
          <path d="M33 44 Q40 50 47 44" stroke="#333" stroke-width="2.5" fill="none"/>
          
          <!-- Partner 徽章 -->
          <rect x="62" y="5" width="20" height="12" fill="#FFD700" rx="2"/>
          <text x="72" y="14" text-anchor="middle" fill="#8B0000" font-size="8" font-weight="bold">P</text>
        </g>
      </g>
    </svg>
    
    <!-- Fallback emoji -->
    <span v-if="showFallback" class="emoji-fallback">{{ emoji }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  employee: {
    type: Object,
    required: true
  },
  size: {
    type: String,
    default: 'medium', // small, medium, large
  },
  interactive: {
    type: Boolean,
    default: false
  },
  showFallback: {
    type: Boolean,
    default: false
  }
})

// 尺寸配置
const sizeConfig = {
  small: { svg: 40, viewBox: 80, padding: 4 },
  medium: { svg: 64, viewBox: 80, padding: 4 },
  large: { svg: 96, viewBox: 80, padding: 4 },
}

const config = computed(() => sizeConfig[props.size] || sizeConfig.medium)
const svgSize = computed(() => config.value.svg)
const viewBoxSize = computed(() => config.value.viewBox)
const padding = computed(() => config.value.padding)

const containerStyle = computed(() => ({
  width: `${svgSize.value}px`,
  height: `${svgSize.value}px`,
}))

// 员工属性
const level = computed(() => props.employee.position_level || 1)
const positionTitle = computed(() => props.employee.position_title || '')
const emoji = computed(() => props.employee.emoji || '👤')
const gender = computed(() => {
  // 从姓名推断性别，或随机
  const name = props.employee.name || ''
  if (name.includes('Alice') || name.includes('Carol')) return 'female'
  if (name.includes('Bob') || name.includes('Dave')) return 'male'
  // 默认根据 ID 哈希
  return props.employee.id?.charCodeAt(0) % 2 === 0 ? 'female' : 'male'
})

// 头像类型
const avatarType = computed(() => {
  if (level.value >= 5) return 'partner'
  if (level.value >= 3) return 'advanced'
  return 'basic'
})

// 是否显示职业道具
const hasProp = computed(() => level.value <= 2)

// 配色方案
const colorSchemes = {
  // 实习生 - 浅色系
  intern: {
    hair: ['#8B4513', '#D2691E', '#A0522D', '#CD853F'],
    body: ['#E6F3FF', '#FFF0E6', '#F0E6FF', '#E6FFE6'],
    skin: ['#FFDBAC', '#F1C27D', '#E0AC69', '#8D5524'],
    bg: ['#F0F8FF', '#FFF5EE', '#F5F5DC', '#F0FFF0'],
  },
  // 专员 - 中性色
  specialist: {
    hair: ['#2F4F4F', '#556B2F', '#8B4513', '#4A4A4A'],
    body: ['#4169E1', '#2E8B57', '#6A5ACD', '#708090'],
    skin: ['#FFDBAC', '#F1C27D', '#E0AC69', '#8D5524'],
    bg: ['#F5F5F5', '#E8E8E8', '#F0F0F0', '#E5E5E5'],
  },
  // 资深 - 深色系
  senior: {
    hair: ['#000000', '#1C1C1C', '#2F4F4F', '#4A4A4A'],
    body: ['#191970', '#006400', '#8B008B', '#483D8B'],
    skin: ['#FFDBAC', '#F1C27D', '#E0AC69', '#8D5524'],
    bg: ['#E6E6FA', '#E0EEE0', '#FFF0F5', '#F0F8FF'],
  },
  // 专家 - 金色/特殊色
  expert: {
    hair: ['#2F1810', '#4A3728', '#556B2F', '#8B4513'],
    body: ['#4B0082', '#8B4513', '#2F4F4F', '#800080'],
    skin: ['#FFDBAC', '#F1C27D', '#E0AC69', '#8D5524'],
    bg: ['#FFF8DC', '#F5F5DC', '#FAEBD7', '#FFE4E1'],
  },
  // 合伙人 - 红金配色
  partner: {
    hair: ['#FFD700', '#DAA520', '#B8860B', '#8B6914'],
    body: ['#8B0000', '#DC143C', '#B22222', '#CD5C5C'],
    skin: ['#FFDBAC', '#F1C27D', '#E0AC69', '#8D5524'],
    bg: ['#FFF8DC', '#FFFACD', '#FAFAD2', '#FFEFD5'],
    cape: '#DC143C',
  },
}

// 根据 ID 和级别选择颜色
const colors = computed(() => {
  const id = props.employee.id || '0'
  const hash = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  
  let scheme
  if (level.value === 5) scheme = colorSchemes.partner
  else if (level.value === 4) scheme = colorSchemes.expert
  else if (level.value === 3) scheme = colorSchemes.senior
  else if (level.value === 2) scheme = colorSchemes.specialist
  else scheme = colorSchemes.intern
  
  return {
    hair: scheme.hair[hash % scheme.hair.length],
    body: scheme.body[hash % scheme.body.length],
    skin: scheme.skin[hash % scheme.skin.length],
    cape: scheme.cape,
  }
})

const bgColor = computed(() => {
  const id = props.employee.id || '0'
  const hash = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  
  let scheme
  if (level.value === 5) scheme = colorSchemes.partner
  else if (level.value === 4) scheme = colorSchemes.expert
  else if (level.value === 3) scheme = colorSchemes.senior
  else if (level.value === 2) scheme = colorSchemes.specialist
  else scheme = colorSchemes.intern
  
  return scheme.bg[hash % scheme.bg.length]
})

// 级别徽章颜色
const levelStarColor = computed(() => {
  const colors = ['#FFD700', '#FFA500', '#FF6347']
  return colors[(level.value - 3) % colors.length]
})
</script>

<style scoped>
.employee-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
}

.employee-avatar.interactive {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.employee-avatar.interactive:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.avatar-svg {
  display: block;
}

.emoji-fallback {
  font-size: inherit;
  line-height: 1;
}

/* 暗黑模式适配 */
@media (prefers-color-scheme: dark) {
  .employee-avatar {
    background: var(--bg-secondary, #1a1a2e);
  }
}
</style>
