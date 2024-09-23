subscription_key = "89afb264c19c4512af32ff8f7edfa936"
endpoint = "https://spotter.cognitiveservices.azure.com/"
token = 'd0a4db0d1c34a1ee699cf4ba44c393b216c49db294bcaa33d91eec84cbedc94b'

import cv2
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
from rest_framework.views import APIView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os
from rest_framework.response import Response
from rest_framework import status
import re
import time
import requests

computervision_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(subscription_key))

def preprocess_image(image_path):
    print("image_path", image_path)
    image = cv2.imread(f'media/{image_path}')

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    preprocessed_path = os.path.join(settings.MEDIA_ROOT, "preprocessed_dni_v2.jpeg")
    cv2.imwrite(preprocessed_path, thresh)
    
    return preprocessed_path

class ServiceDNIAPIView(APIView):    
    def post(self, request, *args, **kwargs):
        image_file  = request.FILES.get("image_path")
        
        path = default_storage.save(image_file.name, ContentFile(image_file.read()))
        image_path = default_storage.path(path)
                
        preprocessed_image_path = preprocess_image(path)
        
        with open(preprocessed_image_path, "rb") as image_stream:
            ocr_result = computervision_client.read_in_stream(image_stream, raw=True)
            
        operation_location = ocr_result.headers["Operation-Location"]
        operation_id = operation_location.split("/")[-1]

        while True:
            result = computervision_client.get_read_result(operation_id)
            if result.status not in ['notStarted', 'running']:
                break
            time.sleep(1)

        if result.status == OperationStatusCodes.succeeded:
            text = ""
            for page in result.analyze_result.read_results:
                for line in page.lines:
                    text += line.text + "\n"
            
            dni_pattern = re.compile(r'PER(\d{8})')
            
            dni_match = dni_pattern.search(text)
            
            if dni_match:
                dni_number = dni_match.group(1)
                info = requests.get(f'https://apiperu.dev/api/dni/{dni_number}?api_token={token}')    
                data = {
                    "dni": dni_number,
                    "info": info.json()
                }
                # Limpiar archivos
                os.remove(image_path)
                os.remove(preprocessed_image_path)
                return Response(data, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Texto con DNI no encontrado."}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({"message": "Texto con DNI no encontrado."}, status=status.HTTP_400_BAD_REQUEST)


  