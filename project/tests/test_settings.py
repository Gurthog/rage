import os
import runpy
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings


class SecurityConfigurationTests(SimpleTestCase):
    def test_production_requires_a_nonempty_secret_key(self):
        for value in (None, ''):
            with self.subTest(value=value), patch.dict(os.environ, {}, clear=True), patch('dotenv.load_dotenv'):
                if value is not None:
                    os.environ['DJANGO_SECRET_KEY'] = value
                with self.assertRaisesMessage(ImproperlyConfigured, 'DJANGO_SECRET_KEY must be set'):
                    runpy.run_path(str(Path(__file__).resolve().parent.parent / 'settings.py'))

    def test_debug_can_use_a_temporary_secret_key(self):
        with patch.dict(os.environ, {'DJANGO_DEBUG': 'true'}, clear=True), patch('dotenv.load_dotenv'):
            config = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'settings.py'))
        self.assertTrue(config['SECRET_KEY'])
        self.assertNotIn('SECURE_SSL_REDIRECT', config)

    def test_production_uses_configured_secret_and_redirects_http(self):
        with patch.dict(os.environ, {'DJANGO_SECRET_KEY': 'configured-secret'}, clear=True), patch('dotenv.load_dotenv'):
            config = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'settings.py'))
        self.assertEqual(config['SECRET_KEY'], 'configured-secret')
        self.assertTrue(config['SECURE_SSL_REDIRECT'])
        with override_settings(
            ALLOWED_HOSTS=['testserver'],
            MIDDLEWARE=['django.middleware.security.SecurityMiddleware'],
            SECURE_SSL_REDIRECT=config['SECURE_SSL_REDIRECT'],
            SECURE_PROXY_SSL_HEADER=config['SECURE_PROXY_SSL_HEADER'],
        ):
            response = self.client.get('/')
            self.assertEqual(response.status_code, 301)
            self.assertEqual(response['Location'], 'https://testserver/')
            self.assertEqual(self.client.get('/', HTTP_X_FORWARDED_PROTO='https').status_code, 200)


class StaticConfigurationTests(SimpleTestCase):
    def test_static_share_is_optional(self):
        for value in (None, ''):
            with self.subTest(value=value), patch.dict(os.environ, {'DJANGO_SECRET_KEY': 'test-secret'}, clear=True), patch('dotenv.load_dotenv'):
                if value is not None:
                    os.environ['STATIC_SHARE'] = value
                config = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'settings.py'))
                self.assertEqual(config['STATICFILES_DIRS'], [config['BASE_DIR'] / 'project' / 'static'])

    def test_static_share_is_a_staticfiles_directory(self):
        with patch.dict(os.environ, {'STATIC_SHARE': '/tmp/static-share', 'DJANGO_SECRET_KEY': 'test-secret'}, clear=True), patch('dotenv.load_dotenv'):
            config = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'settings.py'))
        self.assertEqual(
            config['STATICFILES_DIRS'],
            [config['BASE_DIR'] / 'project' / 'static', Path('/tmp/static-share')],
        )


class MediaConfigurationTests(TestCase):
    def test_media_has_a_separate_local_default(self):
        self.assertTrue(settings.MEDIA_ROOT)
        self.assertNotEqual(settings.MEDIA_ROOT, settings.STATIC_ROOT)
        self.assertNotEqual(settings.MEDIA_URL, settings.STATIC_URL)
