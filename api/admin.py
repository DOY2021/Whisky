from django.contrib import admin
from api.models import Profile, Whisky, Friend, FriendRequest

#CustomUserAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

class ProfileInline(admin.StackedInline):
	model = Profile
	con_delete = False

class FriendInline(admin.StackedInline):
    model = Friend
    fk_name = "friends"
    con_delete = False

class FriendRequestFromInline(admin.StackedInline):
    model = FriendRequest
    fk_name = "from_user"
    con_delete = False

class FriendRequestToInline(admin.StackedInline):
    model = FriendRequest
    fk_name = "to_user"
    con_delete = False

class CustomUserAdmin(UserAdmin):
	inlines = (ProfileInline, FriendInline, FriendRequestFromInline, FriendRequestToInline)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	list_display = ("user","nickname", "bio", "profile_photo")

@admin.register(Whisky)
class WhiskyAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "whisky_detail", "whisky_region", "whisky_rating")
	search_fiels = ["name", "whisky_region"]

