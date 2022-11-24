import tempfile
import shutil

from http import HTTPStatus
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from posts.models import Comment, Post, Group

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(title='Тестовая группа',
                                          slug='test-group',
                                          description='Описание')
        self.post = Post.objects.create(
            text='Тестовый пост',
            author=self.user
        )
        self.comment = Comment.objects.create(
            author=self.user,
            text='Текст комментария',
            post=self.post
        )

    def tearDown(self):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Проверка создания поста."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {'text': 'Текст записанный в форму',
                     'group': self.group.id,
                     'image': uploaded,
                     }
        response = self.authorized_client.post(reverse('posts:post_create'),
                                               data=form_data,
                                               follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(Post.objects.filter(
                        text='Текст записанный в форму',
                        group=self.group.id,
                        author=self.user,
                        image__isnull=False,
                        ).exists())
        self.assertEqual(Post.objects.count(),
                         posts_count + 1)

    def test_can_edit_post(self):
        """Проверка прав редактирования."""
        self.post = Post.objects.create(text='Тестовый текст',
                                        author=self.user,
                                        group=self.group)
        old_text = self.post
        self.group2 = Group.objects.create(title='Тестовая группа2',
                                           slug='test-group2',
                                           description='Описание')
        form_data = {'text': 'Текст записанный в форму',
                     'group': self.group2.id}
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': old_text.id}),
            data=form_data,
            follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(Post.objects.filter(
                        group=self.group2.id,
                        author=self.user,
                        pub_date=self.post.pub_date
                        ).exists())
        self.assertNotEqual(old_text.text, form_data['text'])
        self.assertNotEqual(old_text.group, form_data['group'])

    def test_reddirect_guest_client(self):
        """Проверка редиректа неавторизованного пользователя."""
        self.post = Post.objects.create(text='Тестовый текст',
                                        author=self.user,
                                        group=self.group)
        form_data = {'text': 'Текст записанный в форму'}
        response = self.guest_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response,
                             f'/auth/login/?next=/posts/{self.post.id}/edit/')

    def test_no_edit_post(self):
        """Проверка запрета редактирования не авторизованного пользователя."""
        posts_count = Post.objects.count()
        form_data = {'text': 'Текст записанный в форму',
                     'group': self.group.id}
        response = self.guest_client.post(reverse('posts:post_create'),
                                          data=form_data,
                                          follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotEqual(Post.objects.count(), posts_count + 1)

    def test_comments_added_successfully_by_authorized_user(self):
        """Проверка, что авторизованный пользователь может добавлять
        комментарий."""
        comments_count = Comment.objects.count()
        post_id = self.post.pk
        form_data = {
            'text': 'Тестовый комментарий 2'
        }
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post_id}),
            data=form_data
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)

    def test_guest_comment_add(self):
        """Проверка что гостевой пользователь не может добавить
        комментарий."""
        comments_count = Comment.objects.count()
        post_id = self.post.pk
        form_data = {
            'text': 'Тестовый комментарий 2'
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post_id}),
            data=form_data
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(response,
                             f'/auth/login/?next=/posts/'
                             f'{post_id}/comment/')
