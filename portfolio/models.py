import markdown
from django.db import models
from django.utils.safestring import SafeString, mark_safe


class Tag(models.Model):
    name = models.CharField(max_length=45)


class Post(models.Model):
    title = models.CharField(max_length=110)
    description = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField("Tag", related_name="posts")
    is_public = models.BooleanField(default=False)

    def get_markdown(self) -> SafeString:
        """Renders the content in Markdown format."""
        return mark_safe(
            markdown.Markdown(extensions=["fenced_code", "codehilite"]).convert(
                self.content
            )
        )