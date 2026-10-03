from rest_framework_simplejwt.views import TokenObtainPairView

from core.modules.auth.serializer import LoginSerializer


class ViewTokenObtainPair(TokenObtainPairView):
    throttle_scope = "login"
    serializer_class = LoginSerializer
