from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(
            author=self.user,
            text='Тестовое описание поста')
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание')

    def test_urls_guest_client(self):
        """Проверка доступности URL для неавторизованного юзера."""
        pages = ('/',
                 f'/group/{self.group.slug}/',
                 f'/profile/{self.user.username}/',
                 f'/posts/{self.post.id}/')
        for page in pages:
            response = self.guest_client.get(page)
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_redirect_guest_client(self):
        """Проверка на редирект неавторизованного юзера."""
        url1 = '/auth/login/?next=/create/'
        url2 = f'/auth/login/?next=/posts/{self.post.id}/edit/'
        pages = {'/create/': url1,
                 f'/posts/{self.post.id}/edit/': url2}
        for page, value in pages.items():
            response = self.guest_client.get(page)
            self.assertRedirects(response, value)

    def test_urls_authorized_client(self):
        """Проверка доступности URL для авторизованного юзера."""
        pages = ('/create/',
                 f'/posts/{self.post.id}/edit/')
        for page in pages:
            response = self.authorized_client.get(page)
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """Проверка, что используются правильные шаблоны."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html'}

        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertTemplateUsed(response, template)

    def test_urls_404(self):
        """Проверка на 404, с заведомо несуществующей страницей."""
        page = '/unexisting_page/'
        response = self.guest_client.get(page)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
