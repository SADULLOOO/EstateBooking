from rest_framework import serializers 
from .models import  User, Profile

class RegisterSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('phone_number', 'username', 'password', 'confirm_password')

    def validate(self, attrs):
        phone_number = attrs.get('phone_number') or ''
        username = attrs.get('username') or ''

        if not phone_number and not username:
            raise serializers.ValidationError(
                {"phone_number": "Рақами телефон ё номи корбар лозим аст."}
            )
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Паролхо мувофиқат намекунанд."})
        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError({"phone_number": "Корбар бо ин рақами телефон аллакай сабт шудааст."})
        if username and User.objects.filter(username=username).exists():
            raise serializers.ValidationError({"username": "Ин номи корбар аллакай банд аст."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        phone_number = validated_data.get('phone_number') or None
        username = validated_data.get('username') or phone_number
        user = User.objects.create_user(
            username=username,
            phone_number=phone_number,
            password=validated_data['password'],
        )
        return user


class LoginSerializer(serializers.Serializer):
    # Accepts either a phone number or a username - resolved in LoginView.
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'date_joined']


class ChangeRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['address', 'avatar']
