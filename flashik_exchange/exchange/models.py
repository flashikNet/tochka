import uuid
import secrets
from django.db import models


def generate_api_key():
    return f"key-{secrets.token_hex(16)}"


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


class Instrument(models.Model):
    ticker = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.ticker


class Transaction(models.Model):
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    amount = models.IntegerField()
    price = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.instrument.ticker} {self.amount} @ {self.price}"


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('NEW', 'New'),
        ('EXECUTED', 'Executed'),
        ('PARTIALLY_EXECUTED', 'Partially Executed'),
        ('CANCELLED', 'Cancelled'),
    ]
    ORDER_TYPE_CHOICES = [
        ('LIMIT', 'Limit'),
        ('MARKET', 'Market'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)
    ticker = models.CharField(max_length=10)
    direction = models.CharField(max_length=4, choices=[
                                 ('BUY', 'Buy'), ('SELL', 'Sell')])
    qty = models.IntegerField()
    price = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=ORDER_STATUS_CHOICES, default='NEW')
    filled = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} {self.ticker} {self.direction}"


class Balance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balances = models.JSONField(default=dict)

    def __str__(self):
        return f"Balance of {self.user.name}"
