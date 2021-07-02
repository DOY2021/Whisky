from django.contrib.auth import (
    login as django_login,
    logout as django_logout
)
from django.shortcuts import render, get_object_or_404
from django.conf import settings

#Test API
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser, FileUploadParser, JSONParser
from rest_framework.renderers import JSONRenderer

#Custom Login
from .serializers import CustomLoginSerializer
from .models import TokenModel
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from rest_auth.app_settings import (
    TokenSerializer, UserDetailsSerializer, LoginSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer,
    PasswordChangeSerializer, JWTSerializer, create_token
)

#email auth
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny

#email auth(2)
from django.contrib.auth import get_user_model

#override
from django.http import (
    Http404,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
)
from allauth.account.models import EmailConfirmation, EmailConfirmationHMAC
from allauth.account import app_settings, signals

#API
from api.models import Profile, Whisky, Reaction, Follow
from api.serializers import ProfileSerializer, ProfileCreateSerializer, WhiskySerializer, ReactionListSerializer
#Custom Permission
from api.permissions import IsOwnerOrReadOnly

#Password Reset
from api.serializers import PasswordResetConfirmSerializer

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet


sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters(
        'password', 'old_password', 'new_password1', 'new_password2'
    )
)

#Follow-Unfollow
from api.serializers import FollowSerializer

#Custom Login
class CustomLoginView(GenericAPIView):

    permission_classes = (AllowAny,)
    serializer_class = CustomLoginSerializer
    token_model = TokenModel

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(CustomLoginView, self).dispatch(*args, **kwargs)

    def process_login(self):
        django_login(self.request, self.user)

    def get_response_serializer(self):
        if getattr(settings, 'REST_USE_JWT', False):
            response_serializer = JWTSerializer
        else:
            response_serializer = TokenSerializer
        return response_serializer

    def login(self):
        self.user = self.serializer.validated_data['user']

        if getattr(settings, 'REST_USE_JWT', False):
            self.token = jwt_encode(self.user)
        else:
            self.token = create_token(self.token_model, self.user,
                                      self.serializer)

        if getattr(settings, 'REST_SESSION_LOGIN', True):
            self.process_login()

    def get_response(self):
        serializer_class = self.get_response_serializer()

        if getattr(settings, 'REST_USE_JWT', False):
            data = {
                'user': self.user,
                'token': self.token
            }
            serializer = serializer_class(instance=data,
                                          context={'request': self.request})
        else:
            serializer = serializer_class(instance=self.token,
                                          context={'request': self.request})

        response = Response(serializer.data, status=status.HTTP_200_OK)

        if getattr(settings, 'REST_USE_JWT', False):
            from rest_framework_jwt.settings import api_settings as jwt_settings
            if jwt_settings.JWT_AUTH_COOKIE:
                from datetime import datetime
                expiration = (datetime.utcnow() + jwt_settings.JWT_EXPIRATION_DELTA)
                response.set_cookie(jwt_settings.JWT_AUTH_COOKIE,
                                    self.token,
                                    expires=expiration,
                                    httponly=True)
        return response

    def post(self, request, *args, **kwargs):
        self.request = request
        self.serializer = self.get_serializer(data=self.request.data,
                                              context={'request': request})
        self.serializer.is_valid(raise_exception=True)

        self.login()
        return self.get_response()


#Email Confirmation
class CustomConfirmEmailView(APIView):

    permission_classes = [AllowAny]

    def get(self, *args, **kwargs):
        self.object = confirmation = self.get_object()
        confirmation.confirm(self.request)
        # A React Router Route will handle the failure scenario 
        return HttpResponseRedirect('')

    def get_object(self, queryset=None):
        key = self.kwargs["key"]
        emailconfirmation = EmailConfirmationHMAC.from_key(key)
        if not emailconfirmation:
            if queryset is None:
                queryset = self.get_queryset()
            try:
                emailconfirmation = queryset.get(key=key.lower())
            except EmailConfirmation.DoesNotExist:
                raise Http404()
        return emailconfirmation

    def get_queryset(self):
        qs = EmailConfirmation.objects.all_valid()
        qs = qs.select_related("email_address__user")
        return qs

confirm_email = CustomConfirmEmailView.as_view()


#Password Reset
class PasswordResetConfirmView(GenericAPIView):
    """
    Password reset e-mail link is confirmed, therefore
    this resets the user's password.
    Accepts the following POST parameters: token, uid,
        new_password1, new_password2
    Returns the success/fail message.
    """
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = (AllowAny,)

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(PasswordResetConfirmView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": ("Password has been reset with the new password.")}
        )

#ProfileCreateView
class ProfileCreateAPIView(generics.CreateAPIView):
    model = Profile
    serializer_class = ProfileCreateSerializer
    parser_classes = (FormParser, MultiPartParser)

    def perform_create(self, serializer):
        #File Upload
        file_obj = serializer.validated_data['profile_photo']
        serializer.save(user_id = self.request.user.pk, id = self.request.user.pk)

#ProfileListView
class ProfileViewSet(generics.ListAPIView):   #/profile/all : simple profile list view
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()
    permission_classes = (IsOwnerOrReadOnly,)

class ProfileDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    parser_classes = (FormParser, MultiPartParser)

    def put(self, request, *args, **kwargs):
        file_obj = request.data['profile_photo']
        return self.update(request, *args, **kwargs)


class WhiskyListAPIView(generics.ListAPIView):
    queryset = Whisky.objects.all()
    serializer_class = WhiskySerializer

class WhiskyDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Whisky.objects.all()
    serializer_class = WhiskySerializer

class ReactionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, whisky_pk):
        try:
            return Reaction.objects.all().filter(whisky_id = whisky_pk)
        except Reaction.DoesNotExist:
            raise Http404

    def get(self, request, whisky_pk, format = None):
        reactions = self.get_object(whisky_pk)
        serializer = ReactionListSerializer(reactions, many = True)
        return Response(serializer.data)


    def post(self, request, whisky_pk, format = None):
        reactions = self.get_object(whisky_pk)
        serializer = ReactionListSerializer(reactions, data = request.data)
        if serializer.is_valid(raise_exception = True):
            whisky = get_object_or_404(Whisky, pk = whisky_pk)

            cur_counts = whisky.rating_counts
            cur_rating = whisky.whisky_ratings * cur_counts
            print(cur_counts)

            new_total_rating = cur_rating + request.data.get('review_rating')
            cur_counts = cur_counts+1
            new_rating = round(new_total_rating/cur_counts, 2)
            whisky.rating_counts = cur_counts
            whisky.whisky_ratings = new_rating
            whisky.save()
            serializer.save(user = request.user, whisky = whisky)
            return Response(serializer.data, status = status.HTTP_201_CREATED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def reaction_update_delete(request, reaction_pk):
    reaction = get_object_or_404(Reaction, pk = reaction_pk)
    if not reaction.user == request.user:
        return Response({'message':'No permission'})

    if request.method == 'GET':
        reactions = Reaction.objects.all().filter(pk = reaction_pk)
        serializer = ReactionListSerializer(reactions, many = True)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ReactionListSerializer(reaction, data = request.data)
        if serializer.is_valid(raise_exception = True):
            reaction = get_object_or_404(Reaction, pk = reaction_pk)
            whisky = get_object_or_404(Whisky, pk = reaction.whisky.pk)
            cur_rating = whisky.whisky_ratings * whisky.rating_counts
            cur_counts = whisky.rating_counts
            cur_rating = cur_rating - reaction.review_rating
            cur_rating = cur_rating + request.data.get('review_rating')
            new_rating = round(cur_rating/cur_counts, 2)
            whisky.whisky_ratings = new_rating
            whisky.save()

            serializer.save(user = request.user, whisky = whisky)
            return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

'''
class ReactionUpdateDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, whisky_pk):
        try:
            return Reaction.objects.all().filter(whisky_id = whisky_pk)
        except Reaction.DoesNotExist:
            raise Http404

    def put(self, request, reaction_pk, format = None):
        serializer = ReactionListSerializer(reactions, data = request.data)
        if serializer.is_valid(raise_exception = True):
            reaction = get_object_or_404(Reaction, pk = reaction_pk)
            if not reaction.user == request.user:
                return Response({'message':'No permission'})

            whisky = get_object_or_404(Whisky, pk = reaction.whisky.pk)
            cur_rating = whisky.whisky_ratings * whisky.rating_counts
            cur_counts = whisky.rating_counts
            cur_rating = cur_rating - reaction.review_rating
            cur_rating = cur_rating + request.data.get('review_rating')
            new_rating = round(cur_rating/cur_counts, 2)
            whisky.whisky_ratings = new_rating
            whisky.save()

            serializer.save(user = request.user, whisky = whisky)
            return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
'''
#Follow (New) 

class FollowView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer

    def post(self, request, *args, **kwargs):
        #Exc) 타인 계정 request 불가
        if int(self.request.user.id) == int(request.data['follower']):
            #Exc) 중복 팔로우 불가
            if Follow.objects.filter(follower = request.data['follower'], following = request.data['following']):
                return Response(
                        {"detail": ("Already Following User")}
                        )
            #Exc) 자기자신을 follow 할 수 없음
            elif request.data['follower'] == request.data['following']: 
                return Response(
                        {"detail": ("Can't follow yourself")}
                        )
            else:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(
                        {"detail": ("Successfully Followed")}
                        )
        else:
            return Response(
                    {"detail": ("Bad Request")}
                    )

#Plain Code
#    def post(self, request, *args, **kwargs):
#        serializer = self.get_serializer(data=request.data)
#        serializer.is_valid(raise_exception=True)
#        serializer.save()
#        return Response(
#                {"detail": ("Succesfully Followed")}
#                )


#Work in Progress
class FollowerDetailView(generics.ListAPIView):
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer

