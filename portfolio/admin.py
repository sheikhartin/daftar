from django.contrib import admin

from portfolio.models import Tag, Post, Comment

admin.site.register(Tag)
admin.site.register(Post)
admin.site.register(Comment)
