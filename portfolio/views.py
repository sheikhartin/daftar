import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from portfolio.forms import CommentForm, PostForm
from portfolio.models import Comment, Post, Tag


def superuser_required(
    view_func: Callable[..., HttpResponse],
) -> Callable[..., HttpResponse]:
    """Decorator for class-based view methods that only superusers may use."""

    @wraps(view_func)
    def _wrapped_view(
        self: View, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        if not request.user.is_superuser:
            return JsonResponse(
                {"status": "error", "message": "Superuser access is required."},
                status=403,
            )
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view


def _client_ip(request: HttpRequest) -> str:
    """Best-effort client IP used by the comment rate limiter.

    ``X-Forwarded-For`` is only trusted when the site is explicitly
    configured to run behind a forwarding proxy.
    """
    if settings.TRUST_FORWARDED_HEADERS:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _comment_allowed(request: HttpRequest) -> bool:
    """Fixed-window burst limit for comments (keyed by IP)."""
    if not settings.COMMENT_RATE_LIMIT_ENABLED:
        return True
    key = f"comment-rate:{_client_ip(request)}"
    count = cache.get(key, 0)
    if count >= settings.COMMENT_RATE_LIMIT:
        return False
    cache.set(key, count + 1, settings.COMMENT_RATE_WINDOW_SECONDS)
    return True


class Index(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            "index.html",
            {
                "last_post": Post.objects.filter(is_public=True)
                .annotate(comment_count=Count("comments"))
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
    page_size = 4

    def get(self, request: HttpRequest) -> HttpResponse:
        posts = (
            Post.objects.all()
            if request.user.is_superuser
            else Post.objects.filter(is_public=True)
        )
        query = request.GET.get("query", "").strip()
        if query:
            posts = posts.filter(
                Q(title__icontains=query) | Q(tags__name__icontains=query)
            ).distinct()
        posts = posts.annotate(comment_count=Count("comments")).order_by("-created_at")
        return render(
            request,
            "all_posts.html",
            {
                "query": query,
                "posts": Paginator(posts, self.page_size).get_page(
                    request.GET.get("page")
                ),
            },
        )


class SinglePost(View):
    def _get_post(self, request: HttpRequest, post_slug: str) -> Post:
        if request.user.is_superuser:
            return get_object_or_404(Post, slug=post_slug)
        return get_object_or_404(Post, slug=post_slug, is_public=True)

    def _get_comment(
        self, request: HttpRequest, post_slug: str, comment_id: int
    ) -> Comment | None:
        comments = Comment.objects.filter(id=comment_id, post__slug=post_slug)
        if not request.user.is_superuser:
            comments = comments.filter(post__is_public=True)
        return comments.first()

    def _render(
        self,
        request: HttpRequest,
        post: Post,
        comment_form: CommentForm | None = None,
        error_message: str | None = None,
        status: int = 200,
    ) -> HttpResponse:
        return render(
            request,
            "single_post.html",
            {
                "post": post,
                "comments": post.comments.all(),
                "comment_count": post.comments.count(),
                "has_permission": request.user.is_superuser,
                "comment_form": comment_form or CommentForm(),
                "error_message": error_message,
            },
            status=status,
        )

    def get(self, request: HttpRequest, **kwargs: str) -> HttpResponse:
        post = self._get_post(request, kwargs.get("post_slug", ""))
        return self._render(request, post)

    def post(self, request: HttpRequest, **kwargs: str) -> HttpResponse:
        post_slug = kwargs.get("post_slug", "")

        if like_comment_id := request.POST.get("like_comment_id"):
            return self._like_comment(request, post_slug, like_comment_id)

        post = self._get_post(request, post_slug)
        comment_form = CommentForm(request.POST)

        # Silent success for honeypot submissions (spam bots) - no save.
        if comment_form.data.get("website"):
            return redirect("single_post", post_slug=post_slug)

        if not comment_form.is_valid():
            return self._render(request, post, comment_form=comment_form, status=400)

        if not _comment_allowed(request):
            return self._render(
                request,
                post,
                comment_form=comment_form,
                error_message=(
                    f"You are commenting too quickly. Please wait "
                    f"{settings.COMMENT_RATE_WINDOW_SECONDS // 60} minutes "
                    "before posting again."
                ),
                status=429,
            )

        Comment.objects.create(
            name=comment_form.cleaned_data["name"],
            email=comment_form.cleaned_data.get("email") or None,
            content=comment_form.cleaned_data["content"],
            post=post,
            is_admin_comment=request.user.is_staff or request.user.is_superuser,
        )
        return redirect("single_post", post_slug=post_slug)

    def _like_comment(
        self, request: HttpRequest, post_slug: str, like_comment_id: str
    ) -> JsonResponse:
        try:
            comment_id = int(like_comment_id)
        except (TypeError, ValueError):
            return JsonResponse(
                {"status": "error", "message": "Invalid comment id."}, status=400
            )
        comment = self._get_comment(request, post_slug, comment_id)
        if comment is None:
            return JsonResponse(
                {"status": "error", "message": "Comment not found."}, status=404
            )
        comment_id = comment.pk
        Comment.objects.filter(pk=comment_id).update(likes=F("likes") + 1)
        comment.refresh_from_db(fields=["likes"])
        return JsonResponse(
            {
                "status": "success",
                "action": "like",
                "comment_id": comment_id,
                "likes": comment.likes,
            }
        )

    def _parse_body(self, request: HttpRequest) -> dict[str, Any] | None:
        if "json" not in (request.content_type or ""):
            return None
        try:
            data = json.loads(request.body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def _comment_id_from_body(
        self, request: HttpRequest
    ) -> tuple[dict[str, Any] | None, int | None]:
        data = self._parse_body(request)
        if data is None:
            return None, None
        try:
            return data, int(data.get("comment_id"))
        except (TypeError, ValueError):
            return data, None

    @superuser_required
    def patch(self, request: HttpRequest, **kwargs: str) -> JsonResponse:
        data, comment_id = self._comment_id_from_body(request)
        if data is None or comment_id is None:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON body."}, status=400
            )
        post_slug = kwargs.get("post_slug", "")
        comment = Comment.objects.filter(id=comment_id, post__slug=post_slug).first()
        if comment is None:
            return JsonResponse(
                {"status": "error", "message": "Comment not found."}, status=404
            )
        comment.viewed = True
        comment.save(update_fields=["viewed"])
        return JsonResponse(
            {
                "status": "success",
                "action": "mark_viewed",
                "comment_id": comment.id,
            }
        )

    @superuser_required
    def delete(self, request: HttpRequest, **kwargs: str) -> JsonResponse:
        data, comment_id = self._comment_id_from_body(request)
        if data is None or comment_id is None:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON body."}, status=400
            )
        post_slug = kwargs.get("post_slug", "")
        comment = Comment.objects.filter(id=comment_id, post__slug=post_slug).first()
        if comment is None:
            return JsonResponse(
                {"status": "error", "message": "Comment not found."}, status=404
            )
        comment.delete()
        return JsonResponse(
            {"status": "success", "action": "delete", "comment_id": comment_id}
        )


class EditPost(View):
    @superuser_required
    def get(self, request: HttpRequest, **kwargs: str) -> HttpResponse:
        post = get_object_or_404(Post, slug=kwargs.get("post_slug"))
        return self._render(
            request,
            post,
            PostForm(instance=post),
            selected_tags=[str(tag.pk) for tag in post.tags.all()],
        )

    @superuser_required
    def post(self, request: HttpRequest, **kwargs: str) -> HttpResponse:
        post = get_object_or_404(Post, slug=kwargs.get("post_slug"))
        form = PostForm(request.POST, instance=post)
        if not form.is_valid():
            return self._render(
                request,
                post,
                form,
                status=400,
                selected_tags=request.POST.getlist("tags"),
            )
        post = form.save(commit=False)
        post.save()
        form.save_m2m()
        return redirect("edit_post", post_slug=post.slug)

    @staticmethod
    def _render(
        request: HttpRequest,
        post: Post,
        form: PostForm,
        status: int = 200,
        selected_tags: list[str] | None = None,
    ) -> HttpResponse:
        return render(
            request,
            "edit_post.html",
            {
                "post": post,
                "form": form,
                "all_tags": Tag.objects.all(),
                "selected_tag_ids": selected_tags or [],
            },
            status=status,
        )


def not_found(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    """Custom 404 page (works for every HTTP method, unlike a class view)."""
    return render(request, "404.html", status=404)
