from rest_framework import serializers
from .models import User, Instrument, Order, Transaction

# Схема для регистрации нового пользователя


class NewUserSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=3)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'role', 'api_key']


class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = ['ticker', 'name']


class TransactionSerializer(serializers.ModelSerializer):
    instrument = InstrumentSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = ['instrument', 'amount', 'price', 'timestamp']

# Сериализатор для лимитного ордера (обязательное поле price)


class LimitOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'ticker', 'direction',
                  'qty', 'price', 'status', 'filled']

    def create(self, validated_data):
        validated_data['order_type'] = 'LIMIT'
        return super().create(validated_data)

# Сериализатор для рыночного ордера (без поля price)


class MarketOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'ticker', 'direction', 'qty', 'status']

    def create(self, validated_data):
        validated_data['order_type'] = 'MARKET'
        return super().create(validated_data)

# Сериализаторы для депозитов и снятий


class DepositSerializer(serializers.Serializer):
    ticker = serializers.CharField()
    amount = serializers.IntegerField(min_value=1)


class WithdrawSerializer(serializers.Serializer):
    ticker = serializers.CharField()
    amount = serializers.IntegerField(min_value=1)
