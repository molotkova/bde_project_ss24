from django.urls import path


from fame.views.html import fame_list, experts_list, bullshitters_list ## added for T5
from fame.views.rest import ExpertiseAreasApiView, FameUsersApiView, FameListApiView


app_name = "fame"


urlpatterns = [ ## holds all path definitions for the fame app
    path(
        "api/expertise_areas", ExpertiseAreasApiView.as_view(), name="expertise_areas"
    ),
    path("api/users", FameUsersApiView.as_view(), name="fame_users"),
    path("api/fame", FameListApiView.as_view(), name="fame_fulllist"),
    path("html/fame", fame_list, name="fame_list"),
    ## added below for T5  -----------------------<
    path("html/experts", experts_list, name="experts_list"),
    path("html/bullshitters", bullshitters_list, name="bullshitters_list"),
]
