from rest_framework import generics, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny

from django.contrib.auth import get_user_model
from django.db.models import Q

from .permissions import IsStaffOrSuperuser
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    LoginSerializer,
    ProfileSerializer,
    ChangeRoleSerializer,
)

User = get_user_model()



class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = [] 

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Шумо бомуваффақият сабт шудед.",
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data['phone_number']
        password = serializer.validated_data['password']

        user = User.objects.filter(Q(phone_number=identifier) | Q(username=identifier)).first()

        if user is not None and user.check_password(password):
            if not user.is_active:
                return Response(
                    {"error": "Этот аккаунт заблокирован."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "message": "Шумо бомуваффақият ворид шудед.",
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_200_OK,
            )
        
        return Response(
            {"error": "Рақами телефон ё парол нодуруст аст."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class LogoutView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "Refresh token лозим аст."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist() 
            return Response(
                {"message": "Шумо аз система баромадед. Токен blacklist шуд."},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"error": "Токен нодуруст ё аллакай blacklist шудааст."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user.profile


class UserListView(generics.ListAPIView):
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [IsStaffOrSuperuser]


class UserDeleteView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsStaffOrSuperuser]


class ChangeUserRoleView(GenericAPIView):
    queryset = User.objects.all()
    serializer_class = ChangeRoleSerializer
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request, pk):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.role = serializer.validated_data["role"]
        user.save(update_fields=["role"])
        return Response(UserSerializer(user).data)