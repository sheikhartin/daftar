from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from portfolio.models import Post, Tag


class IndexViewTest(TestCase):
    def test_get_last_post(self) -> None:
        post = Post.objects.create(
            title="Test Post",
            slug="test-post",
            content="Test Content",
            is_public=True,
        )
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, post.title)
        self.assertContains(response, post.slug)


class AllPostsViewTest(TestCase):
    def test_get_all_posts_no_query(self) -> None:
        Post.objects.create(
            title="Test Post 1",
            slug="test-post-1",
            content="Test Content 1",
            is_public=True,
        )
        Post.objects.create(
            title="Test Post 2",
            slug="test-post-2",
            content="Test Content 2",
            is_public=True,
        )
        response = self.client.get(reverse("all_posts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Post 1")
        self.assertContains(response, "Test Post 2")

    def test_get_all_posts_with_query(self) -> None:
        tag = Tag.objects.create(name="test-tag")
        post = Post.objects.create(
            title="Test Post 1",
            slug="test-post-1",
            content="Test Content 1",
            is_public=True,
        )
        post.tags.add(tag)
        Post.objects.create(
            title="Test Post 2",
            slug="test-post-2",
            content="Test Content 2",
            is_public=True,
        )
        response = self.client.get(reverse("all_posts"), {"query": "test-tag"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Post 1")
        self.assertNotContains(response, "Test Post 2")


class SinglePostViewTest(TestCase):
    def test_get_single_post(self) -> None:
        post = Post.objects.create(
            title="Test Post",
            slug="test-post",
            content="Test Content",
            is_public=True,
        )
        response = self.client.get(
            reverse("single_post", kwargs={"post_slug": post.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, post.title)


class EditPostViewTest(TestCase):
    def setUp(self) -> None:
        self.superuser = User.objects.create_superuser(
            username="superuser", password="superpassword"
        )
        self.regular_user = User.objects.create_user(
            username="regularuser", password="regularpassword"
        )
        self.post = Post.objects.create(
            title="Test Post",
            slug="test-post",
            content="Test Content",
            is_public=True,
        )

    def test_get_edit_post_as_superuser(self) -> None:
        self.client.login(username="superuser", password="superpassword")
        response = self.client.get(
            reverse("edit_post", kwargs={"post_slug": self.post.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.post.title)

    def test_post_edit_post_as_superuser(self) -> None:
        self.client.login(username="superuser", password="superpassword")
        response = self.client.post(
            reverse("edit_post", kwargs={"post_slug": self.post.slug}),
            new_data := {
                "title": "Updated Title",
                "description": "Updated description...",
                "slug": "updated-post",
                "content": "The new content...",
                "is_public": "on",
            },
        )
        self.post.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.post.title, new_data["title"])
        self.assertEqual(self.post.description, new_data["description"])
        self.assertEqual(self.post.slug, new_data["slug"])
        self.assertEqual(self.post.content, new_data["content"])
        self.assertEqual(self.post.is_public, True)

    def test_get_edit_post_as_regular_user(self) -> None:
        self.client.login(username="regularuser", password="regularpassword")
        response = self.client.get(
            reverse("edit_post", kwargs={"post_slug": self.post.slug})
        )
        self.assertEqual(response.status_code, 403)

    def test_post_edit_post_as_regular_user(self) -> None:
        self.client.login(username="regularuser", password="regularpassword")
        response = self.client.post(
            reverse("edit_post", kwargs={"post_slug": self.post.slug}),
            {"content": "Unauthorized attempt to change content!"},
        )
        self.assertEqual(response.status_code, 403)
        self.post.refresh_from_db()
        self.assertNotEqual(
            self.post.content, "Unauthorized attempt to change content!"
        )


class NotFoundErrorViewTest(TestCase):
    def test_not_found_error_get(self) -> None:
        response = self.client.get("/nonexistent-url/")
        self.assertEqual(response.status_code, 404)
