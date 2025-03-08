from django.urls import path
from .views import (
    RegisterView, InstrumentListView, OrderbookView, TransactionHistoryView,
    BalanceView, DepositView, WithdrawView, OrderView, OrderDetailView,
    AdminInstrumentView, AdminInstrumentDetailView
)

urlpatterns = [
    path('api/v1/public/register', RegisterView.as_view(), name='register'),
    path('api/v1/public/instrument', InstrumentListView.as_view(), name='instrument_list'),
    path('api/v1/public/orderbook/<str:ticker>', OrderbookView.as_view(), name='orderbook'),
    path('api/v1/public/transactions/<str:ticker>', TransactionHistoryView.as_view(), name='transactions'),
    path('api/v1/balance', BalanceView.as_view(), name='balance'),
    path('api/v1/balance/deposit', DepositView.as_view(), name='deposit'),
    path('api/v1/balance/withdraw', WithdrawView.as_view(), name='withdraw'),
    path('api/v1/order', OrderView.as_view(), name='order'),
    path('api/v1/order/<uuid:order_id>', OrderDetailView.as_view(), name='order_detail'),
    path('api/v1/admin/instrument', AdminInstrumentView.as_view(), name='admin_instrument'),
    path('api/v1/admin/instrument/<str:ticker>', AdminInstrumentDetailView.as_view(), name='admin_instrument_detail'),
]
