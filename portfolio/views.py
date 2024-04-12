from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.views import View
from django.core.paginator import Paginator

from portfolio.models import Post


class Index(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            "index.html",
            {
                "last_post": Post.objects.filter(is_public=True)
                .order_by("-created_at")
                .first()
            },
        )


class AllPosts(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            "all_posts.html",
            {
                "query": (query := request.GET.get("query")),
                "posts": Paginator(
                    (
                        Post.objects.filter(is_public=True, title__icontains=query)
                        | Post.objects.filter(
                            is_public=True, tags__name__icontains=query
                        )
                        if query is not None
                        else Post.objects.filter(is_public=True)
                    )
                    .distinct()
                    .order_by("-created_at"),
                    4,
                ).get_page(request.GET.get("page")),
            },
        )


class SinglePost(View):
    def get(self, request: HttpRequest, **kwargs: str) -> HttpResponse:
        return render(
            request,
            "single_post.html",
            {
                "post": get_object_or_404(
                    Post, slug=kwargs.get("post_slug"), is_public=True
                )
            },
        )


class NotFoundError(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "404.html", status=404)
