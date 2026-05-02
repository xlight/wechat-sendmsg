#!/usr/bin/env python3
"""
测试配置和路径模块 — 验证 Config 加载、paths 工具函数
"""

import os
import json
import unittest
import tempfile


class TestPaths(unittest.TestCase):
    """测试 paths 工具函数。"""

    def setUp(self):
        # 确保不受编译模式影响
        self._patcher = None

    def test_get_base_dir(self):
        """基准目录路径正确。"""
        from paths import get_base_dir
        base = get_base_dir()
        self.assertTrue(os.path.isdir(base))

    def test_get_config_path(self):
        """配置文件路径包含 'config.json'。"""
        from paths import get_config_path
        path = get_config_path()
        self.assertTrue(path.endswith('config.json'))

    def test_get_db_path(self):
        """数据库路径包含 'messages.db'。"""
        from paths import get_db_path
        path = get_db_path()
        self.assertTrue(path.endswith('messages.db'))

    def test_get_data_dir(self):
        """数据目录路径包含 'data'。"""
        from paths import get_data_dir
        path = get_data_dir()
        self.assertTrue(path.endswith('data'))

    def test_is_compiled(self):
        """非编译模式返回 False。"""
        from paths import is_compiled
        self.assertFalse(is_compiled())


class TestConfig(unittest.TestCase):
    """测试 Config 配置管理。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='wechat_test_config_')
        self.config_path = os.path.join(self.tmpdir, 'config.json')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_defaults_when_no_file(self):
        """配置文件不存在时加载默认值。"""
        from config import Config
        # 创建一个指向不存在的路径的配置
        config = Config(config_path=self.config_path)
        self.assertEqual(config.http_port, 8080)
        self.assertIsNotNone(config.wechat_hotkey)

    def test_load_user_config(self):
        """加载用户自定义配置。"""
        user_config = {
            'http_port': 9000,
            'rate_limit_per_minute': 5,
        }
        with open(self.config_path, 'w') as f:
            json.dump(user_config, f)

        from config import Config
        config = Config(config_path=self.config_path)
        self.assertEqual(config.http_port, 9000)
        self.assertEqual(config.rate_limit_per_minute, 5)
        # 未设置的项用默认值
        self.assertEqual(config.rate_limit_per_hour, 20)

    def test_update_runtime(self):
        """运行时更新配置。"""
        from config import Config
        config = Config(config_path=self.config_path)
        config.update({'http_port': 7000})
        self.assertEqual(config.http_port, 7000)

    def test_to_dict(self):
        """序列化配置。"""
        from config import Config
        config = Config(config_path=self.config_path)
        d = config.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn('http_port', d)

    def test_mac_specific_config(self):
        """macOS 特有配置项。"""
        from config import Config
        user_cfg = {
            'mac_wechat_hotkey': 'command+shift+w',
            'mac_send_shortcut': 'command+enter',
        }
        with open(self.config_path, 'w') as f:
            json.dump(user_cfg, f)
        config = Config(config_path=self.config_path)
        self.assertEqual(config.mac_wechat_hotkey, 'command+shift+w')
        self.assertEqual(config.mac_send_shortcut, 'command+enter')

    def test_queue_config(self):
        """消息队列配置项。"""
        from config import Config
        config = Config(config_path=self.config_path)
        self.assertIsInstance(config.queue_max_retries, int)
        self.assertIsInstance(config.queue_poll_interval, float)
        self.assertGreater(config.queue_max_retries, 0)


if __name__ == '__main__':
    unittest.main()
