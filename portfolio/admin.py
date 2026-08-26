from django.contrib import admin

from portfolio.models import Comment, Post, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "created_at", "is_public", "is_rtl")
    list_filter = ("is_public", "is_rtl", "created_at")
    search_fields = ("title", "description", "slug", "content")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "created_at"
    filter_horizontal = ("tags",)
    readonly_fields = ("created_at",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "post",
        "timestamp",
        "viewed",
        "is_admin_comment",
        "likes",
    )
    list_filter = ("viewed", "is_admin_comment", "timestamp")
    search_fields = ("name", "email", "content")
    date_hierarchy = "timestamp"
    readonly_fields = ("likes",)
    actions = ("mark_viewed",)

    @admin.action(description="Mark selected comments as viewed")
    def mark_viewed(self, request, queryset) -> None:
        queryset.update(viewed=True)
