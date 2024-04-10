from django.urls import path

from portfolio import views

handler404 = views.NotFoundError.as_view()

urlpatterns = [
    path("", views.Index.as_view(), name="index"),
    path("posts/", views.AllPosts.as_view(), name="all_posts"),
    path("posts/<slug:post_slug>", views.SinglePost.as_view(), name="single_post"),
]
