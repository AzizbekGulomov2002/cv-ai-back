"""
Role-based DRF permissions for AI CV System.
"""
from rest_framework.permissions import BasePermission


class IsRecruiter(BasePermission):
    """Allow access only to users with role='recruiter'."""

    message = "Access restricted to recruiters only."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'recruiter'
        )


class IsCandidate(BasePermission):
    """Allow access only to users with role='candidate'."""

    message = "Access restricted to candidates only."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'candidate'
        )


class IsRecruiterOrCandidate(BasePermission):
    """Allow access to any authenticated user (recruiter or candidate)."""

    message = "Authentication required."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsRecruiterOrOwner(BasePermission):
    """
    Recruiter: full access.
    Candidate: access only to their own object (obj.user == request.user or obj.uploaded_by == request.user).
    """

    message = "You do not have permission to access this resource."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'recruiter':
            return True
        owner = getattr(obj, 'user', None) or getattr(obj, 'uploaded_by', None)
        return owner == request.user
