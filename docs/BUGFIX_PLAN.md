# v0.3.0-beta 已知问题修复清单

## P1 - 已修复 ✅
- [x] 文件大小限制（5MB）
- [x] PyPyEnum拼写错误

## P2 - 待修复
- [ ] Avatar文件签名验证（magic bytes检查）
- [ ] Avatar更新时URL唯一性（不同style不同文件名）
- [ ] 数据库迁移脚本同步（employee_avatars完整字段）

## P3 - 测试改进
- [ ] Phase 2测试使用真实数据库结构
- [ ] 熔断Split Task子任务验证

---

## 修复计划

### 1. Avatar文件签名验证
**问题**: 恶意文件伪装成图片可通过上传  
**方案**: 检查文件magic bytes

**签名表**:
```python
PNG:  b'\x89PNG\r\n\x1a\n'
JPEG: b'\xff\xd8\xff'
SVG:  开头包含 b'<?xml' 或 b'<svg'
```

### 2. Avatar URL唯一性
**问题**: 同agent不同style生成相同文件名  
**方案**: 文件名包含style信息

**当前**: `{agent_id}_system.svg`  
**修复**: `{agent_id}_{style}_{random}.svg`

### 3. 数据库迁移同步
**问题**: migrate_avatars.py字段不全  
**方案**: 同步所有EmployeeAvatar字段
