from django.contrib import admin
from .models import User, Instrument, Transaction, Order, Balance

admin.site.register(User)
admin.site.register(Instrument)
admin.site.register(Transaction)
admin.site.register(Order)
admin.site.register(Balance)
