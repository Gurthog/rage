import base64
import os
import runpy
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from core.models import Character, Comic, Tag


class SecurityConfigurationTests(SimpleTestCase):
    def test_production_requires_a_nonempty_secret_key(self):
        for value in (None, ''):
            with self.subTest(value=value), patch.dict(os.environ, {}, clear=True), patch('dotenv.load_dotenv'):
                if value is not None:
                    os.environ['DJANGO_SECRET_KEY'] = value
                with self.assertRaisesMessage(ImproperlyConfigured, 'DJANGO_SECRET_KEY must be set'):
                    runpy.run_path(str(Path(__file__).resolve().parent.parent / 'project/settings.py'))

    def test_debug_can_use_a_temporary_secret_key(self):
        with patch.dict(os.environ, {'DJANGO_DEBUG': 'true'}, clear=True), patch('dotenv.load_dotenv'):
            config = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'project/settings.py'))
        self.assertTrue(config['SECRET_KEY'])
        self.assertNotIn('SECURE_SSL_REDIRECT', config)

    def test_production_uses_configured_secret_and_redirects_http(self):
        with patch.dict(os.environ, {'DJANGO_SECRET_KEY': 'configured-secret'}, clear=True), patch('dotenv.load_dotenv'):
            config = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'project/settings.py'))
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
                config = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'project/settings.py'))
                self.assertNotIn('STATICFILES_DIRS', config)

    def test_static_share_is_a_staticfiles_directory(self):
        with patch.dict(os.environ, {'STATIC_SHARE': '/tmp/static-share', 'DJANGO_SECRET_KEY': 'test-secret'}, clear=True), patch('dotenv.load_dotenv'):
            config = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'project/settings.py'))
        self.assertEqual(config['STATICFILES_DIRS'], [Path('/tmp/static-share')])


class MediaConfigurationTests(TestCase):
    def test_media_has_a_separate_local_default(self):
        self.assertTrue(settings.MEDIA_ROOT)
        self.assertNotEqual(settings.MEDIA_ROOT, settings.STATIC_ROOT)
        self.assertNotEqual(settings.MEDIA_URL, settings.STATIC_URL)


class ComicValidationTests(TestCase):
    def test_comic_string_representation_is_its_title(self):
        self.assertEqual(str(Comic(title='A comic')), 'A comic')

    def test_title_and_image_are_required(self):
        comic = Comic()
        with self.assertRaises(ValidationError) as error:
            comic.full_clean()
        self.assertIn('title', error.exception.message_dict)
        self.assertIn('image', error.exception.message_dict)
        with self.assertRaises(ValidationError) as error:
            Comic(title='   ', image='comics/test.png').full_clean()
        self.assertIn('title', error.exception.message_dict)

    def test_original_image_can_be_replaced_without_inferring_provenance(self):
        original = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+'
            'lL1sAAAAASUVORK5CYII='
        )
        replacement = original + b'preserved trailing data'
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            comic = Comic(
                title='A comic',
                image=SimpleUploadedFile('original.png', original, content_type='image/png'),
                found_at='https://example.com/first-copy',
            )
            comic.full_clean()
            comic.save()
            comic.image.open('rb')
            self.assertEqual(comic.image.read(), original)
            comic.image.close()
            identifier = comic.pk
            comic.image = SimpleUploadedFile('better.png', replacement, content_type='image/png')
            comic.save()
            comic.refresh_from_db()
            self.assertEqual(comic.pk, identifier)
            comic.image.open('rb')
            self.assertEqual(comic.image.read(), replacement)
            comic.image.close()
            self.assertEqual(comic.found_at, 'https://example.com/first-copy')
            comic.found_at = 'https://example.com/better-copy'
            comic.save()
            comic.refresh_from_db()
            self.assertEqual(comic.found_at, 'https://example.com/better-copy')
            comic.found_at = ''
            comic.save()
            comic.refresh_from_db()
            self.assertEqual(comic.found_at, '')

    def test_metadata_can_be_recorded_independently(self):
        comic = Comic.objects.create(title='Anonymous', image='comics/test.png')
        comic.full_clean()
        self.assertFalse(comic.creator_credit)
        self.assertFalse(comic.found_at)
        comic.creator_credit = 'Known artist'
        comic.found_at = 'https://example.com/repost'
        comic.full_clean()
        comic.save()
        comic.refresh_from_db()
        self.assertEqual(comic.creator_credit, 'Known artist')
        self.assertEqual(comic.found_at, 'https://example.com/repost')
        comic.found_at = ''
        comic.save()
        comic.refresh_from_db()
        self.assertEqual(comic.creator_credit, 'Known artist')
        self.assertFalse(comic.found_at)

    def test_panel_count_can_be_unknown_but_must_be_positive(self):
        for count in (None, 1, 4):
            comic = Comic(title='A comic', image='comics/test.png', panel_count=count)
            comic.full_clean()
        for count in (0, -1):
            comic = Comic(title='A comic', image='comics/test.png', panel_count=count)
            with self.assertRaises(ValidationError) as error:
                comic.full_clean()
            self.assertIn('panel_count', error.exception.message_dict)

    def test_characters_and_tags_can_be_reused_edited_and_combined(self):
        first = Comic.objects.create(title='One', image='comics/one.png', panel_count=4)
        second = Comic.objects.create(title='Two', image='comics/two.png', panel_count=2)
        troll = Character.objects.create(name='Trollface')
        alone = Character.objects.create(name='Forever Alone')
        work = Tag.objects.create(name='Work')
        school = Tag.objects.create(name='School')
        first.characters.add(troll, alone)
        first.tags.add(work, school)
        second.characters.add(troll)
        second.tags.add(work)
        self.assertEqual(set(troll.comics.all()), {first, second})
        self.assertEqual(set(work.comics.all()), {first, second})
        self.assertEqual(list(Comic.objects.filter(characters=troll, tags=work, panel_count=4)), [first])
        first.characters.remove(alone)
        first.tags.set([school])
        self.assertEqual(set(first.characters.all()), {troll})
        self.assertEqual(set(first.tags.all()), {school})

    def test_identifiers_are_unique_and_stable(self):
        first = Comic.objects.create(title='Same title', image='comics/one.png')
        second = Comic.objects.create(title='Same title', image='comics/two.png')
        unfriendly = Comic.objects.create(title='!!!', image='comics/three.png')
        other_unfriendly = Comic.objects.create(title='???', image='comics/four.png')
        identifiers = {first.slug, second.slug, unfriendly.slug, other_unfriendly.slug}
        self.assertEqual(len(identifiers), 4)
        self.assertTrue(all(identifiers))
        self.assertTrue(first.slug.startswith('same-title-'))
        identifier = first.slug
        first.title = 'A new title'
        first.save()
        first.refresh_from_db()
        self.assertEqual(first.slug, identifier)
