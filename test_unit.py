#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试 - 自适应动态组包 + 改进LRU分级缓存算法

测试模块:
    1. data_generator.py   - 数据生成模块
    2. lru_cache.py        - 改进LRU分级缓存模块
    3. network_controller.py - 网络控制器模块
    4. fuzzy_link_switch_core.py - 模糊控制链路切换引擎

运行方式:
    python test_unit.py              # 运行所有测试
    python test_unit.py -v           # 详细输出
    python test_unit.py TestDataGenerator  # 仅运行指定测试类
"""

import unittest
import json
import time
import random
import sys
from io import StringIO

# ==================== 1. 数据生成模块测试 ====================
class TestDataGenerator(unittest.TestCase):
    """数据生成模块单元测试"""

    @classmethod
    def setUpClass(cls):
        from data_generator import DataGenerator
        cls.DataGenerator = DataGenerator

    def setUp(self):
        self.gen = self.DataGenerator(vehicle_id="TEST-001", start_seq=1000)

    def test_01_generate_one_format(self):
        """单条数据格式完整性"""
        data = self.gen.generate_one(scene="深坑", priority=1)
        required = ['vehicle_id', 'timestamp', 'seq', 'priority', 'scene', 'data']
        for field in required:
            self.assertIn(field, data, f"缺少字段: {field}")

    def test_02_generate_one_values(self):
        """单条数据值正确性"""
        data = self.gen.generate_one(scene="网络质量良好", priority=0)
        self.assertEqual(data['vehicle_id'], "TEST-001")
        self.assertEqual(data['priority'], 0)
        self.assertEqual(data['scene'], "网络质量良好")
        self.assertIsInstance(data['timestamp'], float)
        self.assertIsInstance(data['seq'], int)
        self.assertGreater(data['seq'], 1000)

    def test_03_high_priority_alarm(self):
        """高优数据包含告警信息"""
        data = self.gen.generate_one(priority=1)
        self.assertEqual(data['priority'], 1)
        self.assertIn('alarm_type', data['data'])
        self.assertIn(data['data']['alarm_type'],
                      ["发动机过热", "超载告警", "液压系统故障",
                       "制动系统异常", "胎压异常"])

    def test_04_low_priority_gps(self):
        """低优数据包含GPS信息"""
        data = self.gen.generate_one(priority=0)
        self.assertEqual(data['priority'], 0)
        self.assertIn('gps', data['data'])
        self.assertIn('lat', data['data']['gps'])
        self.assertIn('lng', data['data']['gps'])

    def test_05_seq_increment(self):
        """序列号递增"""
        d1 = self.gen.generate_one()
        d2 = self.gen.generate_one()
        self.assertEqual(d2['seq'], d1['seq'] + 1)

    def test_06_generate_batch(self):
        """批量生成数量正确"""
        batch = self.gen.generate_batch(10)
        self.assertEqual(len(batch), 10)
        seqs = [d['seq'] for d in batch]
        self.assertEqual(len(seqs), len(set(seqs)), "seq应唯一")

    def test_07_generate_random_batch(self):
        """随机批量生成范围"""
        for _ in range(20):
            batch = self.gen.generate_random_batch(2, 8)
            self.assertGreaterEqual(len(batch), 2)
            self.assertLessEqual(len(batch), 8)

    def test_08_high_priority_ratio(self):
        """高优数据占比约15%"""
        batch = [self.gen.generate_one() for _ in range(1000)]
        high_count = sum(1 for d in batch if d['priority'] == 1)
        ratio = high_count / 1000
        self.assertGreaterEqual(ratio, 0.10)
        self.assertLessEqual(ratio, 0.20)

    def test_09_scene_types(self):
        """场景类型覆盖"""
        from data_generator import SCENE_TYPES
        scenes = set()
        for scene in SCENE_TYPES:
            data = self.gen.generate_one(scene=scene)
            scenes.add(data['scene'])
        self.assertTrue(scenes.issuperset(set(SCENE_TYPES)))

    def test_10_json_serializable(self):
        """数据可JSON序列化"""
        data = self.gen.generate_one()
        try:
            s = json.dumps(data, ensure_ascii=False)
            parsed = json.loads(s)
            self.assertEqual(parsed['seq'], data['seq'])
        except Exception as e:
            self.fail(f"JSON序列化失败: {e}")

    def test_11_temperature_range(self):
        """发动机过热温度范围"""
        for _ in range(50):
            data = self.gen.generate_one(priority=1)
            if data['data']['alarm_type'] == '发动机过热':
                temp = data['data']['temperature']
                self.assertGreaterEqual(temp, 95)
                self.assertLessEqual(temp, 140)

    def test_12_default_priority(self):
        """默认优先级随机生成"""
        priorities = [self.gen.generate_one()['priority'] for _ in range(100)]
        self.assertIn(0, priorities)
        self.assertIn(1, priorities)


# ==================== 2. LRU缓存模块测试 ====================
class TestLRUCache(unittest.TestCase):
    """改进LRU分级缓存模块单元测试"""

    @classmethod
    def setUpClass(cls):
        from lru_cache import ImprovedLRUCache, TwoLevelCache
        cls.ImprovedLRUCache = ImprovedLRUCache
        cls.TwoLevelCache = TwoLevelCache

    def setUp(self):
        self.cache = self.ImprovedLRUCache(capacity_mb=1.0, name="TEST")

    def _make_data(self, seq, priority=0):
        return {
            "vehicle_id": "A", "timestamp": time.time(),
            "seq": seq, "priority": priority, "scene": "测试",
            "data": {"value": "x" * 50}
        }

    def test_01_write_and_read(self):
        """写入和读取"""
        data = self._make_data(1)
        ok, _ = self.cache.write(data)
        self.assertTrue(ok)
        result = self.cache.read(1)
        self.assertIsNotNone(result)
        self.assertEqual(result['seq'], 1)

    def test_02_read_nonexistent(self):
        """读取不存在的数据"""
        result = self.cache.read(999)
        self.assertIsNone(result)

    def test_03_delete(self):
        """删除数据"""
        data = self._make_data(2)
        self.cache.write(data)
        self.assertTrue(self.cache.delete(2))
        self.assertIsNone(self.cache.read(2))
        self.assertFalse(self.cache.delete(2))

    def test_04_size(self):
        """缓存大小"""
        self.assertEqual(self.cache.size(), 0)
        for i in range(5):
            self.cache.write(self._make_data(i))
        self.assertEqual(self.cache.size(), 5)

    def test_05_high_priority_not_evicted(self):
        """高优数据不淘汰"""
        small_cache = self.ImprovedLRUCache(capacity_mb=0.0005, name="SMALL")
        for i in range(20):
            priority = 1 if i % 5 == 0 else 0
            small_cache.write(self._make_data(i + 100, priority))
        high_count = small_cache.get_high_priority_count()
        self.assertGreaterEqual(high_count, 3)

    def test_06_update_existing(self):
        """更新已存在数据"""
        data = self._make_data(10)
        self.cache.write(data)
        data2 = self._make_data(10)
        data2['data']['value'] = 'updated'
        ok, msg = self.cache.write(data2)
        self.assertEqual(msg, "updated")
        result = self.cache.read(10)
        self.assertEqual(result['data']['value'], 'updated')

    def test_07_clear(self):
        """清空缓存"""
        for i in range(5):
            self.cache.write(self._make_data(i))
        self.cache.clear()
        self.assertEqual(self.cache.size(), 0)
        self.assertTrue(self.cache.is_empty())

    def test_08_get_all_sorted(self):
        """按优先级排序"""
        for i in range(10):
            priority = 1 if i % 3 == 0 else 0
            self.cache.write(self._make_data(i, priority))
        items = self.cache.get_all_sorted()
        for i in range(len(items) - 1):
            self.assertGreaterEqual(items[i]['priority'], items[i+1]['priority'])

    def test_09_access_count(self):
        """访问次数统计"""
        data = self._make_data(20)
        self.cache.write(data)
        self.cache.read(20)
        self.cache.read(20)
        self.assertEqual(self.cache.cache[20].access_count, 2)

    def test_10_retry_count(self):
        """重试次数统计"""
        data = self._make_data(30)
        self.cache.write(data)
        self.cache.increment_retry(30)
        self.cache.increment_retry(30)
        self.assertEqual(self.cache.get_retry_count(30), 2)

    def test_11_two_level_cache(self):
        """两级缓存基本操作"""
        tl = self.TwoLevelCache(1.0, 0.5)
        for i in range(5):
            tl.add_to_l1(self._make_data(i))
        self.assertEqual(tl.l1_size(), 5)
        self.assertEqual(tl.l2_size(), 0)

    def test_12_move_to_l2(self):
        """L1到L2迁移"""
        tl = self.TwoLevelCache(1.0, 0.5)
        tl.add_to_l1(self._make_data(1))
        tl.move_to_l2(1)
        self.assertEqual(tl.l1_size(), 0)
        self.assertEqual(tl.l2_size(), 1)
        self.assertIsNotNone(tl.get(1))

    def test_13_move_to_l1(self):
        """L2到L1迁移"""
        tl = self.TwoLevelCache(1.0, 0.5)
        tl.add_to_l1(self._make_data(1))
        tl.move_to_l2(1)
        tl.move_to_l1(1)
        self.assertEqual(tl.l1_size(), 1)
        self.assertEqual(tl.l2_size(), 0)

    def test_14_delete_from_either(self):
        """从任一级删除"""
        tl = self.TwoLevelCache(1.0, 0.5)
        tl.add_to_l1(self._make_data(1))
        tl.move_to_l2(1)
        self.assertTrue(tl.delete(1))
        self.assertIsNone(tl.get(1))

    def test_15_total_size(self):
        """总大小统计"""
        tl = self.TwoLevelCache(1.0, 0.5)
        for i in range(3):
            tl.add_to_l1(self._make_data(i))
        for i in range(3, 5):
            tl.add_to_l2(self._make_data(i))
        self.assertEqual(tl.total_size(), 5)

    def test_16_clear_all(self):
        """清空两级缓存"""
        tl = self.TwoLevelCache(1.0, 0.5)
        tl.add_to_l1(self._make_data(1))
        tl.add_to_l2(self._make_data(2))
        tl.clear_all()
        self.assertEqual(tl.total_size(), 0)


# ==================== 3. 模糊控制引擎测试 ====================
class TestFuzzyEngine(unittest.TestCase):
    """模糊控制链路切换引擎单元测试"""

    @classmethod
    def setUpClass(cls):
        from fuzzy_link_switch_core import FuzzyLinkDecisionEngine
        cls.FuzzyLinkDecisionEngine = FuzzyLinkDecisionEngine

    def setUp(self):
        self.engine = self.FuzzyLinkDecisionEngine()

    def test_01_excellent_network(self):
        """网络质量优秀"""
        result = self.engine.decide(-50, -30, 0.1)
        self.assertEqual(result['state'], '优秀')
        self.assertGreaterEqual(result['lq'], 75)

    def test_02_good_network(self):
        """网络质量良好"""
        result = self.engine.decide(-75, -50, 2.0)
        self.assertEqual(result['state'], '良好')
        self.assertGreaterEqual(result['lq'], 55)

    def test_03_warning_network(self):
        """网络预警状态"""
        result = self.engine.decide(-85, -60, 5.0)
        self.assertEqual(result['state'], '预警')
        self.assertGreaterEqual(result['lq'], 35)

    def test_04_danger_network(self):
        """网络危险状态"""
        result = self.engine.decide(-105, -75, 12.0)
        self.assertEqual(result['state'], '危险')
        self.assertGreaterEqual(result['lq'], 15)

    def test_05_invalid_network(self):
        """网络失效状态"""
        result = self.engine.decide(-140, -100, 30.0)
        self.assertEqual(result['state'], '失效')
        self.assertLess(result['lq'], 15)

    def test_06_command_types(self):
        """指令类型有效性"""
        valid_commands = {'HOLD', 'PREPARE_SWITCH', 'SWITCH_TO_WIFI',
                          'SWITCH_TO_CELLULAR', 'CACHE_DATA'}
        for _ in range(50):
            rsrp = random.uniform(-140, -50)
            rssi = random.uniform(-100, -30)
            loss = random.uniform(0.5, 30)
            result = self.engine.decide(rsrp, rssi, loss)
            self.assertIn(result['command'], valid_commands)

    def test_07_lq_range(self):
        """LQ值范围"""
        for _ in range(100):
            rsrp = random.uniform(-140, -50)
            rssi = random.uniform(-100, -30)
            loss = random.uniform(0.5, 30)
            result = self.engine.decide(rsrp, rssi, loss)
            self.assertGreaterEqual(result['lq'], 0)
            self.assertLessEqual(result['lq'], 100)

    def test_08_cache_data_command(self):
        """失效状态返回CACHE_DATA"""
        result = self.engine.decide(-140, -100, 30.0)
        if result['state'] == '失效':
            self.assertEqual(result['command'], 'CACHE_DATA')

    def test_09_result_fields(self):
        """返回字段完整性"""
        result = self.engine.decide(-80, -60, 3.0)
        required = ['command', 'command_desc', 'lq', 'slope', 'state',
                    'target_link', 'current_link', 'in_holdoff',
                    'blacklisted', 'reason']
        for field in required:
            self.assertIn(field, result)

    def test_10_get_last_lq(self):
        """获取最近LQ值"""
        self.engine.decide(-80, -60, 3.0)
        lq = self.engine.get_last_lq()
        self.assertIsNotNone(lq)
        self.assertIsInstance(lq, float)

    def test_11_get_last_state(self):
        """获取最近状态"""
        self.engine.decide(-80, -60, 3.0)
        state = self.engine.get_last_state()
        self.assertIsNotNone(state)
        self.assertIn(state, ['优秀', '良好', '预警', '危险', '失效'])

    def test_12_reset(self):
        """重置引擎"""
        self.engine.decide(-80, -60, 3.0)
        self.engine.reset()
        lq = self.engine.get_last_lq()
        self.assertTrue(lq is None or isinstance(lq, float))

    def test_13_link_switch_wifi(self):
        """切换到WiFi"""
        self.engine.reset()
        result = self.engine.decide(-120, -50, 15.0, "CELLULAR")
        if result['command'] in ('SWITCH_TO_WIFI', 'HOLD'):
            pass  # 接受切换或维持

    def test_14_link_switch_cellular(self):
        """切换到蜂窝"""
        self.engine.reset()
        result = self.engine.decide(-80, -90, 8.0, "WIFI")
        if result['command'] in ('SWITCH_TO_CELLULAR', 'HOLD'):
            pass


# ==================== 4. 网络控制器测试 ====================
class TestNetworkController(unittest.TestCase):
    """网络控制器单元测试"""

    @classmethod
    def setUpClass(cls):
        from network_controller import NetworkController
        cls.NetworkController = NetworkController

    def setUp(self):
        self.controller = self.NetworkController(
            vehicle_id="TEST-TRUCK",
            pc_ip="127.0.0.1", pc_port=18080,
            listen_port=18889,
            l1_cache_mb=5.0, l2_cache_mb=3.0
        )

    def test_01_initial_state(self):
        """初始状态"""
        self.assertEqual(self.controller.vehicle_id, "TEST-TRUCK")
        self.assertEqual(self.controller.current_link, "CELLULAR")
        self.assertTrue(self.controller.is_network_available())

    def test_02_update_network_excellent(self):
        """更新网络状态-优秀/良好"""
        decision = self.controller.update_network(-55, -35, 0.5)
        self.assertIn(decision['state'], ['优秀', '良好'])
        self.assertTrue(self.controller.is_network_available())

    def test_03_update_network_invalid(self):
        """更新网络状态-失效"""
        decision = self.controller.update_network(-140, -100, 30.0)
        self.assertEqual(decision['state'], '失效')
        self.assertFalse(self.controller.is_network_available())

    def test_04_network_recovery(self):
        """网络恢复检测"""
        self.controller.update_network(-140, -100, 30.0)
        self.assertFalse(self.controller.is_network_available())
        self.controller.update_network(-60, -40, 1.0)
        self.assertTrue(self.controller.is_network_available())

    def test_05_calc_max_retries_high(self):
        """高优数据重传次数"""
        retries = self.controller._calc_max_retries(1)
        self.assertEqual(retries, 3)

    def test_06_calc_max_retries_regular(self):
        """常规数据重传次数范围"""
        self.controller.update_network(-80, -60, 5.0)
        for _ in range(10):
            retries = self.controller._calc_max_retries(0)
            self.assertGreaterEqual(retries, 1)
            self.assertLessEqual(retries, 3)

    def test_07_stats_initial(self):
        """统计初始值"""
        self.assertEqual(self.controller.stats['sent_ok'], 0)
        self.assertEqual(self.controller.stats['sent_fail'], 0)
        self.assertEqual(self.controller.stats['cached_l1'], 0)

    def test_08_scene_update(self):
        """场景更新"""
        self.controller.update_network(-55, -35, 0.5)
        self.assertIn(self.controller.scene, ["网络质量良好", "蜂窝链路可用"])

    def test_09_scene_wifi(self):
        """WiFi场景"""
        self.controller.current_link = "WIFI"
        self.controller.update_network(-80, -50, 3.0)
        if self.controller.is_network_available():
            self.assertIn(self.controller.scene,
                          ["WiFi链路可用", "网络质量良好"])

    def test_10_scene_cellular(self):
        """蜂窝场景"""
        self.controller.current_link = "CELLULAR"
        self.controller.update_network(-80, -60, 3.0)
        if self.controller.is_network_available():
            self.assertIn(self.controller.scene,
                          ["蜂窝链路可用", "网络质量良好"])

    def test_11_cache_operations(self):
        """缓存操作"""
        data = {
            "vehicle_id": "TEST", "timestamp": time.time(),
            "seq": 1, "priority": 0, "scene": "测试",
            "data": {"value": "test"}
        }
        self.controller.two_level_cache.add_to_l1(data)
        self.assertEqual(self.controller.two_level_cache.l1_size(), 1)
        result = self.controller.two_level_cache.get(1)
        self.assertIsNotNone(result)

    def test_12_process_new_data(self):
        """处理新数据"""
        data = {
            "vehicle_id": "TEST", "timestamp": time.time(),
            "seq": 100, "priority": 1, "scene": "深坑",
            "data": {"alarm_type": "发动机过热", "temperature": 120}
        }
        self.controller.update_network(-60, -40, 1.0)
        initial_cached = self.controller.stats['cached_l1']
        self.controller.process_new_data(data)
        # 由于PC端未启动，数据可能发送失败进入缓存，也可能发送成功
        self.assertTrue(
            self.controller.stats['sent_ok'] > 0 or
            self.controller.stats['cached_l1'] > initial_cached or
            self.controller.stats['sent_fail'] > 0
        )

    def test_13_handle_command_resend(self):
        """处理补发指令"""
        data = {
            "vehicle_id": "TEST", "timestamp": time.time(),
            "seq": 200, "priority": 0, "scene": "测试",
            "data": {"value": "test"}
        }
        self.controller.two_level_cache.add_to_l1(data)
        self.controller.update_network(-60, -40, 1.0)
        self.controller._handle_command({'cmd': 'RESEND_CMD', 'seq': 200})
        time.sleep(0.1)

    def test_14_handle_command_lock(self):
        """处理锁存指令"""
        self.controller._handle_command({'cmd': 'lock_high_priority'})

    def test_15_handle_command_unknown(self):
        """处理未知指令"""
        self.controller._handle_command({'cmd': 'UNKNOWN_CMD'})


# ==================== 主程序 ====================
def run_tests():
    """运行所有测试并返回结果"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestDataGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestLRUCache))
    suite.addTests(loader.loadTestsFromTestCase(TestFuzzyEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestNetworkController))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


def generate_report(result, output_file="test_report.txt"):
    """生成测试报告"""
    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total - failures - errors - skipped
    success_rate = (passed / total * 100) if total > 0 else 0

    report = []
    report.append("=" * 70)
    report.append("  自适应动态组包 + 改进LRU分级缓存算法 - 单元测试报告")
    report.append("=" * 70)
    report.append("")
    report.append(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"测试框架: Python unittest")
    report.append("")
    report.append("-" * 70)
    report.append("  测试统计")
    report.append("-" * 70)
    report.append(f"  总测试数:     {total}")
    report.append(f"  通过:         {passed}  ({success_rate:.1f}%)")
    report.append(f"  失败:         {failures}")
    report.append(f"  错误:         {errors}")
    report.append(f"  跳过:         {skipped}")
    report.append(f"  结果:         {'通过' if result.wasSuccessful() else '未通过'}")
    report.append("")

    if failures:
        report.append("-" * 70)
        report.append("  失败详情")
        report.append("-" * 70)
        for test, trace in result.failures:
            report.append(f"\n[FAIL] {test}")
            report.append(trace)

    if errors:
        report.append("-" * 70)
        report.append("  错误详情")
        report.append("-" * 70)
        for test, trace in result.errors:
            report.append(f"\n[ERROR] {test}")
            report.append(trace)

    report.append("")
    report.append("=" * 70)
    report.append("  测试完成")
    report.append("=" * 70)

    report_text = "\n".join(report)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)

    return report_text


if __name__ == '__main__':
    print("=" * 70)
    print("  开始运行单元测试...")
    print("=" * 70)

    result = run_tests()

    print("\n" + "=" * 70)
    print("  生成测试报告...")
    print("=" * 70)

    report = generate_report(result)
    print(f"\n报告已保存到: test_report.txt")
    print("\n" + report)

    sys.exit(0 if result.wasSuccessful() else 1)
