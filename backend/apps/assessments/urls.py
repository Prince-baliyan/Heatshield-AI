from django.urls import path

from .views import (
    AssessmentCollectionView,
    AssessmentDetailView,
    AssessmentExportView,
    AssessmentHistoryView,
    AssessmentRecommendationListView,
    LatestAreaAssessmentView,
    RecommendationRuleListView,
)


urlpatterns = [
    path("assessments/", AssessmentCollectionView.as_view(), name="assessment-list"),
    path(
        "assessments/recommendation-rules/",
        RecommendationRuleListView.as_view(),
        name="recommendation-rule-list",
    ),
    path(
        "assessments/<int:pk>/recommendations/",
        AssessmentRecommendationListView.as_view(),
        name="assessment-recommendations",
    ),
    path(
        "assessments/<int:pk>/export/",
        AssessmentExportView.as_view(),
        name="assessment-export",
    ),
    path("assessments/<int:pk>/", AssessmentDetailView.as_view(), name="assessment-detail"),
    path(
        "areas/<int:area_id>/assessments/",
        AssessmentHistoryView.as_view(),
        name="area-assessment-history",
    ),
    path(
        "areas/<int:area_id>/assessment/",
        LatestAreaAssessmentView.as_view(),
        name="area-latest-assessment",
    ),
]
