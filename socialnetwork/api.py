from django.db.models import Q

from fame.models import Fame, FameLevels, ExpertiseAreas
from socialnetwork.models import Posts, SocialNetworkUsers, PostExpertiseAreasAndRatings


from collections import defaultdict

# general methods independent of html and REST views
# should be used by REST and html views


def _get_social_network_user(user) -> SocialNetworkUsers:
    """Given a FameUser, gets the social network user from the request. Assumes that the user is authenticated."""
    try:
        user = SocialNetworkUsers.objects.get(id=user.id)
    except SocialNetworkUsers.DoesNotExist:
        raise PermissionError("User does not exist")
    return user


def timeline(user: SocialNetworkUsers, start: int = 0, end: int = None, published=True):
    """Get the timeline of the user. Assumes that the user is authenticated."""
    _follows = user.follows.all()
    posts = Posts.objects.filter(
        (Q(author__in=_follows) & Q(published=published)) | Q(author=user)
    ).order_by("-submitted")
    if end is None:
        return posts[start:]
    else:
        return posts[start : end + 1]


def search(keyword: str, start: int = 0, end: int = None, published=True):
    """Search for all posts in the system containing the keyword. Assumes that all posts are public"""
    posts = Posts.objects.filter(
        Q(content__icontains=keyword)
        | Q(author__email__icontains=keyword)
        | Q(author__first_name__icontains=keyword)
        | Q(author__last_name__icontains=keyword),
        published=published,
    ).order_by("-submitted")
    if end is None:
        return posts[start:]
    else:
        return posts[start : end + 1]


def follows(user: SocialNetworkUsers, start: int = 0, end: int = None):
    """Get the users followed by this user. Assumes that the user is authenticated."""
    _follows = user.follows.all()
    if end is None:
        return _follows[start:]
    else:
        return _follows[start : end + 1]


def followers(user: SocialNetworkUsers, start: int = 0, end: int = None):
    """Get the followers of this user. Assumes that the user is authenticated."""
    _followers = user.followed_by.all()
    if end is None:
        return _followers[start:]
    else:
        return _followers[start : end + 1]


def follow(user: SocialNetworkUsers, user_to_follow: SocialNetworkUsers):
    """Follow a user. Assumes that the user is authenticated. If user already follows the user, signal that."""
    if user_to_follow in user.follows.all():
        return {"followed": False}
    user.follows.add(user_to_follow)
    user.save()
    return {"followed": True}


def unfollow(user: SocialNetworkUsers, user_to_unfollow: SocialNetworkUsers):
    """Unfollow a user. Assumes that the user is authenticated. If user does not follow the user anyway, signal that."""
    if user_to_unfollow not in user.follows.all():
        return {"unfollowed": False}
    user.follows.remove(user_to_unfollow)
    user.save()
    return {"unfollowed": True}


def submit_post(
    user: SocialNetworkUsers,
    content: str,
    cites: Posts = None,
    replies_to: Posts = None,
):
    """Submit a post for publication. Assumes that the user is authenticated.
    returns a tuple of three elements:
    1. a dictionary with the keys "published" and "id" (the id of the post)
    2. a list of dictionaries containing the expertise areas and their truth ratings
    3. a boolean indicating whether the user was banned and logged out and should be redirected to the login page
    """

    # create post  instance:
    post = Posts.objects.create(
        content=content,
        author=user,
        cites=cites,
        replies_to=replies_to,
    )

    # classify the content into expertise areas:
    # only publish the post if none of the expertise areas contains bullshit:
    _at_least_one_expertise_area_contains_bullshit, _expertise_areas = (
        post.determine_expertise_areas_and_truth_ratings()
    )
    post.published = not _at_least_one_expertise_area_contains_bullshit

    redirect_to_logout = False


    #########################

    # We get the negative expertise areas of the user
    negative_fame_areas = Fame.objects.filter(
        user = user,
        expertise_area__in = [area["expertise_area"] for area in _expertise_areas],
        fame_level__numeric_value__lt=0
    )

    # Check if any of the negative expertise areas of the user coincide with the tags of the post.
    # If it does set the published to false, i.e. do not post.
    if negative_fame_areas.exists():
        post.published = False


    ##this is the efforts for T2a, not working
    if _at_least_one_expertise_area_contains_bullshit:
        for area in _expertise_areas:
            #have to use this 'area[asdasd] and', otherwise it says it has NoneType
            if area['truth_rating'] and area['truth_rating'].numeric_value < 0:
                try:
                    # Get the user's fame entry for this expertise area
                    fame_entry = Fame.objects.get(user=user, expertise_area=area['expertise_area'])

                    # Lower the fame level if possible
                    fame_entry.fame_level = fame_entry.fame_level.get_next_lower_fame_level()
                    fame_entry.save()

                except Fame.DoesNotExist:#if this fame are didnt exist for the user
                    fame_entry = Fame.objects.create(
                        user=user,
                        expertise_area=area['expertise_area'],
                        fame_level= FameLevels.objects.get(name="Confuser"),
                        #we create a new fame object, which is assigned to user that is confuser
                    )
                    fame_entry.save()
                except ValueError:#if we cant get any lower -> user should be banned
                    user.is_banned = True
                    user.is_active = False
                    redirect_to_logout = True
                    user.save()
                    posts_of_the_banned = Posts.objects.filter(
                        author=user,
                        published=True,
                    )
                    for posts in posts_of_the_banned:
                        posts.published = False
                        posts.save()
                finally:
                    pass

    #########################

    post.save()

    return (
        {"published": post.published, "id": post.id},
        _expertise_areas,
        redirect_to_logout,
    )

def rate_post(
    user: SocialNetworkUsers, post: Posts, rating_type: str, rating_score: int
):
    """Rate a post. Assumes that the user is authenticated. If user already rated the post with the given rating_type,
    update that rating score."""
    user_rating = None
    try:
        user_rating = user.userratings_set.get(post=post, rating_type=rating_type)
    except user.userratings_set.model.DoesNotExist:
        pass

    if user == post.author:
        raise PermissionError(
            "User is the author of the post. You cannot rate your own post."
        )

    if user_rating is not None:
        # update the existing rating:
        user_rating.rating_score = rating_score
        user_rating.save()
        return {"rated": True, "type": "update"}
    else:
        # create a new rating:
        user.userratings_set.add(
            post,
            through_defaults={"rating_type": rating_type, "rating_score": rating_score},
        )
        user.save()
        return {"rated": True, "type": "new"}


def fame(user: SocialNetworkUsers):
    """Get the fame of a user. Assumes that the user is authenticated."""
    try:
        user = SocialNetworkUsers.objects.get(id=user.id)
    except SocialNetworkUsers.DoesNotExist:
        raise ValueError("User does not exist")

    return user, Fame.objects.filter(user=user)




def experts():
    """Return for each existing expertise area in the fame profiles a list of the users having positive fame for that
    expertise area. The list should be a Python dictionary with keys ``user'' (for the user) and ``fame_level_numeric''
    (for the corresponding fame value), and should be ranked, i.e. users with the highest fame are shown first, in case
    there is a tie, within that tie sort by date_joined (most recent first). Note that expertise areas with no expert
    may be omitted.
    """
    #########################

    filter_condition = Q(fame_level__numeric_value__gt=0)
    sorting_key = lambda x: (-x['fame_level_numeric'], -x['user'].date_joined.timestamp())

    return get_experts_and_bullshitters(filter_condition=filter_condition, sorting_key=sorting_key)

    #########################



def bullshitters():
    """Return for each existing expertise area in the fame profiles a list of the users having negative fame for that
    expertise area. The list should be a Python dictionary with keys ``user'' (for the user) and ``fame_level_numeric''
    (for the corresponding fame value), and should be ranked, i.e. users with the lowest fame are shown first, in case
    there is a tie, within that tie sort by date_joined (most recent first). Note that expertise areas with no expert
    may be omitted.
    """
    #########################

    filter_condition = Q(fame_level__numeric_value__lt=0)
    sorting_key = lambda x: (x['fame_level_numeric'], -x['user'].date_joined.timestamp())

    return get_experts_and_bullshitters(filter_condition=filter_condition, sorting_key=sorting_key)
    #########################


def get_experts_and_bullshitters(filter_condition, sorting_key):

    # Dictionary to store the result
    areas_experts = defaultdict(list)

    # Query Fame with positive fame levels and include related objects in a single query
    fame_entries = Fame.objects.filter(filter_condition)

    for fame in fame_entries:
        areas_experts[fame.expertise_area].append({
            'user': fame.user,
            'fame_level_numeric': fame.fame_level.numeric_value,
        })

    # Sorting users within each expertise area
    result = {}
    for area, experts in areas_experts.items():
        sorted_experts = sorted(
            experts,
            key=sorting_key
        )
        result[area] = sorted_experts

    return result