#?
from __future__ import unicode_literals, print_function

#
from django.contrib.auth import get_user_model, authenticate
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode as uid_decoder
from django.utils.http import urlsafe_base64_encode as uid_encoder
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text, force_bytes

from rest_framework import serializers, exceptions
from rest_framework.exceptions import ValidationError

from django.shortcuts import render, get_object_or_404

#from posts.models import Post
from api.models import Profile, Whisky, Reaction, Follow, Tag, ReactionComment

#CustomTokenSerializer
from rest_auth.models import TokenModel
from rest_auth.utils import import_callable
from rest_auth.serializers import UserDetailsSerializer as DefaultUserDetailsSerializer

#Profile - Collection & Whisky
from api.models import Collection, Wishlist

#Images
from api.models import WhiskyImage, ReactionImage

#Profile - WhiskyDraft
#from api.models import WhiskyDraft

#Profile - Menu
#from api.models import Menu


# This is to allow you to override the UserDetailsSerializer at any time.
# If you're sure you won't, you can skip this and use DefaultUserDetailsSerializer directly
rest_auth_serializers = getattr(settings, 'REST_AUTH_SERIALIZERS', {})
UserDetailsSerializer = import_callable(
    rest_auth_serializers.get('USER_DETAILS_SERIALIZER', DefaultUserDetailsSerializer)
)

# Get UserModel
from django.contrib.auth.models import User
UserModel = get_user_model()


class CustomLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(style={'input_type': 'password'})

    def authenticate(self, **kwargs):
        return authenticate(self.context['request'], **kwargs)

    def _validate_email(self, email, password):
        user = None

        if email and password:
            user = self.authenticate(email=email, password=password)
        else:
            msg = _('이메일과 비밀번호를 입력해주세요.')
            raise exceptions.ValidationError(msg)

        return user

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        user = None

        if 'allauth' in settings.INSTALLED_APPS:
            from allauth.account import app_settings

            # Authentication through email
            if app_settings.AUTHENTICATION_METHOD == app_settings.AuthenticationMethod.EMAIL:
                user = self._validate_email(email, password)

        if user:
            #비밀번호 틀렸을 경우

            if not user.is_active:
                msg = _('계정이 비활성화되었습니다. 관리자에게 문의해주세요.')
                raise exceptions.ValidationError(msg)

        else:
            msg = _('가입된 정보가 없습니다. 이메일과 비밀번호를 확인해주세요.')
            raise exceptions.ValidationError(msg)

        # If required, is the email verified?
        if 'rest_auth.registration' in settings.INSTALLED_APPS:
             from allauth.account import app_settings
             if app_settings.EMAIL_VERIFICATION == app_settings.EmailVerificationMethod.MANDATORY:
                email_address = user.emailaddress_set.get(email=user.email)
                if not email_address.verified:
                    raise serializers.ValidationError(_('이메일을 인증해주세요.'))

        attrs['user'] = user
        return attrs

class CustomTokenSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TokenModel
        fields = ('key', 'user', 'user_id')

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    password_reset_form_class = PasswordResetForm

    def validate_email(self, value):
        self.reset_form = self.password_reset_form_class(data=self.initial_data)
        if not self.reset_form.is_valid():
            raise serializers.ValidationError(_('Error'))

        ###### FILTER YOUR USER MODEL ######
        if not UserModel.objects.filter(email=value).exists():

            raise serializers.ValidationError(_('Invalid e-mail address'))
        return value

    def save(self):
        request = self.context.get('request')
        opts = {
            'use_https': request.is_secure(),
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL'),

            ###### USE YOUR HTML FILE ######
            'email_template_name': 'email/user_reset_password.html',

            'request': request,
        }
        self.reset_form.save(**opts)

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset e-mail.
    """
    new_password1 = serializers.CharField(max_length=128)
    new_password2 = serializers.CharField(max_length=128)
    uid = serializers.CharField()
    #Front url parameter <uid>
    token = serializers.CharField()
    #Front url parameter <token>

    set_password_form_class = SetPasswordForm

    def custom_validation(self, attrs):
        pass

    #def validate(self, attrs):
    #    self._errors = {}
    #    request_object = self.context['request']
    #    uidb64 = request_object.query_params.get('uidb64')
    #    uid = force_text(uid_decoder('Mg'))
    #    #retrieve uid info in 'MQ' space
    #    self.user = UserModel._default_manager.get(pk=uid)

    #    self.set_password_form = self.set_password_form_class(
    #            user=self.user, data=attrs
    #            )
    #    if not self.set_password_form.is_valid():
    #        raise serializers.ValidationError(self.set_password_form.error)

    #    return attrs

    def validate(self, attrs):
        self._errors = {}

        # Decode the uidb64 to uid to get User object
        try:
            uid = force_text(uid_decoder(attrs['uid']))
            self.user = UserModel._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            raise ValidationError({'uid': ['Invalid value']})

        self.custom_validation(attrs)
        # Construct SetPasswordForm instance
        self.set_password_form = self.set_password_form_class(
            user=self.user, data=attrs
        )
        if not self.set_password_form.is_valid():
            raise serializers.ValidationError(self.set_password_form.errors)
        if not default_token_generator.check_token(self.user, attrs['token']):
            raise ValidationError({'token': ['Invalid value']})

        return attrs

    def save(self):
        return self.set_password_form.save()


#Profile
class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    is_follower = serializers.StringRelatedField(read_only = True, many = True)
    follower_count = serializers.IntegerField(source = "is_follower.count", read_only = True)
    is_following = serializers.StringRelatedField(read_only = True, many = True)
    following_count = serializers.IntegerField(source = "is_following.count", read_only = True)

    class Meta:
        model = Profile
        fields = ("id", "user", "nickname", "bio", "profile_photo", "is_follower", "follower_count", "is_following", "following_count")

class ProfileCreateSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Profile
        fields = ("user", "id", "nickname", "bio", "profile_photo")

        def create(self, validated_data):
            profile = Profile.objects.create(user = user)
            return profile


class ProfilePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("profile_photo", )

#Profile - Whisky List (Full)
class MenuFullSerializer(serializers.ModelSerializer):
    #"my_ratings" field
    my_ratings = serializers.SerializerMethodField()
    def get_my_ratings(self, obj):
        request = self.context['request']
        url = request.build_absolute_uri()
        profile_pk = int(url.split('/')[-4])
        #How to get pk value from serializer
        if Reaction.objects.filter(whisky = obj).exists():
            my_reaction = Reaction.objects.get(whisky = obj, user_id = profile_pk)
            return my_reaction.nose_rating
            #TBU nose_rating -> average rating (single #)
        else:
            return False

    #"public", "short_list" field
    #public = serializers.BooleanField()
    #short_list = serializers.BooleanField()

    class Meta:
        model = Whisky
        fields = ("id", "name_eng", "region", "cask_type", "alcohol", "my_ratings" )
        read_only_fields = ("id", "name_eng", "region", "cask_type", "alcohol", "my_ratings")
        #"public" should be added as a custom field
        #"my_ratings" should be added as a nested field


#ReactionDB
class ReactionImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReactionImage
        fields = ('id', 'image',)

class ReactionListSerializer(serializers.ModelSerializer):
    whisky_name = serializers.SerializerMethodField()
    def get_whisky_name(self, obj):
        return obj.whisky.name_eng

    userName = serializers.SerializerMethodField()
    def get_userName(self, obj):
        return obj.user.username

    avg_rating = serializers.SerializerMethodField()
    def get_avg_rating(self,obj):
        return round((obj.nose_rating + obj.taste_rating + obj.finish_rating)/3, 2)

    reaction_image = ReactionImageSerializer(many = True, required = False)

    class Meta:
        model = Reaction
        fields = ('id','reaction_image', 'user','userName', 'whisky_name', 'review_title', 'review_body', 'avg_rating', 'nose_rating', 'taste_rating', 'finish_rating', 'flavor_tag', 'created_at','modified_at')
        read_only_fields = ('user',)

class ReactionCreateSerializer(serializers.ModelSerializer):
    whisky_name = serializers.SerializerMethodField()
    def get_whisky_name(self, obj):
        return obj.whisky.name_eng

    userName = serializers.SerializerMethodField()
    def get_userName(self, obj):
        return obj.user.username

    reaction_image = ReactionImageSerializer(many = True, required = False)

    class Meta:
        model = Reaction
        fields = ('id','reaction_image', 'user','userName', 'whisky_name', 'review_title', 'review_body', 'nose_rating', 'taste_rating', 'finish_rating', 'flavor_tag', 'created_at','modified_at')
        read_only_fields = ('user',)

    def create(self, validated_data):
        request = self.context['request']
        url = request.build_absolute_uri()
        whisky_pk = int(url.split('/')[-3])
        cur_whisky = get_object_or_404(Whisky, pk = whisky_pk)
        cur_user = self.context['request'].user

        #if reaction contains images
        if 'reaction_image' in validated_data:
            reaction_image = validated_data.pop('reaction_image')
            reaction_instance = Reaction.objects.create(
                user = cur_user,
                whisky = cur_whisky,
                review_title = request.data.get("review_title"),
                review_body = request.data.get("review_body"),
                nose_rating = request.data.get("nose_rating"),
                taste_rating = request.data.get("taste_rating"),
                finish_rating = request.data.get("finish_rating"),
            )
            flavor_tags = request.data.getlist("flavor_tag")
            for flavor in flavor_tags:
                reaction_instance.flavor_tag.add(int(flavor))
            for img in reaction_image:
                ReactionImage.objects.create(**img, reaction = reaction_instance)

        else:
            reaction_instance = Reaction.objects.create(
                user = cur_user,
                whisky = cur_whisky,
                review_title = request.data.get("review_title"),
                review_body = request.data.get("review_body"),
                nose_rating = request.data.get("nose_rating"),
                taste_rating = request.data.get("taste_rating"),
                finish_rating = request.data.get("finish_rating"),
            )
            flavor_tags = request.data.getlist("flavor_tag")
            for flavor in flavor_tags:
                reaction_instance.flavor_tag.add(int(flavor))
        return reaction_instance

class ReactionUpdateSerializer(serializers.ModelSerializer):
    whisky_name = serializers.SerializerMethodField()
    def get_whisky_name(self, obj):
        return obj.whisky.name_eng

    userName = serializers.SerializerMethodField()
    def get_userName(self, obj):
        return obj.user.username

    reaction_image = ReactionImageSerializer(many = True, required = False)

    class Meta:
        model = Reaction
        fields = ('id','reaction_image', 'user','userName', 'whisky_name', 'review_title', 'review_body', 'nose_rating', 'taste_rating', 'finish_rating', 'flavor_tag', 'created_at','modified_at')
        read_only_fields = ('user',)

    def update(self, instance, validated_data):
        request = self.context['request']
        url = request.build_absolute_uri()
        whisky_pk = int(url.split('/')[-2])
        cur_whisky = get_object_or_404(Whisky, pk = whisky_pk)
        cur_user = self.context['request'].user

        #if reaction contains images
        if 'reaction_image' in validated_data:
            reaction_image = validated_data.pop('reaction_image')
            reaction_instance = Reaction.objects.update(
                user = cur_user,
                whisky = cur_whisky,
                review_title = request.data.get("review_title"),
                review_body = request.data.get("review_body"),
                nose_rating = request.data.get("nose_rating"),
                taste_rating = request.data.get("taste_rating"),
                finish_rating = request.data.get("finish_rating"),
            )
            flavor_tags = request.data.getlist("flavor_tag")
            for flavor in flavor_tags:
                reaction_instance.flavor_tag.add(int(flavor))
            for img in reaction_image:
                ReactionImage.objects.create(**img, reaction = reaction_instance)

        else:
            reaction_instance = Reaction.objects.create(
                user = cur_user,
                whisky = cur_whisky,
                review_title = request.data.get("review_title"),
                review_body = request.data.get("review_body"),
                nose_rating = request.data.get("nose_rating"),
                taste_rating = request.data.get("taste_rating"),
                finish_rating = request.data.get("finish_rating"),
            )
            flavor_tags = request.data.getlist("flavor_tag")
            for flavor in flavor_tags:
                reaction_instance.flavor_tag.add(int(flavor))
        return reaction_instance

#WhiskyDB
class WhiskyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhiskyImage
        fields = ('id', 'image',)


#General Whisky(list, pk) (Linked to WhiskyMainAPIView, WhiskyDetailAPIView) 
class WhiskySerializer(serializers.ModelSerializer):
    reactions = ReactionListSerializer(many = True, read_only = True)
    whisky_image = WhiskyImageSerializer(many = True, required = False)

    whisky_ratings = serializers.SerializerMethodField()                # Whisky Rating is done from whisky-side (changed)
    def get_whisky_ratings(self, obj):
        cur_whisky = obj.id
        reactions = Reaction.objects.filter(whisky_id = cur_whisky)
        reaction_cnt = reactions.count()
        if reaction_cnt <= 0:
            return 0
        total_rating = 0
        for reaction in reactions:
            new_nose_rating = reaction.nose_rating
            new_taste_rating = reaction.taste_rating
            new_fin_rating = reaction.finish_rating
            new_avg_rating = round((new_nose_rating + new_taste_rating + new_fin_rating)/3, 2)
            total_rating += new_avg_rating
        result = round(total_rating/reaction_cnt, 2)
        return result

    rating_counts = serializers.SerializerMethodField()
    def get_rating_counts(self, obj):
        cur_whisky = obj.id
        reactions = Reaction.objects.filter(whisky_id = cur_whisky)
        reaction_cnt = reactions.count()
        return reaction_cnt

    class Meta:
        model = Whisky
        fields = '__all__'
        read_only_fields = ('whisky_image', 'whisky_ratings','rating_counts', 'confirmed')


#Whisky Confirm Serializer
class WhiskyConfirmListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Whisky
        fields = '__all__'


class WhiskyConfirmSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.HyperlinkedIdentityField(view_name = 'whisky_confirm', format = 'json')
    #Work in progress

    class Meta:
        model = Whisky
        fields = ('url', 'id', 'whisky_image', 'name_eng', 'name_kor', 'category',  'region', 'distillery', 'bottler', 'bottling_series', 'age', 'cask_type', 'alcohol',  'size', 'single_cask', 'cask_number', 'non_chillfiltered', 'natural_color', 'independent_whisky', 'whisky_detail', 'confirmed')

class WhiskyUpdateSerializer(serializers.ModelSerializer):
    whisky_image = WhiskyImageSerializer(many = True, required = False)

    class Meta:
        model = Whisky
        fields = ('whisky_image', 'name_eng', 'name_kor', 'category',  'region', 'distillery', 'bottler', 'bottling_series', 'age', 'cask_type', 'alcohol',  'size', 'single_cask', 'cask_number', 'non_chillfiltered', 'natural_color', 'independent_whisky', 'whisky_detail')


#Whisky Create Serializer (Open-type DB function)
class WhiskyCreateSerializer(serializers.ModelSerializer):
    whisky_image = WhiskyImageSerializer(many = True, required = False)

    class Meta:
        model = Whisky
        #Update fields according to DB categories
        fields = ('name_eng', 'name_kor', 'whisky_image', 'category',  'region', 'distillery', 'bottler', 'bottling_series', 'age', 'cask_type', 'alcohol',  'size', 'single_cask', 'cask_strength', 'cask_number', 'non_chillfiltered', 'natural_color', 'independent_whisky', 'whisky_detail')

    def create(self, validated_data):
        current_user = self.context['request'].user

        #if whisky contains images
        if 'whisky_image' in validated_data:
            whisky_image = validated_data.pop('whisky_image')
            whisky_instance = Whisky.objects.create(contributor = current_user, **validated_data)
            for img in whisky_image:
                WhiskyImage.objects.create(**img, whisky = whisky_instance)
            return whisky_instance

        else:
            whisky_instance = Whisky.objects.create(contributor = current_user, **validated_data)
            return whisky_instance

#Whisky Confirm
class WhiskyConfirmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Whisky
        fields = '__all__'

#Reaction + Tag
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('kor_tag',)

#ReactionComment
class ReactionCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReactionComment
        fields = ('created_at', 'modified_at')

#Follow(New)
class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow 
        fields = "__all__"

class FollowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow 
        fields = ("follower",)
        depth = 1
        #add hyperlinked profile url

class FollowingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ("following",)
        depth = 1
        #add hyperlinked profile url

#Profile - Collection & Wishlist
class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ("whisky", "created_at")

class CollectionViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ("whisky", "created_at")
        depth = 1

class WishlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wishlist
        fields = ("whisky", "created_at")

class WishlistViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wishlist
        fields = ("whisky", "created_at")
        depth = 1
