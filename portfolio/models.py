import markdown
from django.db import models
from django.utils import timezone
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
    is_public = models.BooleanField(default=False)

    def get_markdown(self) -> SafeString:
        """Renders the content in Markdown format."""
        return mark_safe(
            markdown.Markdown(extensions=["fenced_code", "codehilite"]).convert(
                self.content
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
