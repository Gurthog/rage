from django.contrib.admin.apps import AdminConfig
from django.contrib.admin.sites import AdminSite
from django.shortcuts import redirect
from django.urls import reverse


class RageAdminSite(AdminSite):
    site_header = 'RAGE ADMINISTRATION'
    site_title = 'Rage'

    def get_app_list(self, request, app_label=None):
        from django.contrib.auth.models import Group

        # Group is still auth.Group; only its navigation section changes.
        if app_label not in (None, 'accounts'):
            return super().get_app_list(request, app_label)

        apps = super().get_app_list(request)
        accounts = next((app for app in apps if app['app_label'] == 'accounts'), None)
        auth = next((app for app in apps if app['app_label'] == 'auth'), None)
        groups = [model for model in auth['models'] if model['model'] is Group] if auth else []
        if groups:
            if accounts is None:
                accounts = {
                    'name': 'Accounts',
                    'app_label': 'accounts',
                    'app_url': reverse('admin:app_list', kwargs={'app_label': 'accounts'}, current_app=self.name),
                    'has_module_perms': True,
                    'models': [],
                }
                apps.append(accounts)
            accounts['models'].extend(groups)
            accounts['models'].sort(key=lambda model: model['name'].lower())
            auth['models'] = [model for model in auth['models'] if model['model'] is not Group]
            if not auth['models']:
                apps.remove(auth)

        if app_label == 'accounts':
            return [accounts] if accounts else []
        return sorted(apps, key=lambda app: app['name'].lower())

    def app_index(self, request, app_label, extra_context=None):
        if app_label == 'auth':
            return redirect('admin:app_list', app_label='accounts')
        return super().app_index(request, app_label, extra_context)


class RageAdminConfig(AdminConfig):
    default_site = 'project.admin.RageAdminSite'
