"""Nomzodlar ro‘yxati — sahifalash 10 (job ranking ko‘rinishi uchun)."""

from rest_framework.pagination import PageNumberPagination


class CandidateListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50
