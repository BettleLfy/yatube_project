from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.cache import cache_page
from django.urls import reverse

from .models import Follow, Group, Post, User
from .forms import CommentForm, PostForm
from .utils import paginator


@cache_page(20, key_prefix='index_page')
def index(request):
    context = paginator(Post.objects.all(), request)
    template = 'posts/index.html'
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.content.all()
    context = {
        'group': group,
        'posts': posts,
    }
    context.update(paginator(group.content.all(), request))
    template = 'posts/group_list.html'
    return render(request, template, context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    count = author.posts.count()
    following = request.user.is_authenticated and author.following.filter(
        user=request.user).exists()
    context = {
        'count': count,
        'author': author,
        'following': following
    }
    context.update(paginator(author.posts.all(), request))
    template = 'posts/profile.html'
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    pub_date = post.pub_date
    post_title = post.text[:30]
    author = post.author
    author_posts = author.posts.all().count()
    comments = post.comments.all()
    form = CommentForm()
    context = {
        'post': post,
        'post_title': post_title,
        'author': author,
        'author_posts': author_posts,
        'pub_date': pub_date,
        'form': form,
        'comments': comments
    }
    template = 'posts/post_detail.html'
    return render(request, template, context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None,
                    files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=request.user.username)
    groups = Group.objects.all()
    template = 'posts/create_post.html'
    context = {'form': form, 'groups': groups}
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    author = post.author
    groups = Group.objects.all()
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post)
    template = 'posts/create_post.html'
    if request.user != author:
        return redirect('posts:post_detail', post_id)
    if request.method == 'POST' and form.is_valid():
        post = form.save()
        return redirect('posts:post_detail', post_id)
    context = {
        'form': form,
        'post': post,
        'groups': groups,
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    context = paginator(post_list, request)
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    following = Follow.objects.filter(user=user, author=author)
    if user != author and not following.exists():
        Follow.objects.create(user=user, author=author)
    return redirect(
        reverse(
            'posts:profile',
            kwargs={'username': author.username}
        )
    )


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    following = Follow.objects.filter(user=user, author=author)
    if user != author and following.exists():
        following.delete()
    return redirect(
        reverse(
            'posts:profile',
            kwargs={'username': author.username}
        )
    )
