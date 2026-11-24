from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class AccountAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(username='admin', password='password')
        cls.group = Group.objects.create(name='Moderators')

    def app_models(self, response, label):
        app = next((app for app in response.context['app_list'] if app['app_label'] == label), None)
        return {model['object_name'] for model in app['models']} if app else set()

    def test_superuser_sees_accounts_together(self):
        self.client.force_login(self.admin)
        for url in (reverse('admin:index'), reverse('admin:app_list', args=['accounts'])):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(self.app_models(response, 'accounts'), {'User', 'Group'})
                self.assertNotContains(response, 'Authentication and Authorization')
        self.assertEqual(self.client.get(reverse('admin:accounts_user_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:auth_group_changelist')).status_code, 200)

    def test_group_only_staff_can_navigate_accounts_without_user_access(self):
        staff = User.objects.create_user(username='groupstaff', password='password', is_staff=True)
        staff.user_permissions.add(Permission.objects.get(content_type__app_label='auth', codename='view_group'))
        self.client.force_login(staff)
        for url in (reverse('admin:index'), reverse('admin:app_list', args=['accounts'])):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.app_models(response, 'accounts'), {'Group'})
                self.assertNotContains(response, 'Authentication and Authorization')
        self.assertEqual(self.client.get(reverse('admin:auth_group_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:accounts_user_changelist')).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin:auth_group_add')).status_code, 403)
        self.assertRedirects(self.client.get(reverse('admin:app_list', args=['auth'])), reverse('admin:app_list', args=['accounts']))

    def test_user_only_and_unprivileged_staff(self):
        staff = User.objects.create_user(username='userstaff', password='password', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse('admin:app_list', args=['accounts'])).status_code, 404)
        staff.user_permissions.add(Permission.objects.get(content_type__app_label='accounts', codename='view_user'))
        response = self.client.get(reverse('admin:app_list', args=['accounts']))
        self.assertEqual(self.app_models(response, 'accounts'), {'User'})
        self.assertEqual(self.client.get(reverse('admin:auth_group_changelist')).status_code, 403)

    def test_group_pages_use_accounts_breadcrumb(self):
        self.client.force_login(self.admin)
        for name, args in (
            ('admin:auth_group_changelist', []),
            ('admin:auth_group_add', []),
            ('admin:auth_group_change', [self.group.pk]),
            ('admin:auth_group_history', [self.group.pk]),
            ('admin:auth_group_delete', [self.group.pk]),
        ):
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=args))
                self.assertContains(response, f'href="{reverse("admin:app_list", args=["accounts"])}">Accounts</a>')
                self.assertNotContains(response, '>Authentication and Authorization</a>')

    def test_group_bulk_delete_uses_accounts_breadcrumb(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('admin:auth_group_changelist'), {
            'action': 'delete_selected',
            '_selected_action': [self.group.pk],
        })
        self.assertContains(response, f'href="{reverse("admin:app_list", args=["accounts"])}">Accounts</a>')
        self.assertNotContains(response, 'Authentication and Authorization')
