from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404

from .models import Group, Post, User
from .forms import PostForm
from .utils import paginator


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
    context = {
        'count': count,
        'author': author,
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
    context = {
        'post': post,
        'post_title': post_title,
        'author': author,
        'author_posts': author_posts,
        'pub_date': pub_date,
    }
    template = 'posts/post_detail.html'
    return render(request, template, context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None)
    if request.method != "GET":
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
    form = PostForm(request.POST or None, instance=post)
    template = 'posts/create_post.html'
    if request.user == author:
        if request.method == 'POST' and form.is_valid:
            post = form.save()
            return redirect('posts:post_detail', post_id)
        context = {
            'form': form,
            'post': post,
            'groups': groups,
        }
        return render(request, template, context)
    return redirect('posts:post_detail', post_id)
