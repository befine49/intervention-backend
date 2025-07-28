from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import QA
from .serializers import QASerializer

@api_view(['GET'])
def QAListView(request):
    qas = QA.objects.all().order_by('-created_at')
    serializer = QASerializer(qas, many=True)
    return Response(serializer.data)