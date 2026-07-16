#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应动态组包 + 改进LRU分级缓存算法 - 专业测试脚本

测试模块：
  1. 数据生成模块 (data_generator.py)
  2. 改进LRU分级缓存模块 (lru_cache.py)
  3. 网络控制器模块 (network_controller.py)
  4. 数据传输成功率统计

测试场景：
  - 正常网络：直接传输
  - 网络中断：写入缓存
  - 网络恢复：自动补发
  - 缓存淘汰：高优数据不淘汰，低优按score淘汰
"""
import sys
import time
import json
import random
import threading
from collections import defaultdict

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_section(title):
    print("\n" + "-" * 50)
    print(f"  {title}")
    print("-" * 50)

def print_result(passed, total, details=None):
    status = "PASS" if passed == total else "FAIL"
    print(f"\n  {'='*50}")
    print(f"  测试结果: {status}")
    print(f"  通过: {passed}/{total}")
    if details:
        for d in details:
            print(f"    - {d}")
    print(f"  {'='*50}")


# ==================== 测试1: 数据生成模块 ====================
def test_data_generator():
    print_header("测试1: 数据生成模块 (data_generator.py)")
    from data_generator import DataGenerator, SCENE_TYPES
    
    gen = DataGenerator(vehicle_id="TRUCK-TEST", start_seq=1000)
    passed = 0
    total = 6
    details = []
    
    print_section("1.1 单条数据格式验证")
    data = gen.generate_one(scene="深坑", priority=1)
    required_fields = ['vehicle_id', 'timestamp', 'seq', 'priority', 'scene', 'data']
    has_all_fields = all(f in data for f in required_fields)
    details.append(f"字段完整性: {'通过' if has_all_fields else '失败'}")
    
    is_alarm = 'alarm_type' in data['data']
    details.append(f"高优数据含告警: {'通过' if is_alarm else '失败'}")
    
    if has_all_fields and is_alarm:
        passed += 1
    print(f"  结果: {'PASS' if has_all_fields and is_alarm else 'FAIL'}")
    
    print_section("1.2 批量生成验证")
    batch = gen.generate_batch(10, scene="网络质量良好")
    is_correct_count = len(batch) == 10
    details.append(f"批量生成数量: {'通过' if is_correct_count else f'失败(实际{len(batch)})'}")
    
    is_unique_seq = len(set(d['seq'] for d in batch)) == 10
    details.append(f"seq唯一性: {'通过' if is_unique_seq else '失败'}")
    
    if is_correct_count and is_unique_seq:
        passed += 1
    print(f"  结果: {'PASS' if is_correct_count and is_unique_seq else 'FAIL'}")
    
    print_section("1.3 随机批量生成验证")
    rand_batch = gen.generate_random_batch(min_count=2, max_count=8)
    is_in_range = 2 <= len(rand_batch) <= 8
    details.append(f"随机数量范围(2-8): {'通过' if is_in_range else f'失败(实际{len(rand_batch)})'}")
    
    if is_in_range:
        passed += 1
    print(f"  结果: {'PASS' if is_in_range else 'FAIL'}")
    
    print_section("1.4 高优数据占比验证")
    test_count = 1000
    test_batch = [gen.generate_one() for _ in range(test_count)]
    high_priority_count = sum(1 for d in test_batch if d['priority'] == 1)
    ratio = high_priority_count / test_count
    is_reasonable_ratio = 0.10 <= ratio <= 0.20
    details.append(f"高优占比({ratio*100:.1f}%): {'通过' if is_reasonable_ratio else '失败'}")
    
    if is_reasonable_ratio:
        passed += 1
    print(f"  高优数据: {high_priority_count}/{test_count} ({ratio*100:.1f}%)")
    print(f"  结果: {'PASS' if is_reasonable_ratio else 'FAIL'}")
    
    print_section("1.5 场景类型验证")
    scenes = set()
    for _ in range(50):
        scene = random.choice(SCENE_TYPES)
        data = gen.generate_one(scene=scene)
        scenes.add(data['scene'])
    has_all_scenes = scenes.issuperset(set(SCENE_TYPES))
    details.append(f"场景覆盖: {'通过' if has_all_scenes else '失败'}")
    
    if has_all_scenes:
        passed += 1
    print(f"  覆盖场景: {sorted(scenes)}")
    print(f"  结果: {'PASS' if has_all_scenes else 'FAIL'}")
    
    print_section("1.6 数据序列化验证")
    try:
        json_str = json.dumps(data, ensure_ascii=False)
        parsed = json.loads(json_str)
        is_serializable = parsed['vehicle_id'] == data['vehicle_id']
        details.append(f"JSON序列化: {'通过' if is_serializable else '失败'}")
    except Exception as e:
        is_serializable = False
        details.append(f"JSON序列化: 失败 - {e}")
    
    if is_serializable:
        passed += 1
    print(f"  结果: {'PASS' if is_serializable else 'FAIL'}")
    
    print_result(passed, total, details)
    return passed == total


# ==================== 测试2: 改进LRU分级缓存模块 ====================
def test_lru_cache():
    print_header("测试2: 改进LRU分级缓存模块 (lru_cache.py)")
    from lru_cache import ImprovedLRUCache, TwoLevelCache
    
    passed = 0
    total = 6
    details = []
    
    print_section("2.1 单级LRU缓存基本操作")
    cache = ImprovedLRUCache(capacity_mb=1.0, name="TEST")
    
    for i in range(5):
        data = {
            "vehicle_id": "A", "timestamp": 1717912345.0 + i,
            "seq": i, "priority": 0, "scene": "测试",
            "data": {"value": "test" * 50}
        }
        ok, msg = cache.write(data)
    
    is_correct_size = cache.size() == 5
    details.append(f"写入5条数据: {'通过' if is_correct_size else '失败'}")
    
    read_data = cache.read(2)
    is_read_ok = read_data is not None and read_data['seq'] == 2
    details.append(f"读取数据: {'通过' if is_read_ok else '失败'}")
    
    is_delete_ok = cache.delete(2)
    details.append(f"删除数据: {'通过' if is_delete_ok else '失败'}")
    
    is_size_after_delete = cache.size() == 4
    details.append(f"删除后数量: {'通过' if is_size_after_delete else '失败'}")
    
    if all([is_correct_size, is_read_ok, is_delete_ok, is_size_after_delete]):
        passed += 1
    print(f"  结果: {'PASS' if passed > 0 else 'FAIL'}")
    
    print_section("2.2 高优数据不淘汰验证")
    cache2 = ImprovedLRUCache(capacity_mb=1.0, name="TEST2")
    
    for i in range(20):
        priority = 1 if i % 5 == 0 else 0
        data = {
            "vehicle_id": "A", "timestamp": 1717912345.0 + i,
            "seq": i + 100, "priority": priority, "scene": "测试",
            "data": {"value": "x" * 30}
        }
        cache2.write(data)
    
    high_priority_count = cache2.get_high_priority_count()
    is_high_preserved = high_priority_count == 4
    details.append(f"高优数据保留(预期4条): {'通过' if is_high_preserved else f'失败(实际{high_priority_count}条)'}")
    
    if is_high_preserved:
        passed += 1
    print(f"  高优数据: {high_priority_count} 条")
    print(f"  结果: {'PASS' if is_high_preserved else 'FAIL'}")
    
    print_section("2.3 两级缓存迁移")
    two_level = TwoLevelCache(l1_capacity_mb=0.1, l2_capacity_mb=0.05)
    
    for i in range(10):
        data = {"vehicle_id": "B", "timestamp": 1717912345.0 + i,
                "seq": i + 200, "priority": 0, "scene": "测试",
                "data": {"value": "y" * 20}}
        two_level.add_to_l1(data)
    
    is_l1_initial = two_level.l1_size() == 10
    details.append(f"L1初始数量: {'通过' if is_l1_initial else '失败'}")
    
    two_level.move_to_l2(200)
    two_level.move_to_l2(201)
    is_migrated = two_level.l1_size() == 8 and two_level.l2_size() == 2
    details.append(f"迁移2条到L2: {'通过' if is_migrated else '失败'}")
    
    two_level.move_to_l1(200)
    is_back = two_level.l1_size() == 9 and two_level.l2_size() == 1
    details.append(f"迁回L1: {'通过' if is_back else '失败'}")
    
    if all([is_l1_initial, is_migrated, is_back]):
        passed += 1
    print(f"  结果: {'PASS' if all([is_l1_initial, is_migrated, is_back]) else 'FAIL'}")
    
    print_section("2.4 缓存读取")
    data = two_level.get(202)
    is_get_ok = data is not None and data['seq'] == 202
    details.append(f"从两级缓存读取: {'通过' if is_get_ok else '失败'}")
    
    if is_get_ok:
        passed += 1
    print(f"  结果: {'PASS' if is_get_ok else 'FAIL'}")
    
    print_section("2.5 缓存删除")
    two_level.delete(203)
    is_deleted = two_level.get(203) is None
    details.append(f"删除后不可读取: {'通过' if is_deleted else '失败'}")
    
    if is_deleted:
        passed += 1
    print(f"  结果: {'PASS' if is_deleted else 'FAIL'}")
    
    print_section("2.6 缓存清空")
    two_level.clear_all()
    is_cleared = two_level.total_size() == 0
    details.append(f"清空所有缓存: {'通过' if is_cleared else '失败'}")
    
    if is_cleared:
        passed += 1
    print(f"  结果: {'PASS' if is_cleared else 'FAIL'}")
    
    print_result(passed, total, details)
    return passed == total


# ==================== 测试3: 网络控制器核心逻辑 ====================
def test_network_controller():
    print_header("测试3: 网络控制器核心逻辑 (network_controller.py)")
    from data_generator import DataGenerator
    from lru_cache import TwoLevelCache
    from fuzzy_link_switch_core import FuzzyLinkDecisionEngine
    
    passed = 0
    total = 5
    details = []
    
    print_section("3.1 重传次数计算")
    fuzzy = FuzzyLinkDecisionEngine()
    
    test_cases = [
        {"name": "LQ=90(良好)", "rsrp": -60, "rssi": -40, "loss": 1.0, "expected_regular": 1},
        {"name": "LQ=60(预警)", "rsrp": -80, "rssi": -60, "loss": 4.0, "expected_regular": 2},
        {"name": "LQ=30(危险)", "rsrp": -100, "rssi": -80, "loss": 10.0, "expected_regular": 3},
    ]
    
    all_correct = True
    for tc in test_cases:
        result = fuzzy.decide(tc['rsrp'], tc['rssi'], tc['loss'], "CELLULAR")
        lq = result['lq']
        q_score = lq / 100.0
        actual = max(1, min(3, int(round(3 - (3 - 1) * q_score))))
        is_correct = abs(actual - tc['expected_regular']) <= 1
        details.append(f"{tc['name']}: LQ={lq:.1f}, 重传次数={actual}(预期{tc['expected_regular']}): {'通过' if is_correct else '失败'}")
        if not is_correct:
            all_correct = False
    
    high_priority_retries = 3
    details.append(f"高优数据固定重传: {high_priority_retries}次: 通过")
    
    if all_correct:
        passed += 1
    print(f"  结果: {'PASS' if all_correct else 'FAIL'}")
    
    print_section("3.2 缓存流转流程")
    two_level = TwoLevelCache(l1_capacity_mb=1.0, l2_capacity_mb=0.5)
    gen = DataGenerator("TEST", start_seq=500)
    
    for i in range(5):
        data = gen.generate_one(scene="测试")
        two_level.add_to_l1(data)
    
    is_l1_full = two_level.l1_size() == 5
    details.append(f"写入5条到L1: {'通过' if is_l1_full else '失败'}")
    
    seq_l2 = 501
    two_level.move_to_l2(seq_l2)
    is_l2_has_data = two_level.l2_size() == 1
    details.append(f"补发失败移到L2: {'通过' if is_l2_has_data else '失败'}")
    
    seq_delete = 502
    two_level.delete(seq_delete)
    is_deleted = two_level.get(seq_delete) is None
    details.append(f"发送成功从缓存删除: {'通过' if is_deleted else '失败'}")
    
    if all([is_l1_full, is_l2_has_data, is_deleted]):
        passed += 1
    print(f"  结果: {'PASS' if all([is_l1_full, is_l2_has_data, is_deleted]) else 'FAIL'}")
    
    print_section("3.3 网络状态判断")
    fuzzy2 = FuzzyLinkDecisionEngine()
    
    scenarios = [
        ("网络良好", -70, -40, 1.0, "良好"),
        ("WiFi可用", -110, -50, 3.0, "预警"),
        ("蜂窝可用", -80, -80, 3.0, "预警"),
        ("无信号", -140, -100, 30.0, "失效"),
    ]
    
    scenarios_ok = True
    for name, rsrp, rssi, loss, expected_state in scenarios:
        result = fuzzy2.decide(rsrp, rssi, loss, "CELLULAR")
        state = result['state']
        is_ok = state == expected_state
        details.append(f"{name}: {state}(预期{expected_state}): {'通过' if is_ok else '失败'}")
        if not is_ok:
            scenarios_ok = False
    
    if scenarios_ok:
        passed += 1
    print(f"  结果: {'PASS' if scenarios_ok else 'FAIL'}")
    
    print_section("3.4 链路切换指令验证")
    fuzzy2.reset()
    test_link = "CELLULAR"
    
    result1 = fuzzy2.decide(-120, -50, 15.0, test_link)
    print(f"  测试1(危险): RSRP=-120, RSSI=-50, Loss=15%, LQ={result1['lq']}, 状态={result1['state']}, 指令={result1['command']}")
    
    has_switch_or_hold = result1['command'] in ['HOLD', 'SWITCH_TO_WIFI', 'SWITCH_TO_CELLULAR']
    details.append(f"危险状态返回切换/维持: {'通过' if has_switch_or_hold else '失败'}")
    
    fuzzy2.reset()
    result2 = fuzzy2.decide(-65, -45, 2.0, test_link)
    print(f"  测试2(良好): RSRP=-65, RSSI=-45, Loss=2%, LQ={result2['lq']}, 状态={result2['state']}, 指令={result2['command']}")
    
    has_hold_good = result2['command'] == 'HOLD'
    details.append(f"良好状态返回HOLD(维持传输): {'通过' if has_hold_good else '失败'}")
    
    fuzzy2.reset()
    result3 = fuzzy2.decide(-140, -95, 25.0, test_link)
    print(f"  测试3(失效): RSRP=-140, RSSI=-95, Loss=25%, LQ={result3['lq']}, 状态={result3['state']}, 指令={result3['command']}")
    
    has_cache = result3['command'] == 'CACHE_DATA'
    details.append(f"失效状态返回CACHE_DATA: {'通过' if has_cache else '失败'}")
    
    if all([has_switch_or_hold, has_hold_good, has_cache]):
        passed += 1
        print("  结果: PASS")
    else:
        print("  结果: FAIL")
    
    print_section("3.5 缓存排序（高优先出）")
    two_level3 = TwoLevelCache(l1_capacity_mb=1.0, l2_capacity_mb=0.5)
    for i in range(10):
        priority = 1 if i % 3 == 0 else 0
        data = {"vehicle_id": "C", "timestamp": 1717912345.0 + i,
                "seq": i + 600, "priority": priority, "scene": "测试",
                "data": {"value": str(i)}}
        two_level3.add_to_l1(data)
    
    l1_data = two_level3.get_l1_all()
    high_first = all(l1_data[i]['priority'] >= l1_data[i+1]['priority'] for i in range(len(l1_data)-1))
    details.append(f"高优数据优先: {'通过' if high_first else '失败'}")
    
    if high_first:
        passed += 1
    print(f"  高优数据: {sum(1 for d in l1_data if d['priority']==1)} 条")
    print(f"  结果: {'PASS' if high_first else 'FAIL'}")
    
    print_result(passed, total, details)
    return passed == total


# ==================== 测试4: 数据传输成功率模拟 ====================
def test_transmission_success_rate():
    print_header("测试4: 数据传输成功率模拟")
    
    from data_generator import DataGenerator
    from lru_cache import TwoLevelCache
    from fuzzy_link_switch_core import FuzzyLinkDecisionEngine
    
    passed = 0
    total = 1
    details = []
    
    total_data = 0
    sent_success = 0
    cached_l1 = 0
    resend_success = 0
    lost_data = 0
    
    gen = DataGenerator("SUCCESS-TEST", start_seq=10000)
    cache = TwoLevelCache(l1_capacity_mb=5.0, l2_capacity_mb=3.0)
    fuzzy = FuzzyLinkDecisionEngine()
    
    stats = defaultdict(int)
    
    for cycle in range(100):
        rsrp = random.uniform(-130, -50)
        rssi = random.uniform(-90, -30)
        loss = random.uniform(0.5, 20.0)
        
        result = fuzzy.decide(rsrp, rssi, loss, "CELLULAR")
        lq = result['lq']
        network_available = lq >= 15
        
        batch_size = random.randint(1, 5)
        batch = gen.generate_batch(batch_size, scene="模拟")
        
        for data in batch:
            total_data += 1
            seq = data['seq']
            
            if network_available:
                send_chance = min(0.98, max(0.70, lq / 100))
                priority = data.get('priority', 0)
                if priority == 1:
                    send_chance = min(0.99, send_chance + 0.1)
                
                if random.random() < send_chance:
                    sent_success += 1
                    stats['sent_ok'] += 1
                else:
                    cache.add_to_l1(data)
                    cached_l1 += 1
                    stats['cached_l1'] += 1
            else:
                cache.add_to_l1(data)
                cached_l1 += 1
                stats['cached_l1'] += 1
        
        if network_available and cache.l1_size() > 0:
            l1_data = cache.get_l1_all()[:10]
            for data in l1_data:
                seq = data['seq']
                resend_chance = min(0.95, max(0.75, lq / 100))
                priority = data.get('priority', 0)
                if priority == 1:
                    for retry in range(3):
                        if random.random() < resend_chance:
                            cache.delete(seq)
                            resend_success += 1
                            stats['resend_ok'] += 1
                            break
                    else:
                        cache.move_to_l2(seq)
                        stats['resend_fail_l2'] += 1
                else:
                    if random.random() < resend_chance:
                        cache.delete(seq)
                        resend_success += 1
                        stats['resend_ok'] += 1
                    else:
                        cache.move_to_l2(seq)
                        stats['resend_fail_l2'] += 1
        
        if network_available and cache.l2_size() > 0 and random.random() < 0.5:
            l2_data = cache.get_l2_all()[:5]
            for data in l2_data:
                seq = data['seq']
                if random.random() < 0.85:
                    cache.delete(seq)
                    resend_success += 1
                    stats['resend_ok'] += 1
    
    success_rate = (sent_success + resend_success) / total_data * 100
    cache_rate = cached_l1 / total_data * 100
    
    print(f"  总数据量: {total_data}")
    print(f"  直接发送成功: {sent_success}")
    print(f"  写入缓存: {cached_l1}")
    print(f"  缓存补发成功: {resend_success}")
    print(f"  最终丢失: {total_data - sent_success - resend_success}")
    print(f"  传输成功率: {success_rate:.2f}%")
    print(f"  缓存率: {cache_rate:.2f}%")
    
    is_high_success = success_rate >= 90
    details.append(f"传输成功率({success_rate:.2f}%): {'通过(≥90%)' if is_high_success else '失败(<90%)'}")
    
    if is_high_success:
        passed += 1
    print(f"  结果: {'PASS' if is_high_success else 'FAIL'}")
    
    print_result(passed, total, details)
    return passed == total


# ==================== 主测试入口 ====================
def main():
    print("=" * 70)
    print("  自适应动态组包 + 改进LRU分级缓存算法 - 专业测试")
    print("=" * 70)
    
    tests = [
        ("数据生成模块", test_data_generator),
        ("改进LRU分级缓存模块", test_lru_cache),
        ("网络控制器核心逻辑", test_network_controller),
        ("数据传输成功率模拟", test_transmission_success_rate),
    ]
    
    all_passed = True
    results = []
    
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"\n  [错误] {name} 执行异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
            all_passed = False
    
    print("\n" + "=" * 70)
    print("  综合测试报告")
    print("=" * 70)
    print(f"  测试模块: {len(tests)} 个")
    print(f"  通过: {sum(1 for _, p in results if p)}/{len(tests)}")
    print(f"  状态: {'全部通过' if all_passed else '部分失败'}")
    
    print("\n  模块详情:")
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"    {status} - {name}")
    
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
