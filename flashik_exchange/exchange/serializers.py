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
        fields = ['name', 'ticker']


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['ticker', 'amount', 'price', 'timestamp']


class LimitOrderBodySerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=['BUY', 'SELL'])
    ticker = serializers.CharField()
    qty = serializers.IntegerField(min_value=1)
    price = serializers.IntegerField(min_value=1)


class MarketOrderBodySerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=['BUY', 'SELL'])
    ticker = serializers.CharField()
    qty = serializers.IntegerField(min_value=1)


class LimitOrderSerializer(serializers.ModelSerializer):
    body = LimitOrderBodySerializer(source='*')
    filled = serializers.IntegerField(default=0)

    class Meta:
        model = Order
        fields = ['id', 'status', 'user_id', 'body', 'filled']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        body = ret.pop('body')
        ret['body'] = {
            'direction': body['direction'],
            'ticker': body['ticker'],
            'qty': body['qty'],
            'price': body['price']
        }
        return ret


class MarketOrderSerializer(serializers.ModelSerializer):
    body = MarketOrderBodySerializer(source='*')

    class Meta:
        model = Order
        fields = ['id', 'status', 'user_id', 'body']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        body = ret.pop('body')
        ret['body'] = {
            'direction': body['direction'],
            'ticker': body['ticker'],
            'qty': body['qty']
        }
        return ret


class CreateOrderResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    order_id = serializers.UUIDField()


class DepositSerializer(serializers.Serializer):
    ticker = serializers.CharField()
    amount = serializers.IntegerField(min_value=1)


class WithdrawSerializer(serializers.Serializer):
    ticker = serializers.CharField()
    amount = serializers.IntegerField(min_value=1)


class OkSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
