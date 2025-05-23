import uuid
import secrets
from django.db import models
from decimal import Decimal
from django.core.exceptions import ValidationError
import re


def generate_api_key():
    return f"key-{secrets.token_hex(16)}"


def validate_ticker(value):
    if not re.match(r'^[A-Z]{2,10}$', value):
        raise ValidationError('Ticker must be 2-10 uppercase letters')


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    role = models.CharField(
        max_length=10,
        choices=[('USER', 'User'), ('ADMIN', 'Admin')],
        default='USER'
    )
    api_key = models.CharField(
        max_length=100, unique=True, default=generate_api_key
    )

    def __str__(self):
        return self.name

    def get_balance(self, ticker):
        """Получает баланс пользователя по тикеру"""
        try:
            return self.balances.get(instrument__ticker=ticker).amount
        except Balance.DoesNotExist:
            return 0

    def update_balance(self, ticker, amount_delta):
        """Изменяет баланс пользователя по тикеру"""
        instrument = Instrument.objects.get(ticker=ticker)
        balance, created = self.balances.get_or_create(
            instrument=instrument,
            defaults={'amount': 0}
        )
        new_amount = balance.amount + amount_delta
        if new_amount < 0:
            raise ValidationError("Insufficient balance")
        balance.amount = new_amount
        balance.save()
        return balance


class Instrument(models.Model):
    ticker = models.CharField(max_length=10, unique=True, validators=[validate_ticker])
    name = models.CharField(max_length=100)
    tick_size = models.DecimalField(max_digits=10, decimal_places=2, default=0.01)
    
    def __str__(self):
        return self.ticker

    def validate_price(self, price):
        if price % self.tick_size != 0:
            raise ValidationError(f"Price must be multiple of tick size {self.tick_size}")
        return price


class Transaction(models.Model):
    ticker = models.CharField(max_length=10, validators=[validate_ticker], default='UNKNOWN')
    amount = models.IntegerField()
    price = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['ticker', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.amount}@{self.price}"


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('NEW', 'New'),
        ('EXECUTED', 'Executed'),
        ('PARTIALLY_EXECUTED', 'Partially Executed'),
        ('CANCELLED', 'Cancelled')
    ]

    ORDER_TYPE_CHOICES = [
        ('MARKET', 'Market'),
        ('LIMIT', 'Limit')
    ]

    DIRECTION_CHOICES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ticker = models.CharField(max_length=10, validators=[validate_ticker])
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)
    direction = models.CharField(max_length=4, choices=DIRECTION_CHOICES)
    price = models.IntegerField(null=True)
    qty = models.IntegerField()
    filled = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='NEW'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['ticker', 'status', 'direction', 'price']),
            models.Index(fields=['user', 'status']),
        ]

    def save(self, *args, **kwargs):
        if not self.id:  # Только для новых ордеров
            if self.order_type == 'MARKET':
                self.price = None
            elif self.price is None:
                raise ValidationError("Price is required for limit orders")
            
            if self.qty <= 0:
                raise ValidationError("Quantity must be positive")
            
            if self.order_type == 'LIMIT' and self.price <= 0:
                raise ValidationError("Price must be positive for limit orders")

        super().save(*args, **kwargs)

    @property
    def remaining_quantity(self):
        return self.qty - self.filled

    def __str__(self):
        return f"{self.direction} {self.qty}@{self.price or 'MARKET'} {self.status}"


class Balance(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='balances'
    )
    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.CASCADE,
        related_name='balances'
    )
    amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)

    class Meta:
        unique_together = ['user', 'instrument']
        indexes = [
            models.Index(fields=['user', 'instrument']),
        ]

    def __str__(self):
        return f"{self.user.name}'s balance of {self.instrument.ticker}: {self.amount}"

    @classmethod
    def get_user_balances(cls, user):
        """Получает все балансы пользователя в формате {ticker: amount}"""
        balances = {}
        for balance in cls.objects.filter(user=user).select_related('instrument'):
            balances[balance.instrument.ticker] = float(balance.amount)
        return balances

    def has_sufficient_balance(self, amount):
        """Проверяет достаточно ли средств"""
        return self.amount >= amount

    def update_balance(self, ticker, amount):
        current = self.amount
        if current + amount < 0:
            raise ValidationError("Insufficient balance")
        self.amount = current + amount
        self.save()


class OrderBook:
    @staticmethod
    def get_order_book(ticker):
        """Получает актуальный стакан заявок"""
        active_orders = Order.objects.filter(
            ticker=ticker,
            status__in=['NEW', 'PARTIALLY_EXECUTED'],
            order_type='LIMIT'
        )

        bids = active_orders.filter(direction='BUY').order_by('-price', 'created_at')
        asks = active_orders.filter(direction='SELL').order_by('price', 'created_at')

        bid_levels = {}
        ask_levels = {}

        for order in bids:
            price = float(order.price)  # Преобразуем в float для корректного сравнения
            if price in bid_levels:
                bid_levels[price] += float(order.remaining_quantity)
            else:
                bid_levels[price] = float(order.remaining_quantity)

        for order in asks:
            price = float(order.price)  # Преобразуем в float для корректного сравнения
            if price in ask_levels:
                ask_levels[price] += float(order.remaining_quantity)
            else:
                ask_levels[price] = float(order.remaining_quantity)

        # Преобразуем обратно в Decimal для возврата
        return {
            'bid_levels': [{'price': Decimal(str(price)), 'qty': Decimal(str(qty))} 
                          for price, qty in sorted(bid_levels.items(), reverse=True)],
            'ask_levels': [{'price': Decimal(str(price)), 'qty': Decimal(str(qty))} 
                          for price, qty in sorted(ask_levels.items())]
        }

    @staticmethod
    def match_orders(new_order):
        """Сопоставляет ордера и создает транзакции"""
        if new_order.order_type == 'LIMIT':
            return OrderBook._match_limit_order(new_order)
        else:
            return OrderBook._match_market_order(new_order)

    @staticmethod
    def _match_limit_order(order):
        """Сопоставляет лимитный ордер"""
        opposite_direction = 'SELL' if order.direction == 'BUY' else 'BUY'
        
        matching_orders = Order.objects.filter(
            ticker=order.ticker,
            direction=opposite_direction,
            status__in=['NEW', 'PARTIALLY_EXECUTED'],
            order_type='LIMIT'
        )

        if order.direction == 'BUY':
            matching_orders = matching_orders.filter(price__lte=order.price).order_by('price', 'created_at')
        else:
            matching_orders = matching_orders.filter(price__gte=order.price).order_by('-price', 'created_at')

        return OrderBook._process_matching(order, matching_orders)

    @staticmethod
    def _match_market_order(order):
        """Сопоставляет рыночный ордер"""
        opposite_direction = 'SELL' if order.direction == 'BUY' else 'BUY'
        
        matching_orders = Order.objects.filter(
            ticker=order.ticker,
            direction=opposite_direction,
            status__in=['NEW', 'PARTIALLY_EXECUTED'],
            order_type='LIMIT'
        ).order_by('price' if order.direction == 'BUY' else '-price', 'created_at')

        return OrderBook._process_matching(order, matching_orders)

    @staticmethod
    def _process_matching(taker_order, matching_orders):
        """Обрабатывает сопоставление ордеров и создает транзакции"""
        transactions = []
        remaining_quantity = taker_order.qty - taker_order.filled

        for maker_order in matching_orders:
            if remaining_quantity <= 0:
                break

            match_quantity = min(remaining_quantity, maker_order.remaining_quantity)
            match_price = maker_order.price

            transaction = Transaction.objects.create(
                ticker=taker_order.ticker,
                amount=match_quantity,
                price=match_price
            )
            transactions.append(transaction)

            # Обновляем количество исполненных ордеров
            maker_order.filled += match_quantity
            taker_order.filled += match_quantity
            remaining_quantity -= match_quantity

            # Обновляем статусы
            for order in [maker_order, taker_order]:
                if order.filled == order.qty:
                    order.status = 'EXECUTED'
                elif order.filled > 0:
                    order.status = 'PARTIALLY_EXECUTED'

            maker_order.save()
            taker_order.save()

            # Обновляем балансы
            if taker_order.direction == 'BUY':
                buyer, seller = taker_order.user, maker_order.user
            else:
                buyer, seller = maker_order.user, taker_order.user

            # Обновляем балансы с учетом сделки
            total_price = match_quantity * match_price
            buyer.update_balance(taker_order.ticker, match_quantity)
            buyer.update_balance('USD', -total_price)
            seller.update_balance(taker_order.ticker, -match_quantity)
            seller.update_balance('USD', total_price)

        return transactions
