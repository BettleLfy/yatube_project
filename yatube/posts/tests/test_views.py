from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from django.core.cache import cache

from ..models import Follow, Post, Group

POSTS_TO_CREATE = 20
AMOUNT_OF_POSTS = 10
PAGE_COUNT = 2
User = get_user_model()


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
        bilk_post = [Post(text=f'Тестовый текст {text_num}',
                          group=self.group,
                          author=self.user)
                     for text_num in range(POSTS_TO_CREATE)]
        Post.objects.bulk_create(bilk_post)

    def test_correct_page_amount(self):
        """Проверка количества постов на первой и второй страницах."""
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
