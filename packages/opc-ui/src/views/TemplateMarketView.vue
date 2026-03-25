<template>
  <div class="template-market">
    <div class="page-header">
      <h1>{{ $t('templateMarket.title') }}</h1>
      <div class="header-actions">
        <el-input
          v-model="searchQuery"
          :placeholder="$t('templateMarket.search')"
          prefix-icon="Search"
          class="search-input"
          @input="debouncedSearch"
        />
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          {{ $t('templateMarket.create') }}
        </el-button>
      </div>
    </div>

    <!-- 分类标签 -->
    <div class="category-tabs">
      <el-radio-group v-model="selectedCategory" @change="filterTemplates">
        <el-radio-button label="">{{ $t('templateMarket.all') }}</el-radio-button>
        <el-radio-button v-for="cat in categories" :key="cat" :label="cat">
          {{ cat }}
        </el-radio-button>
      </el-radio-group>
      
      <el-radio-group v-model="sortBy" @change="sortTemplates">
        <el-radio-button label="usage_count">{{ $t('templateMarket.popular') }}</el-radio-button>
        <el-radio-button label="rating">{{ $t('templateMarket.topRated') }}</el-radio-button>
        <el-radio-button label="created_at">{{ $t('templateMarket.newest') }}</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 模板列表 -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="6" animated />
    </div>
    
    <div v-else-if="templates.length === 0" class="empty-state">
      <el-empty :description="$t('templateMarket.empty')" />
    </div>
    
    <div v-else class="template-grid">
      <el-card
        v-for="template in templates"
        :key="template.id"
        class="template-card"
        :body-style="{ padding: '0' }"
      >
        <div class="template-header">
          <el-tag v-if="template.is_system" type="success" size="small">{{ $t('templateMarket.system') }}</el-tag>
          <el-tag v-if="template.is_public" type="info" size="small">{{ $t('templateMarket.public') }}</el-tag>
          <div class="rating">
            <el-icon><StarFilled /></el-icon>
            <span>{{ template.avg_rating.toFixed(1) }}</span>
            <span class="rating-count">({{ template.rating_count }})</span>
          </div>
        </div>
        
        <div class="template-content">
          <h3>{{ template.name }}</h3>
          <p class="description">{{ template.description || $t('templateMarket.noDescription') }}</p>
          
          <div class="meta">
            <span class="usage">
              <el-icon><User /></el-icon>
              {{ template.usage_count }} {{ $t('templateMarket.uses') }}
            </span>
            <span class="steps">
              <el-icon><Connection /></el-icon>
              {{ getStepCount(template) }} {{ $t('templateMarket.steps') }}
            </span>
          </div>
          
          <div class="tags">
            <el-tag
              v-for="tag in getTags(template)"
              :key="tag"
              size="small"
              effect="plain"
            >
              {{ tag }}
            </el-tag>
          </div>
        </div>
        
        <div class="template-actions">
          <el-button type="primary" @click="useTemplate(template)">
            {{ $t('templateMarket.use') }}
          </el-button>
          <el-button v-if="!template.is_system" @click="forkTemplate(template)">
            {{ $t('templateMarket.fork') }}
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 使用模板对话框 -->
    <el-dialog
      v-model="showUseDialog"
      :title="$t('templateMarket.useTemplate')"
      width="600px"
    >
      <el-form :model="useForm" label-position="top">
        <el-form-item :label="$t('templateMarket.workflowName')">
          <el-input v-model="useForm.name" />
        </el-form-item>
        <el-form-item :label="$t('templateMarket.initialInput')">
          <el-input
            v-model="useForm.initialInput"
            type="textarea"
            :rows="4"
            placeholder="{ 'key': 'value' }"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUseDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="creating" @click="confirmUseTemplate">
          {{ $t('templateMarket.createWorkflow') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 创建模板对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="$t('templateMarket.createTemplate')"
      width="700px"
    >
      <el-form :model="createForm" label-position="top">
        <el-form-item :label="$t('templateMarket.name')" required>
          <el-input v-model="createForm.name" />
        </el-form-item>
        <el-form-item :label="$t('templateMarket.description')">
          <el-input v-model="createForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item :label="$t('templateMarket.category')" required>
          <el-input v-model="createForm.category" />
        </el-form-item>
        <el-form-item :label="$t('templateMarket.tags')">
          <el-select
            v-model="createForm.tags"
            multiple
            filterable
            allow-create
            placeholder="添加标签"
          />
        </el-form-item>
        <el-form-item :label="$t('templateMarket.steps')" required>
          <div class="steps-editor">
            <div
              v-for="(step, index) in createForm.steps_config"
              :key="index"
              class="step-item"
            >
              <el-input v-model="step.title" :placeholder="$t('templateMarket.stepTitle')" />
              <el-select v-model="step.employee_id" :placeholder="$t('templateMarket.selectEmployee')">
                <el-option
                  v-for="emp in employees"
                  :key="emp.id"
                  :label="emp.name"
                  :value="emp.id"
                />
              </el-select>
              <el-input-number v-model="step.estimated_cost" :min="0" :precision="2" />
              <el-button type="danger" @click="removeStep(index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-button @click="addStep">
              <el-icon><Plus /></el-icon>
              {{ $t('templateMarket.addStep') }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="createForm.is_public">{{ $t('templateMarket.makePublic') }}</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="creating" @click="confirmCreate">
          {{ $t('templateMarket.create') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Plus, StarFilled, User, Connection, Delete } from '@element-plus/icons-vue'
import { useTemplateStore } from '@/stores/template'
import { useEmployeeStore } from '@/stores/employee'

const router = useRouter()
const templateStore = useTemplateStore()
const employeeStore = useEmployeeStore()

// 状态
const loading = ref(false)
const templates = ref([])
const categories = ref([])
const employees = ref([])
const searchQuery = ref('')
const selectedCategory = ref('')
const sortBy = ref('usage_count')

// 对话框状态
const showUseDialog = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const selectedTemplate = ref(null)

// 表单
const useForm = ref({
  name: '',
  initialInput: '{}',
})

const createForm = ref({
  name: '',
  description: '',
  category: 'general',
  tags: [],
  steps_config: [],
  is_public: false,
})

// 方法
const loadTemplates = async () => {
  loading.value = true
  try {
    const result = await templateStore.listTemplates({
      category: selectedCategory.value || undefined,
      sort_by: sortBy.value,
    })
    templates.value = result.templates || []
    categories.value = result.categories || []
  } catch (error) {
    ElMessage.error('加载模板失败')
  } finally {
    loading.value = false
  }
}

const loadEmployees = async () => {
  try {
    await employeeStore.fetchEmployees()
    employees.value = employeeStore.employees
  } catch (error) {
    console.error('加载员工失败', error)
  }
}

const debouncedSearch = () => {
  // TODO: 实现搜索
}

const filterTemplates = () => {
  loadTemplates()
}

const sortTemplates = () => {
  loadTemplates()
}

const getStepCount = (template) => {
  try {
    const config = JSON.parse(template.steps_config || '[]')
    return config.length
  } catch {
    return 0
  }
}

const getTags = (template) => {
  try {
    return JSON.parse(template.tags || '[]')
  } catch {
    return []
  }
}

const useTemplate = (template) => {
  selectedTemplate.value = template
  useForm.value.name = template.name
  showUseDialog.value = true
}

const confirmUseTemplate = async () => {
  if (!selectedTemplate.value) return
  
  creating.value = true
  try {
    let initialInput = {}
    try {
      initialInput = JSON.parse(useForm.value.initialInput)
    } catch {
      ElMessage.warning('初始输入格式错误，使用空对象')
    }
    
    const result = await templateStore.createWorkflowFromTemplate(
      selectedTemplate.value.id,
      {
        initial_input: initialInput,
        workflow_name: useForm.value.name,
      }
    )
    
    ElMessage.success('工作流创建成功')
    showUseDialog.value = false
    router.push(`/workflows/${result.data.workflow_id}`)
  } catch (error) {
    ElMessage.error('创建工作流失败')
  } finally {
    creating.value = false
  }
}

const forkTemplate = async (template) => {
  try {
    const newName = `${template.name} (Fork)`
    await templateStore.forkTemplate(template.id, { new_name: newName })
    ElMessage.success('Fork成功')
    loadTemplates()
  } catch (error) {
    ElMessage.error('Fork失败')
  }
}

const addStep = () => {
  createForm.value.steps_config.push({
    title: '',
    employee_id: '',
    estimated_cost: 0.5,
    description: '',
  })
}

const removeStep = (index) => {
  createForm.value.steps_config.splice(index, 1)
}

const confirmCreate = async () => {
  if (!createForm.value.name || createForm.value.steps_config.length === 0) {
    ElMessage.warning('请填写必填项')
    return
  }
  
  creating.value = true
  try {
    await templateStore.createTemplate(createForm.value)
    ElMessage.success('模板创建成功')
    showCreateDialog.value = false
    loadTemplates()
  } catch (error) {
    ElMessage.error('创建模板失败')
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  loadTemplates()
  loadEmployees()
})
</script>

<style scoped>
.template-market {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.search-input {
  width: 300px;
}

.category-tabs {
  display: flex;
  justify-content: space-between;
  margin-bottom: 24px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.template-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.template-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.template-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.rating {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #f7ba2a;
}

.rating-count {
  color: #909399;
  font-size: 12px;
}

.template-content {
  padding: 16px;
}

.template-content h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
}

.description {
  color: #606266;
  font-size: 14px;
  margin: 0 0 12px 0;
  min-height: 40px;
}

.meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #909399;
}

.meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.template-actions {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #e4e7ed;
}

.steps-editor {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 12px;
}

.step-item {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  align-items: center;
}

.step-item .el-input {
  flex: 1;
}

.step-item .el-select {
  width: 150px;
}

.loading-state,
.empty-state {
  padding: 40px;
}
</style>
