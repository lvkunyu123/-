# 基于安卓终端的露天矿盲区数据传输仿真系统

## 项目内容

本项目实现了一套面向露天矿场景的自适应数据传输系统，核心功能包括：

### 核心模块

| 模块 | 文件 | 功能描述 |
|------|------|----------|
| **数据生成模块** | [data_generator.py](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/data_generator.py) | 随机生成符合格式要求的车辆报文数据，支持高/低优先级数据，包含告警信息和GPS信息 |
| **改进LRU分级缓存** | [lru_cache.py](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/lru_cache.py) | 实现两级缓存架构，高优先级数据绝对不淘汰，低优先级数据按评分机制淘汰 |
| **模糊控制链路切换** | [fuzzy_link_switch_core.py](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/fuzzy_link_switch_core.py) | 实时监测链路状态，基于模糊控制算法进行链路切换决策 |
| **网络控制器** | [network_controller.py](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/network_controller.py) | 协调数据传输、缓存、补发流程，根据网络质量动态调整重传策略 |
| **TCP传输模块** | [tcp_sender.py](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/tcp_sender.py) | 负责与PC端的TCP通信，支持命令回调和数据发送 |
| **PC端接收服务** | [dispatch_server.py](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/dispatch_server.py) | 监听8080端口接收数据，存储到SQLite数据库，支持补发指令 |
| **主模拟器** | [main_simulator.py](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/main_simulator.py) | 系统主入口，模拟网络波动，协调各模块运行 |

### 辅助工具

| 工具 | 文件 | 功能描述 |
|------|------|----------|
| 单元测试 | [test_unit.py](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/test_unit.py) | 基于unittest框架的57个单元测试用例 |
| 专业测试 | [test_adaptive_system.py](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/test_adaptive_system.py) | 系统级功能测试和传输成功率模拟 |
| 数据清理 | [clean_duplicate.py](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/clean_duplicate.py) | 清理数据库中的重复记录 |
| 数据库读取 | [read_db.py](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/read_db.py) | 查询数据库中的数据 |

### 数据格式

系统传输的JSON报文格式：

```json
{
    "vehicle_id": "TRUCK-001",
    "timestamp": 1717912345.678,
    "seq": 100,
    "priority": 1,
    "scene": "深坑",
    "data": {
        "alarm_type": "发动机过热",
        "temperature": 120
    }
}
```

| 字段 | 说明 |
|------|------|
| vehicle_id | 车辆标识（车牌号） |
| timestamp | 时间戳（秒） |
| seq | 序列号（递增） |
| priority | 优先级（1=高优，0=低优） |
| scene | 场景（网络质量良好/WiFi链路可用/蜂窝链路可用/无信号/深坑等） |
| data | 传输数据（告警信息或GPS信息） |

---

## 项目的实用性

### 适用场景

本系统适用于**露天矿盲区数据传输**场景，解决以下核心问题：

1. **网络不稳定**：矿区环境复杂，网络信号波动大，系统通过缓存机制保证数据不丢失
2. **链路切换**：支持WiFi和蜂窝双链路，根据网络质量自动切换最优链路
3. **数据优先级**：高优先级告警数据（如发动机过热、制动异常）优先传输，确保关键信息及时送达
4. **缓存淘汰**：改进的LRU算法确保高优数据永不淘汰，低优数据智能淘汰

### 核心特性

- **自适应动态组包**：根据网络质量动态调整传输策略
- **改进LRU分级缓存**：两级缓存架构，高优数据绝对保护
- **模糊控制链路切换**：实时监测网络状态，智能决策链路切换
- **动态重传策略**：高优数据强制重传3次，常规数据根据网络质量动态调整
- **防重复机制**：PC端去重，避免重复数据入库

---

## 用户如何开始项目

### 环境要求

- Python 3.7+
- 依赖库：`statsmodels`, `scikit-fuzzy`, `numpy`

### 安装依赖

```bash
pip install statsmodels scikit-fuzzy numpy
```

### 运行方式

#### 方式一：完整仿真（PC端 + 手机端）

**步骤1：启动PC端接收服务**

```bash
python dispatch_server.py
```

服务将监听 `0.0.0.0:8080`，接收数据并存入 `mine_data.db` 数据库。

**步骤2：启动手机端模拟器**

```bash
# 常驻运行模式
python main_simulator.py forever

# 测试模式（指定周期数）
python main_simulator.py test 100
```

#### 方式二：单元测试

```bash
# 运行所有单元测试
python test_unit.py

# 运行指定测试模块
python test_unit.py TestDataGenerator
python test_unit.py TestLRUCache
python test_unit.py TestFuzzyEngine
python test_unit.py TestNetworkController
```

#### 方式三：专业测试

```bash
python test_adaptive_system.py
```

#### 方式四：清理数据库

```bash
# 清理重复数据并创建唯一索引
python clean_duplicate.py

# 仅预览，不删除
python clean_duplicate.py --dry-run
```

---

## 用户可以在这里获得项目帮助

### 文档资源

- [基于安卓终端的露天矿盲区数据传输仿真方案.pdf](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/基于安卓终端的露天矿盲区数据传输仿真方案.pdf) - 项目详细技术文档
- [矿场部分算法综合.docx](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/矿场部分算法综合.docx) - 算法调研报告

### 测试报告

- [test_report.txt](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/test_report.txt) - 单元测试报告（57个测试用例全部通过）
- [100周期测试运行结果.txt](file:///c:/Users/PC/Desktop/研究生/研0-2026-7/100周期测试运行结果.txt) - 系统仿真测试结果

### 常见问题

**Q: 运行时出现 `Recursive use of cursors not allowed` 错误？**

A: 这是SQLite多线程并发问题。PC端已添加线程锁保护，确保每次操作使用独立cursor。

**Q: 数据库中有重复数据？**

A: 运行 `python clean_duplicate.py` 清理重复数据，系统已添加唯一索引防止重复入库。

**Q: 如何调整网络波动模拟参数？**

A: 修改 `main_simulator.py` 中的 `_generate_network_params()` 方法，调整RSRP、RSSI、Loss的随机范围。

---

## 谁负责维护和贡献项目

### 项目负责人

- **姓名**：研究生团队
- **研究方向**：露天矿盲区数据传输算法研究

### 核心贡献

| 模块 | 负责人 | 功能说明 |
|------|--------|----------|
| 自适应动态组包 | 研究生团队 | 数据生成、传输策略、重传机制 |
| 改进LRU分级缓存 | 研究生团队 | 两级缓存、高优保护、智能淘汰 |
| 模糊控制链路切换 | 研究生团队 | 实时监测、模糊决策、链路切换 |

### 联系信息

如有问题或建议，请联系项目负责人。

---

## 许可证

本项目仅供学术研究使用。
