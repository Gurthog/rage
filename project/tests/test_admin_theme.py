from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.test import TestCase
from django.urls import reverse


class AdminThemeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(username='admin', password='password')

    def assert_branded(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'RAGE ADMINISTRATION')
        self.assertContains(response, ' | Rage</title>', html=False)
        self.assertContains(response, static('project/admin-theme.css'))
        self.assertContains(response, 'theme-toggle')
        self.assertNotContains(response, 'Django administration')

    def test_login_has_branding_and_theme(self):
        response = self.client.get(reverse('admin:login'))
        self.assert_branded(response)
        self.assertContains(response, 'BOTTOM TEXT', count=1)
        self.assertLess(response.content.index(b'</form>'), response.content.index(b'BOTTOM TEXT'))

    def test_invalid_login_keeps_bottom_text(self):
        response = self.client.post(reverse('admin:login'), {'username': 'admin', 'password': 'wrong'})
        self.assertContains(response, 'BOTTOM TEXT', count=1)

    def test_admin_pages_have_branding_and_theme(self):
        self.client.force_login(self.admin)
        for url in (
            reverse('admin:index'),
            reverse('admin:accounts_user_changelist'),
            reverse('admin:accounts_user_change', args=[self.admin.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assert_branded(response)
                self.assertNotContains(response, 'BOTTOM TEXT')
        self.assertContains(self.client.get(reverse('admin:index')), 'Site administration')

    def test_logout_has_branding_and_theme(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('admin:logout'))
        self.assert_branded(response)
        self.assertNotContains(response, 'BOTTOM TEXT')

    def test_theme_stylesheet_is_available_to_staticfiles(self):
        self.assertIsNotNone(finders.find('project/admin-theme.css'))
