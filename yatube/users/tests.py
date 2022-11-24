from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()


class UsersURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_for_guest_users(self):
        pages = (
            '/auth/login/',
            '/auth/signup/',
            '/auth/password_reset/',
            '/auth/password_reset/done/',
            '/auth/reset/<id64>/<token>/',
            '/auth/reset/done/')
        for page in pages:
            response = self.guest_client.get(page)
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_for_loggined_users(self):
        pages = ('/auth/password_change/',
                 '/auth/password_change/done/',
                 '/auth/logout/')
        for page in pages:
            response = self.authorized_client.get(page)
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_templates_for_users(self):
        templates_url_names = {
            '/auth/login/': 'users/login.html',
            '/auth/signup/': 'users/signup.html',
            '/auth/password_reset/': 'users/password_reset_form.html',
            '/auth/password_reset/done/': 'users/password_reset_done.html',
            '/auth/reset/<id64>/<token>/': 'users/password_reset_confirm.html',
            '/auth/reset/done/': 'users/password_reset_complete.html',
            '/auth/password_change/': 'users/password_change_form.html',
            '/auth/password_change/done/': 'users/password_change_done.html',
            '/auth/logout/': 'users/logged_out.html'
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertTemplateUsed(response, template)
