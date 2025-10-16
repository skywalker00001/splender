# 🧪 测试目录

本目录包含所有测试文件、测试分析文档和测试输出。

## 📁 目录结构

```
test/
├── README.md                    # 本文档
├── test_game_suite.py           # 游戏核心机制测试套件
├── test_comprehensive.py        # 全面测试套件（含AI测试）
├── test_evolution.py            # 进化机制测试
├── test_final.py               # 最终AI对局测试
├── AI_TEST_ANALYSIS.md         # AI测试分析报告
└── SOLUTION_FOR_DEADLOCK.md    # 死锁问题解决方案文档
```

## 🎯 测试文件说明

### test_game_suite.py
**核心游戏机制测试**

测试内容：
- 游戏初始化
- 拿球规则（3个不同色/2个同色）
- 买卡和积分
- 预购功能
- 球数上限（10个球限制）
- 最后一轮机制
- 同分排名规则
- 进化功能
- 稀有/传说卡规则

运行方式：
```bash
cd /home/work/houyi/pj_25_q4/splendor
python test/test_game_suite.py
```

### test_comprehensive.py
**全面测试套件**

测试内容：
- 完整游戏流程（4个AI玩家）
- 牌堆耗尽边缘案例
- 最后一轮触发
- 同分平局判定
- 完整进化链测试
- 复杂拿球规则
- 复杂买卡支付（含大师球）
- 球数限制和放回机制

运行方式：
```bash
cd /home/work/houyi/pj_25_q4/splendor
python test/test_comprehensive.py
```

### test_evolution.py
**进化机制测试**

测试内容：
- 基本游戏流程
- 进化条件判断
- 进化链（Lv1→Lv2→Lv3）
- 进化后分数计算

运行方式：
```bash
cd /home/work/houyi/pj_25_q4/splendor
python test/test_evolution.py
```

### test_final.py
**AI完整对局测试**

测试内容：
- 2人局中等AI对战
- 完整游戏流程（从开始到结束）
- AI决策验证
- 球池管理测试

运行方式：
```bash
cd /home/work/houyi/pj_25_q4/splendor
python test/test_final.py
```

## 📊 分析文档

### AI_TEST_ANALYSIS.md
**AI测试分析报告**

内容：
- 死锁原因分析
- AI策略评估
- 性能对比
- 解决方案建议

### SOLUTION_FOR_DEADLOCK.md
**死锁问题解决方案**

内容：
- 死锁场景描述
- 根本原因分析
- 解决方案实现
- 代码示例

## 🚀 快速测试命令

```bash
# 运行所有测试
cd /home/work/houyi/pj_25_q4/splendor
python test/test_game_suite.py && python test/test_comprehensive.py

# 运行特定测试
python test/test_evolution.py
python test/test_final.py

# 运行测试并保存输出
python test/test_game_suite.py > test/output_game_suite.txt 2>&1
python test/test_comprehensive.py > test/output_comprehensive.txt 2>&1
```

## 📝 测试输出

测试输出会保存在当前目录，建议命名格式：
- `output_<测试名称>.txt` - 标准输出
- `error_<测试名称>.txt` - 错误输出（如果需要）

## ⚠️ 注意事项

1. **路径依赖**: 所有测试文件已配置父目录导入，从项目根目录运行即可
2. **随机性**: 某些测试使用随机种子（seed=42），确保结果可复现
3. **超时设置**: AI对局测试设置了500回合上限，防止无限循环
4. **依赖文件**: 测试依赖 `splendor_pokemon.py` 和 `backend/ai_player.py`

## 🔧 开发建议

### 添加新测试
1. 在 `test/` 目录创建新的测试文件
2. 添加路径配置：
   ```python
   import sys
   import os
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```
3. 导入需要的模块：
   ```python
   from splendor_pokemon import *
   from backend.ai_player import AIPlayer
   ```
4. 更新本README文档

### 测试最佳实践
- ✅ 使用清晰的测试标题和描述
- ✅ 每个测试函数只测试一个功能点
- ✅ 使用断言验证结果
- ✅ 打印详细的测试过程和结果
- ✅ 处理异常情况并打印错误信息

## 📚 相关文档

- 主项目README: `../README.md`
- 游戏规则: `../游戏逻辑流程图.md`
- AI策略: `../backend/AI_STRATEGY.md`
- AI优化总结: `../AI_OPTIMIZATION_SUMMARY.md`
- 卡牌数据说明: `../卡牌数据导入说明.md`

---

**最后更新**: 2025-10-16  
**维护者**: 开发团队

