import markdown
import nh3
from django.db import models
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.safestring import SafeString, mark_safe

# Allowlist for the HTML produced by Python-Markdown after rendering.
# Everything else (scripts, event handlers, iframes, ...) is removed.
MARKDOWN_ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "del",
    "details",
    "div",
    "dl",
    "dd",
    "dt",
    "em",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "img",
    "ins",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "span",
    "strong",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}
MARKDOWN_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "td": {"colspan", "rowspan", "align"},
    "th": {"colspan", "rowspan", "align"},
    "div": {"class"},
    "pre": {"class"},
    "code": {"class"},
    "span": {"class"},
    "table": {"class"},
}
MARKDOWN_URL_SCHEMES = {"http", "https", "mailto"}


class Tag(models.Model):
    name = models.CharField(max_length=45)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=110, db_index=True)
    description = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    tags = models.ManyToManyField("Tag", related_name="posts")
    is_rtl = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def render_markdown(self, text: str) -> str:
        """Renders Markdown to HTML with the extensions the site uses."""
        return markdown.Markdown(
            extensions=["tables", "fenced_code", "codehilite"],
            extension_configs={"codehilite": {"guess_lang": False}},
        ).convert(text or "")

    def get_markdown(self) -> SafeString:
        """Renders the content in Markdown format, sanitized for safe HTML."""
        rendered = self.render_markdown(self.content)
        safe_html = nh3.clean(
            rendered,
            tags=MARKDOWN_ALLOWED_TAGS,
            attributes=MARKDOWN_ALLOWED_ATTRIBUTES,
            url_schemes=MARKDOWN_URL_SCHEMES,
            link_rel="noopener noreferrer nofollow",
        )
        return mark_safe(safe_html)

    def get_truncated_content(self) -> str:
        """A plain-text preview of the content (safe for autoescaping)."""
        rendered = self.render_markdown(self.content)
        preview = " ".join(strip_tags(rendered).split())[:200]
        return f"{preview}..." if preview else ""


class Comment(models.Model):
    name = models.CharField(max_length=55)
    email = models.EmailField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    viewed = models.BooleanField(default=False)
    is_admin_comment = models.BooleanField(default=False)
    likes = models.IntegerField(default=0)
    content = models.TextField()
    post = models.ForeignKey("Post", related_name="comments", on_delete=models.CASCADE)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.name}: {self.content[:50]}"
