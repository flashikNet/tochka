from django.urls import path
from .views import (
    RegisterView, InstrumentListView, OrderbookView, TransactionHistoryView,
    BalanceView, DepositView, WithdrawView, OrderView, OrderDetailView,
    AdminInstrumentView, AdminInstrumentDetailView
)

urlpatterns = [
    path('public/register', RegisterView.as_view(), name='register'),
    path(
        'public/instrument', 
        InstrumentListView.as_view(), 
        name='instrument_list'
    ),
    path(
        'public/orderbook/<str:ticker>', 
        OrderbookView.as_view(), 
        name='orderbook'
    ),
    path(
        'public/transactions/<str:ticker>', 
        TransactionHistoryView.as_view(), 
        name='transactions'
    ),
    path(
        'balance', 
        BalanceView.as_view(), 
        name='balance'
    ),
    path(
        'balance/deposit', 
        DepositView.as_view(), 
        name='deposit'
    ),
    path(
        'balance/withdraw', 
        WithdrawView.as_view(), 
        name='withdraw'
    ),
    path(
        'order', 
        OrderView.as_view(), 
        name='order'
    ),
    path(
        'order/<uuid:order_id>', 
        OrderDetailView.as_view(), 
        name='order_detail'
    ),
    path(
        'admin/instrument', 
        AdminInstrumentView.as_view(), 
        name='admin_instrument'
    ),
    path(
        'admin/instrument/<str:ticker>', 
        AdminInstrumentDetailView.as_view(), 
        name='admin_instrument_detail'
    ),
]
