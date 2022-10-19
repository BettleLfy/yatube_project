from django.shortcuts import render, get_object_or_404

from .models import Group, Post

POSTS_CNT = 10


def index(request):
    posts = Post.objects.select_related('author', 'group')[:POSTS_CNT]
    context = {
        'posts': posts,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.content.select_related('author')[:POSTS_CNT]
    context = {
        'group': group,
        'posts': posts,
    }
    return render(request, 'posts/group_list.html', context)
