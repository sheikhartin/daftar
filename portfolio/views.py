import json
import string
from typing import Union, Any, Callable

from django.shortcuts import redirect, render, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseForbidden
from django.views import View
from django.db.models import Count, Q
from django.core.paginator import Paginator

from portfolio.models import Tag, Post, Comment


def superuser_required(
    view_func: Callable[..., Union[HttpResponse, HttpResponseForbidden]],
) -> Callable[..., Union[HttpResponse, HttpResponseForbidden]]:
    def _wrapped_view(
        request: View,
        *args: Any,
        **kwargs: Any,
    ) -> Union[HttpResponse, HttpResponseForbidden]:
        if not request.request.user.is_superuser:
            return HttpResponseForbidden(
                "You must be a superuser to perform this action."
            )
        return view_func(request, *args, **kwargs)

    return _wrapped_view


class Index(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            "index.html",
            {
                "last_post": Post.objects.filter(is_public=True)
                .order_by("-created_at")
                .first(),
                "has_permission": request.user.is_superuser,
                "posts_with_unread_comments": Post.objects.annotate(
                    unread_comments_count=Count(
                        "comments", filter=Q(comments__viewed=False)
                    )
                ).filter(unread_comments_count__gt=0),
            },
        )


class AllPosts(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        posts = (
            Post.objects.all()
            if request.user.is_superuser
            else Post.objects.filter(is_public=True)
        )
        return render(
            request,
            "all_posts.html",
            {
                "query": (query := request.GET.get("query")),
                "posts": Paginator(
                    (
                        posts.filter(
                            Q(title__icontains=query) | Q(tags__name__icontains=query)
                        )
                        if query is not None
                        else posts
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
                "post": (
                    post := (
                        get_object_or_404(Post, slug=kwargs.get("post_slug"))
                        if request.user.is_superuser
                        else get_object_or_404(
                            Post, slug=kwargs.get("post_slug"), is_public=True
                        )
                    )
                ),
                "comments": post.comments.all().order_by("-timestamp"),
                "has_permission": request.user.is_superuser,
            },
        )

    def post(
        self,
        request: HttpRequest,
        **kwargs: str,
    ) -> Union[HttpResponse, JsonResponse]:
        if "like_comment_id" in request.POST:
            comment = get_object_or_404(
                Comment, id=(comment_id := request.POST.get("like_comment_id"))
            )
            comment.likes += 1
            comment.save(update_fields=["likes"])
            return JsonResponse(
                {
                    "status": "success",
                    "action": "like",
                    "comment_id": comment_id,
                    "likes": comment.likes,
                }
            )
        Comment.objects.create(
            content=request.POST.get("comment_content").strip(),
            name=request.POST.get("comment_name").strip(),
            email=request.POST.get("comment_email").strip(),
            post=(
                get_object_or_404(Post, slug=kwargs.get("post_slug"), is_public=True)
                if not request.user.is_staff or not request.user.is_superuser
                else get_object_or_404(Post, slug=kwargs.get("post_slug"))
            ),
            is_admin_comment=request.user.is_staff or request.user.is_superuser,
        )
        return redirect("single_post", post_slug=kwargs.get("post_slug"))

    @superuser_required
    def patch(self, request: HttpRequest, **kwargs: str) -> JsonResponse:
        data = json.loads(request.body)
        Comment.objects.filter(id=(comment_id := data.get("comment_id"))).update(
            viewed=True
        )
        return JsonResponse(
            {"status": "success", "action": "mark_viewed", "comment_id": comment_id}
        )

    @superuser_required
    def delete(self, request: HttpRequest, **kwargs: str) -> JsonResponse:
        data = json.loads(request.body)
        Comment.objects.filter(id=(comment_id := data.get("comment_id"))).delete()
        return JsonResponse(
            {"status": "success", "action": "delete", "comment_id": comment_id}
        )


class EditPost(View):
    @superuser_required
    def get(self, request: HttpRequest, **kwargs: str) -> HttpResponse:
        return render(
            request,
            "edit_post.html",
            {
                "post": get_object_or_404(Post, slug=kwargs.get("post_slug")),
                "all_tags": Tag.objects.all(),
            },
        )

    @superuser_required
    def post(self, request: HttpRequest, **kwargs: str) -> HttpResponse:
        post = get_object_or_404(Post, slug=kwargs.get("post_slug"))
        post.title = request.POST.get("title").strip()
        post.description = request.POST.get("description").strip()
        post.slug = request.POST.get("slug").strip(string.punctuation)
        post.content = request.POST.get("content").strip()
        post.is_rtl = "is_rtl" in request.POST
        post.is_public = "is_public" in request.POST
        post.tags.clear()
        for tag_id in request.POST.getlist("tags"):
            post.tags.add(Tag.objects.get(id=tag_id))
        post.save()
        return redirect("edit_post", post_slug=post.slug)


class NotFoundError(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "404.html", status=404)
