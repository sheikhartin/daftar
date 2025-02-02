import markdown
from django.db import models
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.safestring import SafeString, mark_safe


class Tag(models.Model):
    name = models.CharField(max_length=45)


class Post(models.Model):
    title = models.CharField(max_length=110)
    description = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    tags = models.ManyToManyField("Tag", related_name="posts")
    is_rtl = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)

    def get_markdown(self) -> SafeString:
        """Renders the content in Markdown format."""
        return mark_safe(
            markdown.Markdown(
                extensions=["tables", "fenced_code", "codehilite"]
            ).convert(self.content)
        )

    def get_truncated_content(self) -> SafeString:
        """Truncates a content carefully."""
        return mark_safe(
            "{}...".format(
                strip_tags(
                    markdown.markdown(
                        self.content, extensions=["tables", "fenced_code", "codehilite"]
                    )
                )[:200]
            )
        )


class Comment(models.Model):
    name = models.CharField(max_length=55)
    email = models.EmailField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    viewed = models.BooleanField(default=False)
    is_admin_comment = models.BooleanField(default=False)
    likes = models.IntegerField(default=0)
    content = models.TextField()
    post = models.ForeignKey("Post", related_name="comments", on_delete=models.CASCADE)
