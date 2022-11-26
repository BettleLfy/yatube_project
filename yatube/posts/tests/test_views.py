import tempfile
import shutil

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Follow, Post, Group
from ..forms import PostForm

POSTS_TO_CREATE = 20
AMOUNT_OF_POSTS = 10
PAGE_COUNT = 2
User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class ViewsTest(TestCase):
    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.user = User.objects.create_user(username='auth')
        self.user2 = User.objects.create_user(username='auth2')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(title='Тестовая группа',
                                          slug='test_group')
        self.post = Post.objects.create(text='Тестовый текст',
                                        group=self.group,
                                        author=self.user)

    def test_correct_page_amount(self):
        """Проверка количества постов на первой и второй страницах."""
        bilk_post = [Post(text=f'Тестовый текст {text_num}',
                          group=self.group,
                          author=self.user)
                     for text_num in range(POSTS_TO_CREATE)]
        Post.objects.bulk_create(bilk_post)
        pages = (reverse('posts:index'),
                 reverse('posts:profile',
                         kwargs={'username': self.user.username}),
                 reverse('posts:group_list',
                         kwargs={'slug': self.group.slug}))
        for page in pages:
            for page_num in range(1, PAGE_COUNT + 1):
                response = self.authorized_client.get(page, {'page': page_num})
                count_posts = len(response.context['page_obj'])
                self.assertEqual(count_posts, AMOUNT_OF_POSTS)

    def test_views_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug':
                            f'{self.group.slug}'}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username':
                            f'{self.user.username}'}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id':
                            self.post.id}): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id':
                            self.post.id}): 'posts/create_post.html'}
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertTemplateUsed(response, template)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        post_text_0 = {response.context['post'].text: 'Тестовый пост',
                       response.context['post'].group: self.group,
                       response.context['post'].author: self.user.username}
        for value, expected in post_text_0.items():
            self.assertEqual(post_text_0[value], expected)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField}
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_added_correctly(self):
        """Пост при создании добавлен корректно."""
        cache.clear()
        post = Post.objects.create(
            text='Тестовый текст проверка как добавился',
            author=self.user,
            group=self.group)
        response_index = self.authorized_client.get(
            reverse('posts:index'))
        response_group = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': f'{self.group.slug}'}))
        response_profile = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'}))
        index = response_index.context['page_obj']
        group = response_group.context['page_obj']
        profile = response_profile.context['page_obj']
        self.assertIn(post, index)
        self.assertIn(post, group)
        self.assertIn(post, profile)

    def test_post_added_correctly_user2(self):
        """Пост при создании не добавляется другому пользователю
           Но виден на главной и в группе."""
        group2 = Group.objects.create(title='Тестовая группа 2',
                                      slug='test_group2')
        posts_count = Post.objects.filter(group=self.group).count()
        post = Post.objects.create(
            text='Тестовый пост от другого автора',
            author=self.user2,
            group=group2)
        response_profile = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'}))
        group = Post.objects.filter(group=self.group).count()
        profile = response_profile.context['page_obj']
        self.assertEqual(group, posts_count)
        self.assertNotIn(post, profile)

    def test_cache(self):
        response = self.authorized_client.get(
            reverse('posts:index'))
        with_cache = response.content
        self.post.delete()
        response = self.authorized_client.get(
            reverse('posts:index'))
        after_deleting_post = response.content
        cache.clear()
        response = response = self.authorized_client.get(
            reverse('posts:index'))
        after_clearing_cache = response.content
        self.assertEqual(with_cache, after_deleting_post)
        self.assertNotEqual(after_deleting_post, after_clearing_cache)


class FollowPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.un_subscriber = User.objects.create_user(username='un_subscriber')
        cls.subscriber = User.objects.create_user(username='follower')
        cls.author = User.objects.create_user(username='following')
        cls.subscriber_2 = User.objects.create_user(
            username='subscriber_2')
        cls.follow = Follow.objects.create(
            user=cls.subscriber,
            author=cls.author,
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.subscriber)
        self.subscriber_2_client = Client()
        self.subscriber_2_client.force_login(self.subscriber_2)
        cache.clear()

    def test_auth_user_follow(self):
        """Проверка, что авторизованный пользователь может подписываться
        на других пользователей и удалять их из подписок."""
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.author})
        )
        self.assertTrue(Follow.objects.filter(
            user=self.subscriber,
            author=self.author,
        ).exists())

    def test_unfollow_post_delete(self):
        self.authorized_client.get(
            reverse('posts:profile_unfollow', kwargs={'username': self.author})
        )
        post = Post.objects.create(author=self.author)
        response = self.authorized_client.get(reverse(
            'posts:follow_index'))
        self.assertNotIn(post, response.context['page_obj'])

    def test_follow_page_follower(self):
        """Проверка, что посты появляются по подписке."""
        response = self.authorized_client.get(reverse(
            'posts:follow_index'
        ))
        follower_posts_cnt = len(response.context['page_obj'])
        self.assertEqual(follower_posts_cnt, 1)
        post = Post.objects.get(id=self.post.pk)
        self.assertIn(post, response.context['page_obj'])

    def test_follow_page_unfollower_2(self):
        """Проверка, что посты не появляются если не подписан."""
        response = self.subscriber_2_client.get(reverse(
            'posts:follow_index'))
        posts_cnt_new = len(response.context['page_obj'].object_list)
        self.assertEqual(posts_cnt_new, 0)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostImageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='testslug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded
        )
        cls.post_id = cls.post.pk
        cls.post_without_group = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            image=cls.uploaded,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostImageTests.user)
        cache.clear()

    def test_image_context(self):
        """URL-адрес использует соответствующий шаблон с картинкой."""
        list = (
            reverse('posts:index'),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.user.username}),
        )
        for page_number in list:
            with self.subTest(page_number=page_number):
                response = self.authorized_client.get(page_number)
                self.assertTrue(response.context['page_obj'][0].image)

    def test_post_detail_show_image(self):
        """Шаблон post_detail сформирован с картинкой."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context['post'].image, self.post.image)
