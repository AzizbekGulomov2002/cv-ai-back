"""
Role-based DRF permissions for AI CV System.

When API_REQUIRE_AUTH is False (default), all checks pass so the API is fully open.
"""
from django.conf import settings
from rest_framework.permissions import BasePermission


def api_is_open() -> bool:
    """True when the API runs without login (default)."""
    return not getattr(settings, "API_REQUIRE_AUTH", False)


class OptionalAuth(BasePermission):
    """IsAuthenticated when API_REQUIRE_AUTH is on; otherwise allow everyone."""

    message = "Authentication required."

    def has_permission(self, request, view):
        if api_is_open():
            return True
        return bool(request.user and request.user.is_authenticated)


class IsRecruiter(BasePermission):
    """Allow access only to users with role='recruiter'."""

    message = "Access restricted to recruiters only."

    def has_permission(self, request, view):
        if api_is_open():
            return True
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'recruiter'
        )


class IsCandidate(BasePermission):
    """Allow access only to users with role='candidate'."""

    message = "Access restricted to candidates only."

    def has_permission(self, request, view):
        if api_is_open():
            return True
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'candidate'
        )


class IsRecruiterOrCandidate(BasePermission):
    """Allow access to any authenticated user (recruiter or candidate)."""

    message = "Authentication required."

    def has_permission(self, request, view):
        if api_is_open():
            return True
        return request.user and request.user.is_authenticated


class IsRecruiterOrOwner(BasePermission):
    """
    Recruiter: full access.
    Candidate: access only to their own object (obj.user == request.user or obj.uploaded_by == request.user).
    """

    message = "You do not have permission to access this resource."

    def has_permission(self, request, view):
        if api_is_open():
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if api_is_open():
            return True
        if request.user.role == 'recruiter':
            return True
        owner = getattr(obj, 'user', None) or getattr(obj, 'uploaded_by', None)
        return owner == request.user
