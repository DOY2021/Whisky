import json
from django.contrib.auth import (
    login as django_login,
    logout as django_logout
)
from django.http.response import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
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
from rest_auth.utils import jwt_encode
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

# Whisky DB
from api.models import Whisky
from api.serializers import (WhiskySerializer, WhiskyConfirmListSerializer, WhiskyConfirmSerializer, WhiskyCreateSerializer, WhiskyUpdateSerializer)
from django_filters.rest_framework import DjangoFilterBackend

# Reaction
from api.models import Reaction, Tag, ReactionComment
from api.serializers import ReactionListSerializer, ReactionCreateSerializer, ReactionUpdateSerializer, TagSerializer, ReactionCommentSerializer

#Custom Permission
from api.permissions import IsOwnerOrReadOnly

#Password Reset
from api.serializers import PasswordResetConfirmSerializer

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

#Follow-Unfollow
from api.models import Follow
from api.serializers import FollowSerializer, FollowerSerializer, FollowingSerializer

#SearchAPI
from rest_framework import filters

#Whisky Confirm
from rest_framework.permissions import IsAdminUser

#Pagination
from api.pagination import PageSize5Pagination

#Profile
from api.models import Profile
from api.serializers import ProfileSerializer, ProfileCreateSerializer

#Profile - Collection & Wishlist
from api.models import Wishlist, Collection
from api.serializers import WishlistSerializer, WishlistViewSerializer, CollectionSerializer, CollectionViewSerializer

#Profile - Menu
from api.serializers import MenuFullSerializer

#Get UserModel
from django.contrib.auth.models import User
UserModel = get_user_model()

#SocialLogin
import requests
import jwt
from Whisky.settings import SECRET_KEY
from django.views import View
from allauth.socialaccount.models import SocialAccount, SocialApp

#Login-parameters
sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters(
        'password', 'old_password', 'new_password1', 'new_password2'
    )
)

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
        return redirect(reverse('rest_login'))

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


#Profile
class ProfileCreateAPIView(generics.CreateAPIView):
    model = Profile
    serializer_class = ProfileCreateSerializer
    parser_classes = (FormParser, MultiPartParser)

    def perform_create(self, serializer):
        if Profile.objects.filter(id = self.request.user.pk).exists():
            return Response({'message': '이미 프로필을 생성하셨습니다.'},)
        #redirection to profile update if possible
        else:
            file_obj = serializer.validated_data['profile_photo']
            serializer.save(user_id = self.request.user.pk, id = self.request.user.pk, profile_photo = file_obj)

class NicknameDuplicateAPIView(APIView):
    def get(self, request, nickname, format = None):
        if Profile.objects.filter(nickname = nickname).exists():
            return Response({'message': 'Already exists'})
        else:
            return Response({'message': 'Available nickname'})

class ProfileViewSet(generics.ListAPIView):
    #url: profile/all
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()
    permission_classes = (IsOwnerOrReadOnly,)

class ProfileDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    parser_classes = (FormParser, MultiPartParser)

    #def get(self, request, *args, **kwargs):
    #    return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        file_obj = request.data['profile_photo']
        return self.update(request, *args, **kwargs)

#Profile - Whisky List (Full) 
class MenuFullAPIView(generics.ListAPIView):
    serializer_class = MenuFullSerializer
    #Search Function Added - API extraction possible (with queryset, serializer_class)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name_eng', 'region']
    ordering_fields = ['name_eng', 'region', 'cask_type', 'alcohol']

    #contributor = ForeignKeyField 업데이트 여부 결정

    def get_queryset(self):
        queryset = Whisky.objects.all()
        current_user = self.request.user
        menu = Whisky.objects.filter(confirmed = True, contributor = current_user)
        return menu

# class MenuFullUpdateAPIView(generics.RetrieveUpdateAPIView):
#     serializer_class = MenuFullSerializer
#     #Search Function Added - API extraction possible (with queryset, serializer_class)
#     filter_backends = [filters.SearchFilter, filters.OrderingFilter]
#     search_fields = ['name_eng', 'region']
#     ordering_fields = ['name_eng', 'region', 'cask_type', 'alcohol']
# 
#     def put(self, request, *args, **kwargs):
#         return self.update(request, *args, **kwargs)

#Whisky Mainpage
class WhiskyMainListAPIView(generics.ListAPIView):
    queryset = Whisky.objects.filter(confirmed = True)
    #Add order_by
    serializer_class = WhiskySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['name_eng', 'name_kor', 'distillery']
    ordering_fields = ['whisky_ratings','rating_counts', 'updated_at']
    filterset_fields = ['category']
    #Pagination
    pagination_class = PageSize5Pagination


#Whisky DB
class WhiskyListAPIView(generics.ListAPIView):
    queryset = Whisky.objects.filter(confirmed = True)
    serializer_class = WhiskySerializer
    #Search Function Added - API extraction possible (with queryset, serializer_class)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name_eng', 'name_kor','distillery']
    ordering_fields = ['rating_counts', 'updated_at']

class WhiskyDetailAPIView(generics.RetrieveAPIView):
    queryset = Whisky.objects.all()
    serializer_class = WhiskySerializer

#Whisky Create (Open-type DB function #1)
class WhiskyCreateAPIView(generics.CreateAPIView):
    model = Whisky
    serializer_class = WhiskyCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs): 
        return self.create(request, *args, **kwargs)

#Whisky Update (Open-type DB function #2)
class WhiskyUpdateAPIView(generics.RetrieveUpdateAPIView):
    queryset = Whisky.objects.all()
    serializer_class = WhiskyUpdateSerializer

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

#Whisky Confirm
class WhiskyConfirmListAPIView(generics.ListAPIView):
    queryset = Whisky.objects.filter(confirmed = False)
    serializer_class = WhiskyConfirmListSerializer
    permission_classes = [IsAdminUser]

class WhiskyConfirmAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Whisky.objects.filter(confirmed = False)
    serializer_class = WhiskyConfirmSerializer
    permission_classes = [IsAdminUser]


#Reaction
class ReactionListAPIView(generics.ListAPIView):
    ordering_fields = ['modified_at']
    #Pagination
    pagination_class = PageSize5Pagination
    permission_classes = [IsAuthenticated]
    serializer_class = ReactionListSerializer

    def get_queryset(self):
        queryset = Reaction.objects.all()
        pk = self.kwargs['whisky_pk']
        whisky_reactions = Reaction.objects.filter(whisky_id = pk)
        return Reaction.objects.filter(whisky_id = pk)

class ReactionCreateAPIView(generics.CreateAPIView):
    model = Reaction
    serializer_class = ReactionCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        #중복 reaction 생성 확인 -> update만 가능
        pk = self.kwargs['whisky_pk']
        reactions = Reaction.objects.filter(whisky_id = pk)      # Duplicate Check (Review "POST" to one whisky by a user is done only once.)
        check = reactions.filter(user = request.user).count()
        if check >= 1:
            return Response({'message':'Your review to that whisky already exists'})
        else:
            return self.create(request, *args, **kwargs)

class ReactionUpdateAPIView(generics.UpdateAPIView):
    model = Reaction
    serializer_class = ReactionUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, *args, **kwargs):
        pk = self.kwargs['whisky_pk']
        reactions = Reaction.objects.filter(whisky_id = pk)
        check = reactions.filter(user = request.user).count()
        if check <= 0:
            return Response({'message': 'You have no reviews to this whisky'})
        else:
            return self.update(request, *args, **kwargs)
    

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
            cur_rating = whisky.whisky_ratings * whisky.rating_counts * 3
            cur_counts = whisky.rating_counts
            new_nose_rating= request.data.get('nose_rating')
            new_taste_rating= request.data.get('taste_rating')
            new_finish_rating= request.data.get('finish_rating')
            new_total_rating = new_nose_rating + new_taste_rating + new_finish_rating
            cur_rating = cur_rating - (reaction.nose_rating + reaction.taste_rating + reaction.finish_rating)
            cur_rating = cur_rating + new_total_rating
            new_rating = round((cur_rating/(cur_counts*3)), 2)
            whisky.whisky_ratings = new_rating
            whisky.save()

            # Edit Tag Fields in whisky DB
            serializer.save(user = request.user, whisky = whisky)
            return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        reaction = get_object_or_404(Reaction, pk = reaction_pk)
        whisky = get_object_or_404(Whisky, pk = reaction.whisky.pk)
        cur_rating = whisky.whisky_ratings * whisky.rating_counts *3
        cur_counts = whisky.rating_counts
        cur_rating = cur_rating - (reaction.nose_rating + reaction.taste_rating + reaction.finish_rating)
        if cur_counts == 1:     #Division by Zero Exception
            cur_counts = 0
            new_rating = 0
        else:
            cur_counts -= 1
            new_rating = round((cur_rating/(cur_counts*3)), 2)

        whisky.rating_counts = cur_counts
        whisky.whisky_ratings = new_rating
        whisky.save()
        reaction.delete()
        return Response({'message':'Review: %d Deleted' %reaction_pk})


#Tag
class TagListView(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

#WhiskyTag
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def WhiskyTopTagView(request, whisky_pk):
    if request.method == 'GET':
        whisky = get_object_or_404(Whisky, pk =whisky_pk)
        selected = Reaction.objects.filter(whisky = whisky)
        flavor_dict = dict()
        top_flavor = dict()
        flavor_counts = 0
        for reaction in selected:
            for tag in reaction.flavor_tag.all():
                flavor_dict[tag.kor_tag] = flavor_dict.get(tag.kor_tag, 0) + 1
                flavor_counts += 1
        if flavor_counts > 0 :
            flavor_list = sorted(flavor_dict.items(), reverse = True, key = lambda item: item[1])
            list_len = len(flavor_list)
            if list_len >= 3:
                list_len = 3
            for i in range(list_len):
                top_flavor[flavor_list[i][0]] = (int(round(((flavor_list[i][1]*100)/flavor_counts), 0)))
        top_tags = {'Flavor_top3': top_flavor}
        return Response(
            {'Top tags for whisky': top_tags}
        )


#ReactionComment
class ReactionCommentListAPIView(generics.ListAPIView):
    serializer_class = ReactionCommentSerializer
    queryset = ReactionComment.objects.all()

    def get_object(self, queryset = None):
        pk = self.kwargs['reaction_pk']
        return ReactionComment.objects.filter(review = pk)

class ReactionCommentCreateAPIView(generics.CreateAPIView):
    serializer_class = ReactionCommentSerializer
    serializer = ReactionCommentSerializer

    def perform_create(self, serializer):
        serializer.save(user = self.request.user.id, review = self.kwargs['reaction_pk'])
        return Response(
            {'message':'Comment posted'})


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
                follower_new = Profile.objects.get(id = request.data['follower'])
                following_new = Profile.objects.get(id = request.data['following'])
                Follow.objects.create(follower = follower_new, following = following_new)
                #serializer = self.get_serializer(data=request.data)
                #serializer.is_valid(raise_exception=True)
                #serializer.save()
                return Response(
                        {"detail": ("Successfully Followed")}
                        )
        else:
            return Response(
                    {"detail": ("Bad Request")}
                    )

class FollowingDetailView(generics.ListAPIView):
    serializer_class = FollowingSerializer

    def get_queryset(self):
        queryset = Follow.objects.all()
        pk = self.kwargs['profile_pk']
        return Follow.objects.filter(follower_id = pk)

class FollowerDetailView(generics.ListAPIView):
    serializer_class = FollowerSerializer

    def get_queryset(self):
        queryset = Follow.objects.all()
        pk = self.kwargs['profile_pk']
        return Follow.objects.filter(following_id = pk)

#Profile - Collection & Wishlist
class CollectionAPIView(generics.ListAPIView):
    serializer_class = CollectionViewSerializer
    queryset = Collection.objects.all()

    def get_object(self):
        pk = self.kwargs['pk']
        return Collection.objects.filter(user = pk)

class CollectionCreateAPIView(generics.CreateAPIView):
    serializer_class = CollectionSerializer
    serializer = CollectionSerializer

    def perform_create(self, serializer):
        if Collection.objects.filter(user=self.request.user.id, whisky=self.request.data['whisky']).exists():
            return Response(
                    {"detail": ("Already Existing in your Collection")},
                    status=status.HTTP_400_BAD_REQUEST,
                    )
        else:
            # +1 credit point
            profile = self.request.user.profile
            credit = self.request.user.profile.credit
            credit += 1
            profile.credit = credit
            profile.save()
            # end function
            serializer.save(user_id = self.request.user.id)
            return Response(
                    {"detail": ("Successfully added in your Collection (+1 Credit Point!)")},
                    status=status.HTTP_200_OK,
                    )

class WishlistAPIView(generics.ListAPIView):
    serializer_class = WishlistViewSerializer
    queryset = Wishlist.objects.all()

    def get_object(self):
        pk = self.kwargs['pk']
        return Wishlist.objects.filter(user = pk)

class WishlistCreateAPIView(generics.CreateAPIView):
    serializer_class = WishlistSerializer
    serializer = WishlistSerializer

    def perform_create(self, serializer):
        if Wishlist.objects.filter(user=self.request.user.id, whisky=self.request.data['whisky']).exists():
            return Response(
                    {"detail": ("Already Existing in your Wishlist")},
                    status=status.HTTP_400_BAD_REQUEST,
                    )
        else:
            # +1 credit point
            profile = self.request.user.profile
            credit = self.request.user.profile.credit
            credit += 1
            profile.credit = credit
            profile.save()
            # end function
            serializer.save(user_id = self.request.user.id)
            return Response(
                    {"detail": ("Successfully added in your Collection (+1 Credit Point!)")},
                    status=status.HTTP_200_OK,
            )

#Main
class MainRecentReactionView(generics.ListAPIView):
    ordering_fields = ['modified_at']
    #Pagination
    pagination_class = PageSize5Pagination
    permission_classes = [AllowAny]
    serializer_class = ReactionListSerializer

    def get_queryset(self):
        RecentReaction = Reaction.objects.order_by('-modified_at')
        return RecentReaction

class MainPopularWhiskyView(generics.ListAPIView):
    ordering_fields = ['rating_counts']
    #Pagination
    pagination_class = PageSize5Pagination
    permission_classes = [AllowAny]
    serializer_class = WhiskySerializer

    def get_queryset(self):
        RecentWhisky = Whisky.objects.order_by('-rating_counts')
        return RecentWhisky

#Social Login - Naver

class NaverLoginView(View):
    def get(self, request):
        access_token = request.headers["Authorization"]
        headers = ({'Authorization' : f"Bearer {access_token}"})
        #Authorization(프론트에서 받은 토큰)을 이용해서 회원정보를 확인하는 API 주소
        url = "https://openapi.naver.com/v1/nid/me"
        #API를 요청하여 회원 정보를 response에 저장
        response = requests.request("POST", url, headers=headers)
        #유저 정보를 json화하여 변수에 저장
        user = response.json()

        if SocialAccount.objects.filter(uid = user['response']['id']).exists():
            user_info = SocialAccount.objects.get(uid = user['response']['id'])
            #jwt token 발행
            encoded_jwt = jwt.encode({'id':user_info.id}, SECRET_KEY, algorithm = 'HS256')

            #jwt토큰, user_pk을 프론트엔드에 전달
            return JsonResponse({
                'access_token' : encoded_jwt.decode('UTF-8'),
                'user_id': user_info.id,
                }, status = 200)

        else:
            if User.objects.filter(username = user['response']['email']).exists():
                return Response(
                        {"detail": ("이미 가입된 이메일 계정입니다")},
                        status = status.HTTP_400_BAD_REQUEST
                        )
            else:
                new_user = User.objects.create_user(username = user['response']['email'], password = None, email = user['response']['email'], is_active = True)
                new_user.save()

                new_user_info = SocialAccount(
                        user_id = new_user.id,
                        uid = user['response']['id'],
                        provider = SocialApp.objects.get(provider = 'naver')
                        )
                new_user_info.save()

                encoded_jwt = jwt.encode({'id': new_user_info.id}, SECRET_KEY, algorithm = 'HS256')
                none_member_type = 1
                return JsonResponse({
                    'access_token': encoded_jwt.decode('UTF-8'),
                    'user_id': new_user_info.id,
                    }, status = 200)
