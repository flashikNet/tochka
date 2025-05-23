from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction
from .serializers import (
    NewUserSerializer, UserSerializer, InstrumentSerializer,
    DepositSerializer, WithdrawSerializer, LimitOrderSerializer,
    MarketOrderSerializer, TransactionSerializer, CreateOrderResponseSerializer
)
from .models import User, Instrument, Order, Transaction, Balance, OrderBook
from django.core.exceptions import ValidationError

# Вспомогательная функция для аутентификации
def get_authenticated_user(request):
    """
    Аутентифицирует пользователя по API ключу из заголовка Authorization.
    Формат заголовка: TOKEN <api_key>
    """
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
    """Регистрация нового пользователя и создание начального баланса"""
    
    def post(self, request):
        serializer = NewUserSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data['name']
            user = User.objects.create(name=name)
            return Response(UserSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

# 2. Список доступных инструментов (public)
class InstrumentListView(APIView):
    """Публичный эндпоинт для получения списка доступных инструментов"""
    
    def get(self, request):
        instruments = Instrument.objects.all()
        serializer = InstrumentSerializer(instruments, many=True)
        return Response(serializer.data)

# 3. Получение ордербука по инструменту
class OrderbookView(APIView):
    """Получение актуального ордербука по указанному инструменту"""
    
    def get(self, request, ticker):
        try:
            Instrument.objects.get(ticker=ticker)
            orderbook = OrderBook.get_order_book(ticker)
            return Response(orderbook)
        except Instrument.DoesNotExist:
            return Response(
                {"detail": "Instrument not found"},
                status=status.HTTP_404_NOT_FOUND
            )

# 4. История сделок (демо-данные)


class TransactionHistoryView(APIView):
    """История сделок по инструменту"""
    
    def get(self, request, ticker):
        transactions = Transaction.objects.filter(ticker=ticker)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

# 5. Получение баланса (требуется авторизация)
class BalanceView(APIView):
    """Получение баланса пользователя по всем активам"""
    
    def get(self, request):
        user = get_authenticated_user(request)
        if user is None:
            return Response(
                {"detail": "Неверный или отсутствующий API ключ"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        balances = Balance.get_user_balances(user)
        return Response(balances)

# 6. Депозит (обновление баланса)
class DepositView(APIView):
    """Пополнение баланса пользователя"""
    
    def post(self, request):
        user = get_authenticated_user(request)
        if user is None:
            return Response(
                {"detail": "Неверный или отсутствующий API ключ"},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        serializer = DepositSerializer(data=request.data)
        if serializer.is_valid():
            ticker = serializer.validated_data['ticker']
            amount = serializer.validated_data['amount']
            
            try:
                user.update_balance(ticker, amount)
                return Response({"success": True})
            except Instrument.DoesNotExist:
                return Response(
                    {"detail": "Invalid ticker"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except ValidationError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

# 7. Снятие средств (вывод)
class WithdrawView(APIView):
    """Вывод средств с баланса пользователя"""
    
    def post(self, request):
        user = get_authenticated_user(request)
        if user is None:
            return Response(
                {"detail": "Неверный или отсутствующий API ключ"},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        serializer = WithdrawSerializer(data=request.data)
        if serializer.is_valid():
            ticker = serializer.validated_data['ticker']
            amount = serializer.validated_data['amount']
            
            try:
                user.update_balance(ticker, -amount)
                return Response({"success": True})
            except Instrument.DoesNotExist:
                return Response(
                    {"detail": "Invalid ticker"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except ValidationError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

# 8. Создание ордера и список ордеров (требуется авторизация)
class OrderView(APIView):
    """Создание новых ордеров и получение списка ордеров пользователя"""
    
    def post(self, request):
        """
        Создание нового ордера (лимитного или рыночного).
        Проверяет наличие достаточного баланса и пытается исполнить ордер.
        """
        user = get_authenticated_user(request)
        if user is None:
            return Response(
                {"detail": "Неверный или отсутствующий API ключ"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        data = request.data.copy()
        
        # Проверка существования инструмента
        try:
            instrument = Instrument.objects.get(ticker=data['ticker'])
        except Instrument.DoesNotExist:
            return Response(
                {"detail": "Instrument not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Проверка баланса для SELL ордеров
        if data['direction'] == 'SELL':
            if user.get_balance(data['ticker']) < data['qty']:
                return Response(
                    {"detail": "Insufficient balance"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Проверка баланса USD для BUY лимитных ордеров
        price = data.get('price', Order.objects.filter(ticker=data['ticker'], direction='BUY').order_by('-price').first().price)
        if data['direction'] == 'BUY':
            required_balance = data['qty'] * price
            if user.get_balance('USD') < required_balance:
                return Response(
                    {"detail": "Insufficient USD balance"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Создание и исполнение ордера
        with transaction.atomic():
            order_data = {
                'user': user,
                'ticker': data['ticker'],
                'direction': data['direction'],
                'qty': data['qty'],
                'price': data.get('price'),
                'order_type': "LIMIT" if 'price' in data else "MARKET"
            }

            order = Order.objects.create(**order_data)

            try:
                transactions = OrderBook.match_orders(order)
                
                # Отмена рыночного ордера при недостаточной ликвидности
                if order.price is None and order.status != 'EXECUTED':
                    order.status = 'CANCELLED'
                    order.save()
                    return Response(
                        {"detail": "Not enough liquidity for market order"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                return Response({
                    "success": True,
                    "order_id": str(order.id)
                })

            except Exception as e:
                order.status = 'CANCELLED'
                order.save()
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

    def get(self, request):
        """Получение списка всех ордеров пользователя"""
        user = get_authenticated_user(request)
        if user is None:
            return Response(
                {"detail": "Неверный или отсутствующий API ключ"},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        orders = Order.objects.filter(user=user)
        response_data = []
        
        for order in orders:
            serializer = (
                MarketOrderSerializer(order)
                if order.price is None
                else LimitOrderSerializer(order)
            )
            if serializer.data is not None:
                response_data.append(serializer.data)
                
        return Response(response_data)

# 9. Детализация и отмена ордера (требуется авторизация)


class OrderDetailView(APIView):
    """Управление отдельным ордером: просмотр деталей и отмена"""
    
    def get(self, request, order_id):
        """Получение детальной информации об ордере"""
        user = get_authenticated_user(request)
        if user is None:
            return Response(
                {"detail": "Неверный или отсутствующий API ключ"},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        try:
            order = Order.objects.get(id=order_id, user=user)
            serializer = (
                LimitOrderSerializer(order)
                if order.order_type == 'LIMIT'
                else MarketOrderSerializer(order)
            )
            return Response(serializer.data)
            
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, order_id):
        """Отмена ордера"""
        user = get_authenticated_user(request)
        if user is None:
            return Response(
                {"detail": "Неверный или отсутствующий API ключ"},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        try:
            order = Order.objects.get(id=order_id, user=user)
            order.status = "CANCELLED"
            order.save()
            return Response({"success": True})
            
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

# 10. Админ: добавление инструмента (требуется авторизация и роль ADMIN)


class AdminInstrumentView(APIView):
    """Административный интерфейс для управления инструментами"""
    
    def post(self, request):
        """Добавление нового инструмента"""
        user = get_authenticated_user(request)
        if user is None or user.role != 'ADMIN':
            return Response(
                {"detail": "Доступ запрещён"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = InstrumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True})
            
        return Response(
            serializer.errors,
            status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

# 11. Админ: удаление инструмента (требуется авторизация и роль ADMIN)


class AdminInstrumentDetailView(APIView):
    """Административный интерфейс для управления отдельным инструментом"""
    
    def delete(self, request, ticker):
        """Удаление инструмента"""
        user = get_authenticated_user(request)
        if user is None or user.role != 'ADMIN':
            return Response(
                {"detail": "Доступ запрещён"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        try:
            instrument = Instrument.objects.get(ticker=ticker)
            instrument.delete()
            return Response({"success": True})
            
        except Instrument.DoesNotExist:
            return Response(
                {"detail": "Instrument not found"},
                status=status.HTTP_404_NOT_FOUND
            )
