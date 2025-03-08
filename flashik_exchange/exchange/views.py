from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    NewUserSerializer, UserSerializer, InstrumentSerializer,
    DepositSerializer, WithdrawSerializer, LimitOrderSerializer,
    MarketOrderSerializer, TransactionSerializer
)
from .models import User, Instrument, Order, Transaction, Balance

# Вспомогательная функция для аутентификации


def get_authenticated_user(request):
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith("TOKEN "):
        api_key = auth_header.split()[1]
        try:
            return User.objects.get(api_key=api_key)
        except User.DoesNotExist:
            return None
    return None

# 1. Регистрация пользователя


class RegisterView(APIView):
    def post(self, request):
        serializer = NewUserSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data['name']
            user = User.objects.create(name=name)
            # Автоматически создаём баланс для нового пользователя
            Balance.objects.create(user=user, balances={})
            return Response(UserSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

# 2. Список доступных инструментов (public)


class InstrumentListView(APIView):
    def get(self, request):
        instruments = Instrument.objects.all()
        serializer = InstrumentSerializer(instruments, many=True)
        return Response(serializer.data)

# 3. Получение ордербука по инструменту (демо-данные)


class OrderbookView(APIView):
    def get(self, request, ticker):
        orderbook = {
            "bid_levels": [{"price": 100, "qty": 5}],
            "ask_levels": [{"price": 105, "qty": 3}],
        }
        return Response(orderbook)

# 4. История сделок (демо-данные)


class TransactionHistoryView(APIView):
    def get(self, request, ticker):
        transactions = Transaction.objects.filter(instrument__ticker=ticker)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

# 5. Получение баланса (требуется авторизация)


class BalanceView(APIView):
    def get(self, request):
        user = get_authenticated_user(request)
        if user is None:
            return Response({"detail": "Неверный или отсутствующий API ключ"}, status=status.HTTP_401_UNAUTHORIZED)
        balance_obj, created = Balance.objects.get_or_create(
            user=user, defaults={'balances': {}})
        return Response(balance_obj.balances)

# 6. Депозит (обновление баланса)


class DepositView(APIView):
    def post(self, request):
        user = get_authenticated_user(request)
        if user is None:
            return Response({"detail": "Неверный или отсутствующий API ключ"}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = DepositSerializer(data=request.data)
        if serializer.is_valid():
            ticker = serializer.validated_data['ticker']
            amount = serializer.validated_data['amount']
            balance_obj, created = Balance.objects.get_or_create(
                user=user, defaults={'balances': {}})
            balances = balance_obj.balances
            balances[ticker] = balances.get(ticker, 0) + amount
            balance_obj.balances = balances
            balance_obj.save()
            return Response({"success": True})
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

# 7. Снятие средств (вывод)


class WithdrawView(APIView):
    def post(self, request):
        user = get_authenticated_user(request)
        if user is None:
            return Response({"detail": "Неверный или отсутствующий API ключ"}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = WithdrawSerializer(data=request.data)
        if serializer.is_valid():
            ticker = serializer.validated_data['ticker']
            amount = serializer.validated_data['amount']
            balance_obj, created = Balance.objects.get_or_create(
                user=user, defaults={'balances': {}})
            balances = balance_obj.balances
            current_balance = balances.get(ticker, 0)
            if current_balance < amount:
                return Response({"detail": "Недостаточно средств"}, status=status.HTTP_400_BAD_REQUEST)
            balances[ticker] = current_balance - amount
            balance_obj.balances = balances
            balance_obj.save()
            return Response({"success": True})
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

# 8. Создание ордера и список ордеров (требуется авторизация)


class OrderView(APIView):
    def post(self, request):
        user = get_authenticated_user(request)
        if user is None:
            return Response({"detail": "Неверный или отсутствующий API ключ"}, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data
        # Если присутствует поле price – лимитный ордер, иначе рыночный
        if 'price' in data:
            serializer = LimitOrderSerializer(data=data)
        else:
            serializer = MarketOrderSerializer(data=data)
        if serializer.is_valid():
            order = serializer.save(user=user)
            return Response({"success": True, "order_id": str(order.id)})
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    def get(self, request):
        user = get_authenticated_user(request)
        if user is None:
            return Response({"detail": "Неверный или отсутствующий API ключ"}, status=status.HTTP_401_UNAUTHORIZED)
        orders = Order.objects.filter(user=user)
        # Для демонстрации можно объединить оба типа ордеров
        # Здесь используется лимитный сериализатор, но можно сделать и универсальный
        serializer = LimitOrderSerializer(orders, many=True)
        return Response(serializer.data)

# 9. Детализация и отмена ордера (требуется авторизация)


class OrderDetailView(APIView):
    def get(self, request, order_id):
        user = get_authenticated_user(request)
        if user is None:
            return Response({"detail": "Неверный или отсутствующий API ключ"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            order = Order.objects.get(id=order_id, user=user)
            if order.order_type == 'LIMIT':
                serializer = LimitOrderSerializer(order)
            else:
                serializer = MarketOrderSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, order_id):
        user = get_authenticated_user(request)
        if user is None:
            return Response({"detail": "Неверный или отсутствующий API ключ"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            order = Order.objects.get(id=order_id, user=user)
            order.status = "CANCELLED"
            order.save()
            return Response({"success": True})
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

# 10. Админ: добавление инструмента (требуется авторизация и роль ADMIN)


class AdminInstrumentView(APIView):
    def post(self, request):
        user = get_authenticated_user(request)
        if user is None or user.role != 'ADMIN':
            return Response({"detail": "Доступ запрещён"}, status=status.HTTP_403_FORBIDDEN)
        serializer = InstrumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True})
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

# 11. Админ: удаление инструмента (требуется авторизация и роль ADMIN)


class AdminInstrumentDetailView(APIView):
    def delete(self, request, ticker):
        user = get_authenticated_user(request)
        if user is None or user.role != 'ADMIN':
            return Response({"detail": "Доступ запрещён"}, status=status.HTTP_403_FORBIDDEN)
        try:
            instrument = Instrument.objects.get(ticker=ticker)
            instrument.delete()
            return Response({"success": True})
        except Instrument.DoesNotExist:
            return Response({"detail": "Instrument not found"}, status=status.HTTP_404_NOT_FOUND)
