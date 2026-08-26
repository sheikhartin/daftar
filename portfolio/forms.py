"""Forms used by the portfolio views."""

from django import forms
from django.utils.text import slugify

from portfolio.models import Post, Tag


class CommentForm(forms.Form):
    """Validates a visitor comment and includes a spam honeypot."""

    name = forms.CharField(
        max_length=55,
        strip=True,
        error_messages={"required": "Please enter your name."},
    )
    email = forms.EmailField(
        required=False,
        max_length=254,
        error_messages={"invalid": "Please enter a valid email address."},
    )
    content = forms.CharField(
        max_length=2000,
        strip=True,
        widget=forms.Textarea,
        error_messages={
            "required": "Please write a comment.",
            "max_length": "Comments must be 2000 characters or fewer.",
        },
    )
    # Honeypot: humans never see or fill this field.
    website = forms.CharField(required=False, widget=forms.HiddenInput)


class PostForm(forms.ModelForm):
    """Validates post edits for superusers."""

    slug = forms.CharField(max_length=255, strip=True)
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "description",
            "slug",
            "content",
            "tags",
            "is_rtl",
            "is_public",
        ]

    def clean_slug(self) -> str:
        slug = slugify(self.cleaned_data["slug"])
        if not slug:
            raise forms.ValidationError(
                "The slug may only contain letters, numbers, hyphens and underscores."
            )
        posts = Post.objects.filter(slug=slug)
        if self.instance.pk:
            posts = posts.exclude(pk=self.instance.pk)
        if posts.exists():
            raise forms.ValidationError("This slug is already in use.")
        return slug
