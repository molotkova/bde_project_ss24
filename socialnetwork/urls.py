from django.urls import path

from socialnetwork.views.html import timeline
from socialnetwork.views.rest import PostsListApiView

app_name = "socialnetwork"

urlpatterns = [
    path("api/posts", PostsListApiView.as_view(), name="posts_fulllist"),
    path("api/posts/experts", PostsListApiView.as_view(), name="posts_fulllist"),
    path("api/posts/bullshitters", PostsListApiView.as_view(), name="posts_fulllist"),
    path("html/timeline", timeline, name="timeline"),
]
