"""
Resolve the effective user for API writes when the project runs in open (no-token) mode.

Anonymous requests are attributed to a single placeholder user so FK fields stay valid.
"""
from django.contrib.auth import get_user_model

ANON_API_USERNAME = "__anonymous_api__"


def get_api_actor(request):
    """
    Return the authenticated user, or a shared placeholder user for unauthenticated API access.

    Used when DEFAULT_PERMISSION is AllowAny so uploads / jobs / ranking still have valid
    ``uploaded_by`` / ``created_by`` without requiring VITE_API_TOKEN or similar.
    """
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return user

    User = get_user_model()
    placeholder, created = User.objects.get_or_create(
        username=ANON_API_USERNAME,
        defaults={
            "email": "anonymous-api@local.invalid",
            "first_name": "Public",
            "last_name": "API",
        },
    )
    if created:
        placeholder.set_unusable_password()
        placeholder.save()
    return placeholder
