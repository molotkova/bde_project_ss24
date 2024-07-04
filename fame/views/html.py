from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


from fame.serializers import FameSerializer
from socialnetwork import api
from socialnetwork.api import _get_social_network_user
from socialnetwork.models import SocialNetworkUsers




@require_http_methods(["GET"])
@login_required
def fame_list(request):
    # try to get the user from the request parameters:
    userid = request.GET.get("userid", None)
    user = None
    if userid is None:
        user = _get_social_network_user(request.user)
    else:
        try:
            user = SocialNetworkUsers.objects.get(id=userid)
        except ValueError:
            pass


    user, fame = api.fame(user)
    context = {
        "fame": FameSerializer(fame, many=True).data,
        "user": user if user else "",
    }
    return render(request, "fame.html", context=context)




## fame\views\html.py added for T5 -------------------<


@require_http_methods(["GET"])
@login_required
## define experts_list func that handles requests to view experts list on the hmtl
def experts_list(request):
    ## get the list of experts using experts() func from api.py
    experts = api.experts()


    ## we then create a context dict with the list of experts
    context = {
        "experts": experts,
    }


    ## then here we fill in the experts.html template with data from the context dict above
    return render(request, "experts.html", context=context)
