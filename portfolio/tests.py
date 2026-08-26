import json
import re

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.safestring import SafeString

from portfolio.models import Comment, Post, Tag


class PortfolioTestCase(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.superuser = User.objects.create_superuser(
            username="superuser",
            email="super@example.com",
            password="superpassword",
        )
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
            password="regularpassword",
        )
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staffpassword",
            is_staff=True,
        )
        self.tag = Tag.objects.create(name="python")
        self.public_post = Post.objects.create(
            title="Public Post",
            slug="public-post",
            description="A public post",
            content="# Hello\n\nSome **content**.",
            is_public=True,
        )
        self.public_post.tags.add(self.tag)
        self.private_post = Post.objects.create(
            title="Private Post",
            slug="private-post",
            description="A private post",
            content="secret content",
            is_public=False,
        )
        self.comment = Comment.objects.create(
            name="Alice",
            email="alice@example.com",
            content="Nice post!",
            post=self.public_post,
        )

    def tearDown(self) -> None:
        cache.clear()


class IndexViewTest(PortfolioTestCase):
    def test_anonymous_sees_public_last_post(self) -> None:
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Post")
        self.assertContains(response, "public-post")

    def test_last_post_is_the_newest(self) -> None:
        Post.objects.create(
            title="Newest Post",
            slug="newest-post",
            description="The newest one",
            is_public=True,
        )
        response = self.client.get(reverse("index"))
        self.assertContains(response, "Newest Post")
        self.assertNotContains(response, "Public Post")

    def test_private_posts_are_hidden(self) -> None:
        response = self.client.get(reverse("index"))
        self.assertNotContains(response, "Secret Content")
        self.assertNotContains(response, "Private Post")

    def test_superuser_sees_unread_comments(self) -> None:
        Comment.objects.create(
            name="Bob",
            content="Unread!",
            post=self.private_post,
            viewed=False,
        )
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unread comments")
        self.assertContains(response, "Private Post")

    def test_anonymous_does_not_see_unread_comments(self) -> None:
        Comment.objects.create(
            name="Bob", content="Unread!", post=self.public_post, viewed=False
        )
        response = self.client.get(reverse("index"))
        self.assertNotContains(response, "Unread comments")


class AllPostsViewTest(PortfolioTestCase):
    def test_anonymous_sees_only_public_posts(self) -> None:
        response = self.client.get(reverse("all_posts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Post")
        self.assertNotContains(response, "Private Post")

    def test_superuser_sees_private_posts_with_badge(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("all_posts"))
        self.assertContains(response, "Private Post")
        self.assertContains(response, "PRIVATE")

    def test_search_by_title(self) -> None:
        response = self.client.get(reverse("all_posts"), {"query": "Public"})
        self.assertContains(response, "Public Post")
        self.assertNotContains(response, "Private Post")

    def test_search_by_tag(self) -> None:
        response = self.client.get(reverse("all_posts"), {"query": "python"})
        self.assertContains(response, "Public Post")
        self.assertNotContains(response, "Private Post")

    def test_empty_query_shows_everything(self) -> None:
        response = self.client.get(reverse("all_posts"), {"query": ""})
        self.assertContains(response, "Public Post")
        self.assertNotContains(response, "Private Post")

    def test_query_is_preserved_in_search_box(self) -> None:
        response = self.client.get(reverse("all_posts"), {"query": "python"})
        self.assertContains(response, 'value="python"')

    def test_comment_count_is_annotated(self) -> None:
        response = self.client.get(reverse("all_posts"))
        self.assertContains(response, ">1<")

    def test_pagination_second_page(self) -> None:
        for index in range(5):
            Post.objects.create(
                title=f"Page Post {index}",
                slug=f"page-post-{index}",
                is_public=True,
            )
        response = self.client.get(reverse("all_posts"), {"page": 2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Next page")

    def test_invalid_page_returns_200(self) -> None:
        response = self.client.get(reverse("all_posts"), {"page": 9999})
        self.assertEqual(response.status_code, 200)

    def test_special_characters_in_query_are_safe(self) -> None:
        response = self.client.get(reverse("all_posts"), {"query": "<script>"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<script>")


class SinglePostViewTest(PortfolioTestCase):
    def test_get_public_post(self) -> None:
        response = self.client.get(
            reverse("single_post", kwargs={"post_slug": "public-post"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Post")
        self.assertContains(response, "<h1>Hello</h1>", html=True)

    def test_get_private_post_as_anonymous_is_404(self) -> None:
        response = self.client.get(
            reverse("single_post", kwargs={"post_slug": "private-post"})
        )
        self.assertEqual(response.status_code, 404)

    def test_get_private_post_as_superuser(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.get(
            reverse("single_post", kwargs={"post_slug": "private-post"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Private Post")

    def test_comment_content_is_escaped(self) -> None:
        Comment.objects.create(
            name="Mallory",
            content="<script>alert(1)</script>",
            post=self.public_post,
        )
        response = self.client.get(
            reverse("single_post", kwargs={"post_slug": "public-post"})
        )
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_markdown_is_sanitized(self) -> None:
        post = Post.objects.create(
            title="Unsafe",
            slug="unsafe",
            description="unsafe content",
            content=(
                "[click](javascript:alert(1))\n\n"
                "<script>alert(2)</script>\n\n"
                '<img src="x" onerror="alert(3)">\n\n'
                "**bold**"
            ),
            is_public=True,
        )
        response = self.client.get(
            reverse("single_post", kwargs={"post_slug": post.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "javascript:")
        self.assertNotContains(response, "<script>")
        self.assertNotContains(response, "onerror")
        self.assertContains(response, "<strong>bold</strong>", html=True)

    def test_comment_count_shown(self) -> None:
        response = self.client.get(
            reverse("single_post", kwargs={"post_slug": "public-post"})
        )
        self.assertContains(response, ">1<")


class CommentCreationTest(PortfolioTestCase):
    def _comment_data(self, **overrides):
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "content": "Great article!",
        }
        data.update(overrides)
        return data

    def test_valid_comment_is_created(self) -> None:
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._comment_data(),
        )
        self.assertRedirects(
            response,
            reverse("single_post", kwargs={"post_slug": "public-post"}),
        )
        comment = Comment.objects.get(name="John Doe")
        self.assertEqual(comment.content, "Great article!")
        self.assertEqual(comment.email, "john@example.com")
        self.assertFalse(comment.is_admin_comment)

    def test_missing_name_is_rejected(self) -> None:
        data = self._comment_data(name="")
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}), data
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Comment.objects.filter(name="").count(), 0)

    def test_too_long_name_is_rejected(self) -> None:
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._comment_data(name="x" * 60),
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_email_is_rejected(self) -> None:
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._comment_data(email="not-an-email"),
        )
        self.assertEqual(response.status_code, 400)

    def test_too_long_content_is_rejected(self) -> None:
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._comment_data(content="x" * 2001),
        )
        self.assertEqual(response.status_code, 400)

    def test_honeypot_comment_is_dropped_silently(self) -> None:
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._comment_data(website="http://spam.example"),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.filter(name="John Doe").count(), 0)

    def test_comment_on_private_post_as_anonymous_is_404(self) -> None:
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "private-post"}),
            self._comment_data(),
        )
        self.assertEqual(response.status_code, 404)

    def test_staff_comment_is_marked_admin(self) -> None:
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._comment_data(),
        )
        self.assertEqual(response.status_code, 302)
        comment = Comment.objects.get(name="John Doe")
        self.assertTrue(comment.is_admin_comment)

    @override_settings(
        COMMENT_RATE_LIMIT=1,
        COMMENT_RATE_LIMIT_ENABLED=True,
        COMMENT_RATE_WINDOW_SECONDS=600,
    )
    def test_rate_limit_blocks_fourth_comment(self) -> None:
        first = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._comment_data(),
        )
        self.assertEqual(first.status_code, 302)
        second = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._comment_data(name="Jane"),
        )
        self.assertEqual(second.status_code, 429)
        self.assertEqual(Comment.objects.filter(name="Jane").count(), 0)


class LikeCommentTest(PortfolioTestCase):
    def test_like_comment(self) -> None:
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            {"like_comment_id": str(self.comment.id)},
        )
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["action"], "like")
        self.assertEqual(payload["likes"], 1)

    def test_like_comment_twice_increments(self) -> None:
        self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            {"like_comment_id": str(self.comment.id)},
        )
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            {"like_comment_id": str(self.comment.id)},
        )
        self.assertEqual(json.loads(response.content)["likes"], 2)

    def test_like_invalid_id_returns_400(self) -> None:
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            {"like_comment_id": "not-a-number"},
        )
        self.assertEqual(response.status_code, 400)

    def test_like_comment_from_another_post_is_404(self) -> None:
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "private-post"}),
            {"like_comment_id": str(self.comment.id)},
        )
        self.assertEqual(response.status_code, 404)

    def test_like_private_post_comment_as_anonymous_is_404(self) -> None:
        private_comment = Comment.objects.create(
            name="Bob", content="secret", post=self.private_post
        )
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "private-post"}),
            {"like_comment_id": str(private_comment.id)},
        )
        self.assertEqual(response.status_code, 404)

    def test_like_private_post_comment_as_superuser(self) -> None:
        private_comment = Comment.objects.create(
            name="Bob", content="secret", post=self.private_post
        )
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("single_post", kwargs={"post_slug": "private-post"}),
            {"like_comment_id": str(private_comment.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["likes"], 1)


class CommentAdminActionsTest(PortfolioTestCase):
    def _json(self, comment_id):
        return json.dumps({"comment_id": comment_id}).encode()

    def test_patch_requires_superuser(self) -> None:
        response = self.client.patch(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._json(self.comment.id),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.regular_user)
        response = self.client.patch(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._json(self.comment.id),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_patch_marks_comment_viewed(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.patch(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._json(self.comment.id),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.viewed)

    def test_patch_with_bad_json_returns_400(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.patch(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            data=b"{not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_comment_from_another_post_is_404(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.patch(
            reverse("single_post", kwargs={"post_slug": "private-post"}),
            self._json(self.comment.id),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_requires_superuser(self) -> None:
        response = self.client.delete(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._json(self.comment.id),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_delete_removes_comment(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.delete(
            reverse("single_post", kwargs={"post_slug": "public-post"}),
            self._json(self.comment.id),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())


class EditPostViewTest(PortfolioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.edit_url = reverse(
            "edit_post", kwargs={"post_slug": self.public_post.slug}
        )

    def _post_data(self, **overrides):
        data = {
            "title": "Updated Title",
            "description": "Updated description",
            "slug": "updated-post",
            "content": "The new content...",
            "is_public": "on",
        }
        data.update(overrides)
        return data

    def test_get_edit_post_as_superuser(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Post")

    def test_get_edit_post_as_anonymous_is_403(self) -> None:
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 403)

    def test_get_edit_post_as_regular_user_is_403(self) -> None:
        self.client.force_login(self.regular_user)
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 403)

    def test_post_edit_updates_post(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.post(self.edit_url, self._post_data())
        self.assertEqual(response.status_code, 302)
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.title, "Updated Title")
        self.assertEqual(self.public_post.slug, "updated-post")
        self.assertEqual(self.public_post.content, "The new content...")
        self.assertTrue(self.public_post.is_public)

    def test_post_edit_slugifies_user_input(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.post(self.edit_url, self._post_data(slug="My New Slug!"))
        self.assertEqual(response.status_code, 302)
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.slug, "my-new-slug")

    def test_post_edit_duplicate_slug_is_rejected(self) -> None:
        Post.objects.create(
            title="Other", slug="taken", description="x", is_public=True
        )
        self.client.force_login(self.superuser)
        response = self.client.post(self.edit_url, self._post_data(slug="taken"))
        self.assertEqual(response.status_code, 400)
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.slug, "public-post")

    def test_post_edit_blank_slug_is_rejected(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.post(self.edit_url, self._post_data(slug="!!!"))
        self.assertEqual(response.status_code, 400)

    def test_post_edit_too_long_title_is_rejected(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.post(self.edit_url, self._post_data(title="x" * 120))
        self.assertEqual(response.status_code, 400)

    def test_post_edit_as_regular_user_is_403(self) -> None:
        self.client.force_login(self.regular_user)
        response = self.client.post(self.edit_url, self._post_data())
        self.assertEqual(response.status_code, 403)
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.title, "Public Post")

    def test_post_edit_updates_tags(self) -> None:
        self.client.force_login(self.superuser)
        other_tag = Tag.objects.create(name="django")
        response = self.client.post(
            self.edit_url,
            self._post_data(tags=[str(other_tag.id)]),
        )
        self.assertEqual(response.status_code, 302)
        self.public_post.refresh_from_db()
        self.assertEqual(
            list(self.public_post.tags.values_list("name", flat=True)),
            ["django"],
        )


class NotFoundErrorViewTest(PortfolioTestCase):
    def test_custom_404_handler(self) -> None:
        response = self.client.get("/nonexistent-url/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Status code: 404", status_code=404)


class SecurityHeadersTest(PortfolioTestCase):
    def test_csp_is_present_and_matches_nonce(self) -> None:
        response = self.client.get(
            reverse("single_post", kwargs={"post_slug": "public-post"})
        )
        self.assertEqual(response.status_code, 200)
        csp = response.headers.get("Content-Security-Policy", "")
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("object-src 'none'", csp)
        nonces = re.findall(r'nonce="([^"]+)"', response.content.decode())
        self.assertTrue(nonces, "inline script should carry a nonce")
        for nonce in nonces:
            self.assertIn(f"nonce-{nonce}", csp)

    def test_additional_security_headers(self) -> None:
        response = self.client.get(reverse("index"))
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("Referrer-Policy"), "same-origin")
        self.assertIn(
            "geolocation=()",
            response.headers.get("Permissions-Policy", ""),
        )


class MarkdownModelTest(PortfolioTestCase):
    def test_markdown_strips_script_and_javascript_urls(self) -> None:
        post = Post.objects.create(
            title="XSS",
            slug="xss",
            description="x",
            content=(
                "<script>alert(1)</script>\n\n"
                "[bad](javascript:alert(1))\n\n"
                '<img src="x" onerror="alert(2)">'
            ),
        )
        rendered = str(post.get_markdown())
        self.assertNotIn("<script", rendered)
        self.assertNotIn("javascript:", rendered)
        self.assertNotIn("onerror", rendered)

    def test_markdown_keeps_code_highlighting(self) -> None:
        post = Post.objects.create(
            title="Code",
            slug="code",
            description="x",
            content="```python\nprint('hi')\n```",
        )
        rendered = str(post.get_markdown())
        self.assertIn("codehilite", rendered)
        self.assertIn('<span class="nb">print</span>', rendered)

    def test_truncated_content_is_plain_text(self) -> None:
        post = Post.objects.create(
            title="Trunc",
            slug="trunc",
            description="x",
            content="# Heading\n\nSome long text...",
        )
        preview = post.get_truncated_content()
        self.assertIsInstance(preview, str)
        self.assertNotIsInstance(preview, SafeString)
        self.assertTrue(preview.endswith("..."))
        self.assertNotIn("<", preview)

    def test_truncated_content_handles_malformed_html(self) -> None:
        post = Post.objects.create(
            title="Bad",
            slug="bad",
            description="x",
            content="hello <script",
        )
        preview = post.get_truncated_content()
        # Plain text preview must never be marked safe or contain raw tags.
        self.assertNotIn("<script", preview.lower() or "")
