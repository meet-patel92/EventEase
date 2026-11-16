from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "password",
            "password_confirm",
            "role",
            "first_name",
            "last_name",
            "phone",
            "date_of_birth",
        )
        # Public registration must never be able to assign privileged roles.
        read_only_fields = ("id", "role")

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        candidate_user = User(
            username=attrs.get("username", ""),
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate_user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError(
                    "Invalid email or password."
                )
            if not user.is_active:
                raise serializers.ValidationError(
                    "User account is disabled."
                )
            attrs["user"] = user
        else:
            raise serializers.ValidationError(
                "Must include both email and password."
            )
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "role",
            "first_name",
            "last_name",
            "phone",
            "date_of_birth",
            "is_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "role", "created_at", "updated_at")


class UserRegistrationResponseSerializer(serializers.Serializer):
    """Serializer for user registration response."""

    user = UserSerializer(read_only=True)
    tokens = serializers.DictField(child=serializers.CharField(), read_only=True)
    message = serializers.CharField(read_only=True)


class UserLoginResponseSerializer(serializers.Serializer):
    """Serializer for user login response."""

    user = UserSerializer(read_only=True)
    tokens = serializers.DictField(child=serializers.CharField(), read_only=True)
    message = serializers.CharField(read_only=True)
