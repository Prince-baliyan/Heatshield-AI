from django.db import connection
from django.db.utils import DatabaseError
from rest_framework.response import Response
from rest_framework.views import APIView

class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        database_status = "ok"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            database_status = "error"

        http_status = 200 if database_status == "ok" else 503
        return Response(
            {
                "service": "HeatShield AI API",
                "status": "ok" if database_status == "ok" else "degraded",
                "database": database_status,
            },
            status=http_status,
        )
