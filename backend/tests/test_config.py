"""Tests for Configuration Management

This module tests the ConfigLoader utility and configuration loading from:
- YAML files
- Environment variables
- Default values
- Kubernetes ConfigMap integration
"""

import os
import pytest
import tempfile
from pathlib import Path
import yaml
from api.utils.config import ConfigLoader


class TestConfigLoader:
    """Test ConfigLoader functionality"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Clear cached config before each test
        ConfigLoader.clear()
        yield
        # Clear after test
        ConfigLoader.clear()

    @pytest.fixture
    def sample_config_file(self):
        """Create a temporary config file for testing"""
        config_data = {
            'django': {
                'secret_key': 'test-secret-key',
                'debug': False,
                'allowed_hosts': ['example.com', 'test.com'],
            },
            'database': {
                'host': 'db.example.com',
                'port': 3306,
                'name': 'testdb',
                'user': 'testuser',
                'password': 'testpass',
            },
            'cache': {
                'enable_redis': True,
                'redis': {
                    'host': 'redis.example.com',
                    'port': 6379,
                },
                'ttl': {
                    'problem_list': 300,
                    'problem_detail': 600,
                },
            },
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_load_from_yaml_file(self, sample_config_file):
        """Test loading configuration from YAML file"""
        config = ConfigLoader.load(config_path=sample_config_file)

        # Test basic get
        assert config.get('django.secret_key') == 'test-secret-key'
        assert config.get('database.host') == 'db.example.com'
        assert config.get('cache.redis.host') == 'redis.example.com'

    def test_get_with_default_value(self, sample_config_file):
        """Test get with default value for non-existent keys"""
        config = ConfigLoader.load(config_path=sample_config_file)

        # Non-existent key should return default
        assert config.get('non.existent.key', default='default_value') == 'default_value'
        assert config.get('another.missing.key') is None

    def test_get_bool(self, sample_config_file):
        """Test get_bool for boolean values"""
        config = ConfigLoader.load(config_path=sample_config_file)

        assert config.get_bool('django.debug') is False
        assert config.get_bool('cache.enable_redis') is True
        assert config.get_bool('non.existent', default=True) is True

    def test_get_bool_from_string(self):
        """Test get_bool with string values"""
        ConfigLoader.clear()
        ConfigLoader.load()

        # Test runtime set with string values
        ConfigLoader.set('test.bool_true', 'true')
        ConfigLoader.set('test.bool_false', 'false')
        ConfigLoader.set('test.bool_1', '1')
        ConfigLoader.set('test.bool_0', '0')

        assert ConfigLoader.get_bool('test.bool_true') is True
        assert ConfigLoader.get_bool('test.bool_false') is False
        assert ConfigLoader.get_bool('test.bool_1') is True
        assert ConfigLoader.get_bool('test.bool_0') is False

    def test_get_int(self, sample_config_file):
        """Test get_int for integer values"""
        config = ConfigLoader.load(config_path=sample_config_file)

        assert config.get_int('database.port') == 3306
        assert config.get_int('cache.redis.port') == 6379
        assert config.get_int('non.existent', default=1234) == 1234

    def test_get_list(self, sample_config_file):
        """Test get_list for list values"""
        config = ConfigLoader.load(config_path=sample_config_file)

        hosts = config.get_list('django.allowed_hosts')
        assert isinstance(hosts, list)
        assert 'example.com' in hosts
        assert 'test.com' in hosts

        # Test default
        assert config.get_list('non.existent', default=['default']) == ['default']

    def test_get_list_from_comma_separated_string(self):
        """Test get_list from comma-separated string"""
        ConfigLoader.clear()
        ConfigLoader.load()

        # Set comma-separated string
        ConfigLoader.set('test.hosts', 'host1,host2,host3')

        hosts = ConfigLoader.get_list('test.hosts')
        assert hosts == ['host1', 'host2', 'host3']

    def test_get_dict(self, sample_config_file):
        """Test get_dict for dictionary values"""
        config = ConfigLoader.load(config_path=sample_config_file)

        ttl_config = config.get_dict('cache.ttl')
        assert isinstance(ttl_config, dict)
        assert ttl_config['problem_list'] == 300
        assert ttl_config['problem_detail'] == 600

        # Test default
        assert config.get_dict('non.existent', default={'key': 'value'}) == {'key': 'value'}

    def test_env_var_override(self, sample_config_file, monkeypatch):
        """Test environment variable override"""
        config = ConfigLoader.load(config_path=sample_config_file)

        # Set environment variable
        monkeypatch.setenv('TEST_DB_HOST', 'env-override.com')

        # Env var should take precedence
        value = config.get('database.host', env_var='TEST_DB_HOST')
        assert value == 'env-override.com'

    def test_env_var_fallback(self, monkeypatch):
        """Test environment variable as fallback when config file doesn't exist"""
        ConfigLoader.clear()

        # Set environment variables
        monkeypatch.setenv('DB_HOST', 'env-db-host.com')
        monkeypatch.setenv('DB_PORT', '5432')
        monkeypatch.setenv('DEBUG', 'true')

        config = ConfigLoader.load(config_path='/non/existent/path.yaml')

        # Should fall back to env vars
        assert config.get('any.key', env_var='DB_HOST') == 'env-db-host.com'
        assert config.get_int('any.key', env_var='DB_PORT') == 5432
        assert config.get_bool('any.key', env_var='DEBUG') is True

    def test_reload_configuration(self, sample_config_file):
        """Test reload functionality"""
        config = ConfigLoader.load(config_path=sample_config_file)

        # Get initial value
        initial_value = config.get('django.secret_key')
        assert initial_value == 'test-secret-key'

        # Modify the config file
        new_config = {
            'django': {
                'secret_key': 'new-secret-key',
            }
        }

        with open(sample_config_file, 'w') as f:
            yaml.dump(new_config, f)

        # Reload configuration
        config = ConfigLoader.reload()

        # Should get new value
        new_value = config.get('django.secret_key')
        assert new_value == 'new-secret-key'

    def test_set_runtime_value(self):
        """Test setting configuration values at runtime"""
        ConfigLoader.clear()
        config = ConfigLoader.load()

        # Set values
        ConfigLoader.set('runtime.test_key', 'test_value')
        ConfigLoader.set('runtime.nested.key', 42)

        # Verify values
        assert config.get('runtime.test_key') == 'test_value'
        assert config.get('runtime.nested.key') == 42

    def test_get_all(self, sample_config_file):
        """Test get_all returns complete configuration"""
        config = ConfigLoader.load(config_path=sample_config_file)

        all_config = config.get_all()

        assert isinstance(all_config, dict)
        assert 'django' in all_config
        assert 'database' in all_config
        assert all_config['django']['secret_key'] == 'test-secret-key'

    def test_clear_cache(self, sample_config_file):
        """Test clearing cached configuration"""
        config = ConfigLoader.load(config_path=sample_config_file)

        # Verify loaded
        assert config.get('django.secret_key') == 'test-secret-key'

        # Clear cache
        ConfigLoader.clear()

        # Should need to reload
        config = ConfigLoader.load(config_path=sample_config_file)
        assert config.get('django.secret_key') == 'test-secret-key'

    def test_nested_key_access(self, sample_config_file):
        """Test accessing deeply nested configuration keys"""
        config = ConfigLoader.load(config_path=sample_config_file)

        # Deep nesting
        value = config.get('cache.ttl.problem_list')
        assert value == 300

        # Non-existent nested key
        value = config.get('cache.ttl.non_existent.very.deep', default='not_found')
        assert value == 'not_found'

    def test_empty_config_file(self):
        """Test loading empty configuration file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('')
            temp_path = f.name

        try:
            config = ConfigLoader.load(config_path=temp_path)

            # Should return default values
            assert config.get('any.key', default='default') == 'default'

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_malformed_yaml(self):
        """Test handling of malformed YAML file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('invalid: yaml: content: {[}')
            temp_path = f.name

        try:
            # Should handle error gracefully
            config = ConfigLoader.load(config_path=temp_path)

            # Should fall back to defaults
            assert config.get('any.key', default='default') == 'default'

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_default_path_priority(self, tmp_path):
        """Test default path priority"""
        ConfigLoader.clear()

        # Create config in different default locations
        config_dir = tmp_path / 'config'
        config_dir.mkdir()
        config_file = config_dir / 'config.yaml'

        config_data = {'test': {'key': 'value'}}
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Load with specific path
        config = ConfigLoader.load(config_path=str(config_file))
        assert config.get('test.key') == 'value'

    def test_config_file_env_var(self, sample_config_file, monkeypatch):
        """Test CONFIG_FILE environment variable"""
        ConfigLoader.clear()

        # Set CONFIG_FILE env var
        monkeypatch.setenv('CONFIG_FILE', sample_config_file)

        # Load without specifying path
        config = ConfigLoader.load()

        # Should load from CONFIG_FILE
        assert config.get('django.secret_key') == 'test-secret-key'


class TestConfigIntegration:
    """Integration tests for configuration in Django settings"""

    def test_settings_import(self):
        """Test that settings.py can import and use ConfigLoader"""
        from django.conf import settings

        # Verify settings are loaded
        assert hasattr(settings, 'SECRET_KEY')
        assert hasattr(settings, 'DATABASES')
        assert hasattr(settings, 'CACHES')

    def test_settings_cache_configuration(self):
        """Test cache configuration in settings"""
        from django.conf import settings

        # Verify CACHES is configured
        assert 'default' in settings.CACHES
        assert 'BACKEND' in settings.CACHES['default']

    def test_settings_database_configuration(self):
        """Test database configuration in settings"""
        from django.conf import settings

        # Verify DATABASES is configured
        assert 'default' in settings.DATABASES
        assert 'ENGINE' in settings.DATABASES['default']
        assert 'NAME' in settings.DATABASES['default']

    def test_settings_celery_configuration(self):
        """Test Celery configuration in settings"""
        from django.conf import settings

        # Verify Celery settings exist
        assert hasattr(settings, 'CELERY_BROKER_URL')
        assert hasattr(settings, 'CELERY_RESULT_BACKEND')
        assert hasattr(settings, 'CELERY_TASK_ROUTES')


class TestKubernetesConfigMap:
    """Tests for Kubernetes ConfigMap integration"""

    @pytest.fixture
    def k8s_config_file(self):
        """Simulate Kubernetes ConfigMap mount"""
        config_data = {
            'django': {
                'debug': False,
                'allowed_hosts': ['api.testcase.run', 'testcase.run'],
            },
            'database': {
                'host': 'mysql-service.default.svc.cluster.local',
                'port': 3306,
            },
            'cache': {
                'enable_redis': True,
                'redis': {
                    'host': 'redis-service.default.svc.cluster.local',
                },
            },
        }

        # Create temporary directory simulating /etc/algoitny/
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.yaml'

            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)

            yield str(config_path)

    def test_load_from_k8s_configmap(self, k8s_config_file):
        """Test loading configuration from Kubernetes ConfigMap mount"""
        ConfigLoader.clear()
        config = ConfigLoader.load(config_path=k8s_config_file)

        # Verify Kubernetes service DNS names
        assert config.get('database.host') == 'mysql-service.default.svc.cluster.local'
        assert config.get('cache.redis.host') == 'redis-service.default.svc.cluster.local'

    def test_k8s_secret_env_var_override(self, k8s_config_file, monkeypatch):
        """Test that Kubernetes Secrets (env vars) override ConfigMap"""
        ConfigLoader.clear()

        # Simulate Kubernetes Secret as env var
        monkeypatch.setenv('SECRET_KEY', 'k8s-secret-value')
        monkeypatch.setenv('DB_PASSWORD', 'k8s-db-password')

        config = ConfigLoader.load(config_path=k8s_config_file)

        # Env vars (from Secrets) should take precedence
        assert config.get('django.secret_key', env_var='SECRET_KEY') == 'k8s-secret-value'
        assert config.get('database.password', env_var='DB_PASSWORD') == 'k8s-db-password'


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_none_values(self):
        """Test handling of None values"""
        ConfigLoader.clear()
        ConfigLoader.load()

        ConfigLoader.set('test.none_value', None)

        # Should return default for None values
        assert ConfigLoader.get('test.none_value', default='default') == 'default'

    def test_empty_string_values(self):
        """Test handling of empty string values"""
        ConfigLoader.clear()
        ConfigLoader.load()

        ConfigLoader.set('test.empty_string', '')

        # Should return empty string, not default
        assert ConfigLoader.get('test.empty_string', default='default') == ''

    def test_numeric_string_conversion(self, monkeypatch):
        """Test automatic conversion of numeric strings from env vars"""
        ConfigLoader.clear()

        monkeypatch.setenv('TEST_INT', '42')
        monkeypatch.setenv('TEST_FLOAT', '3.14')
        monkeypatch.setenv('TEST_BOOL_TRUE', 'true')
        monkeypatch.setenv('TEST_BOOL_FALSE', 'false')

        config = ConfigLoader.load()

        # Should auto-convert from env vars
        assert config.get('any', env_var='TEST_INT') == 42
        assert config.get('any', env_var='TEST_FLOAT') == 3.14
        assert config.get('any', env_var='TEST_BOOL_TRUE') is True
        assert config.get('any', env_var='TEST_BOOL_FALSE') is False

    def test_list_with_empty_values(self):
        """Test list with empty values"""
        ConfigLoader.clear()
        ConfigLoader.load()

        ConfigLoader.set('test.list', 'value1,,value2,,')

        result = ConfigLoader.get_list('test.list')

        # Should filter out empty strings
        assert result == ['value1', 'value2']

    def test_concurrent_access(self, sample_config_file):
        """Test thread-safe access to configuration"""
        import threading

        config = ConfigLoader.load(config_path=sample_config_file)
        results = []

        def read_config():
            for _ in range(100):
                value = config.get('django.secret_key')
                results.append(value)

        # Create multiple threads
        threads = [threading.Thread(target=read_config) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # All reads should return the same value
        assert all(v == 'test-secret-key' for v in results)
        assert len(results) == 1000  # 10 threads * 100 reads
