from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from core.models import Character, Comic, Tag, User


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(username='admin', password='password')
        cls.character = Character.objects.create(name='Trollface')
        cls.tag = Tag.objects.create(name='Work')
        cls.comic = Comic.objects.create(
            title='A comic', image='comics/test.png', panel_count=4, creator_credit='Artist'
        )
        cls.comic.characters.add(cls.character)
        cls.comic.tags.add(cls.tag)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_all_models_are_available_in_admin(self):
        for model in ('comic', 'character', 'tag', 'user'):
            with self.subTest(model=model):
                self.assertEqual(self.client.get(reverse(f'admin:core_{model}_changelist')).status_code, 200)

    def test_comic_list_search_and_filters(self):
        url = reverse('admin:core_comic_changelist')
        response = self.client.get(url)
        self.assertContains(response, 'A comic')
        self.assertContains(response, '4')
        self.assertNotContains(response, 'Artist')
        for query in ('comic', 'Artist'):
            with self.subTest(query=query):
                self.assertContains(self.client.get(url, {'q': query}), 'A comic')
        for parameter, value in (
            ('characters__id__exact', self.character.pk),
            ('tags__id__exact', self.tag.pk),
        ):
            with self.subTest(parameter=parameter):
                self.assertContains(self.client.get(url, {parameter: value}), 'A comic')

    def test_character_and_tag_search(self):
        for model, name in (('character', 'Trollface'), ('tag', 'Work')):
            with self.subTest(model=model):
                url = reverse(f'admin:core_{model}_changelist')
                self.assertContains(self.client.get(url, {'q': name}), name)
                self.assertNotContains(self.client.get(url, {'q': 'no match'}), name)

    def test_comic_form_and_assignments(self):
        url = reverse('admin:core_comic_change', args=[self.comic.pk])
        response = self.client.get(url)
        self.assertContains(response, 'data-ajax--url')
        self.assertContains(response, 'Creator credit')
        self.assertNotContains(response, 'name="slug"')
        response = self.client.post(url, {
            'title': 'Updated comic',
            'panel_count': '2',
            'creator_credit': 'Known artist',
            'characters': [self.character.pk],
            'tags': [self.tag.pk],
        })
        if response.status_code != 302:
            self.fail(str(response.context['adminform'].form.errors))
        self.comic.refresh_from_db()
        self.assertEqual(self.comic.title, 'Updated comic')
        self.assertEqual(self.comic.creator_credit, 'Known artist')
        self.assertEqual(self.comic.image.name, 'comics/test.png')
        self.assertEqual(list(self.comic.characters.all()), [self.character])
        self.assertEqual(list(self.comic.tags.all()), [self.tag])

    def test_staff_need_model_permissions(self):
        staff = User.objects.create_user(username='staff', password='password', is_staff=True)
        self.client.force_login(staff)
        url = reverse('admin:core_comic_changelist')
        self.assertEqual(self.client.get(url).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(codename='view_comic'))
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:core_comic_add')).status_code, 403)
