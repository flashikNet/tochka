from django.db import migrations, models
import django.db.models.deletion


def convert_balances_forward(apps, schema_editor):
    """Конвертирует старые JSON балансы в новую структуру"""
    Balance = apps.get_model('exchange', 'Balance')
    User = apps.get_model('exchange', 'User')
    Instrument = apps.get_model('exchange', 'Instrument')
    
    # Создаем USD инструмент, если его нет
    usd_instrument, _ = Instrument.objects.get_or_create(
        ticker='USD',
        defaults={'name': 'US Dollar', 'tick_size': 0.01}
    )
    
    # Сохраняем старые балансы во временную структуру
    old_balances = []
    for balance in Balance.objects.select_related('user'):
        if balance.balances:
            old_balances.append((balance.user, balance.balances))
    
    # Удаляем все старые записи
    Balance.objects.all().delete()
    
    # Создаем новые записи
    for user, balances in old_balances:
        for ticker, amount in balances.items():
            instrument, _ = Instrument.objects.get_or_create(
                ticker=ticker,
                defaults={'name': ticker, 'tick_size': 0.01}
            )
            Balance.objects.create(
                user=user,
                instrument=instrument,
                amount=amount
            )


def convert_balances_backward(apps, schema_editor):
    """Конвертирует балансы обратно в JSON формат"""
    Balance = apps.get_model('exchange', 'Balance')
    User = apps.get_model('exchange', 'User')
    
    # Группируем балансы по пользователям
    user_balances = {}
    for balance in Balance.objects.select_related('user', 'instrument'):
        if balance.user_id not in user_balances:
            user_balances[balance.user_id] = {}
        user_balances[balance.user_id][balance.instrument.ticker] = float(balance.amount)
    
    # Удаляем все текущие записи
    Balance.objects.all().delete()
    
    # Создаем старый формат балансов
    for user_id, balances in user_balances.items():
        Balance.objects.create(
            user_id=user_id,
            balances=balances
        )


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0003_remove_instrument_max_quantity_and_more'),  # 
    ]

    operations = [
        # 1. Изменяем тип связи с OneToOne на ForeignKey
        migrations.AlterField(
            model_name='balance',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='exchange.user'
            ),
        ),
        
        # 2. Создаем новые поля
        migrations.AddField(
            model_name='balance',
            name='amount',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=20),
        ),
        migrations.AddField(
            model_name='balance',
            name='instrument',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='balances',
                to='exchange.instrument'
            ),
        ),
        
        # 3. Конвертируем данные
        migrations.RunPython(
            convert_balances_forward,
            convert_balances_backward,
        ),
        
        # 4. Удаляем старое поле balances
        migrations.RemoveField(
            model_name='balance',
            name='balances',
        ),
        
        # 5. Делаем новые поля обязательными
        migrations.AlterField(
            model_name='balance',
            name='instrument',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='balances',
                to='exchange.instrument'
            ),
        ),
        
        # 6. Добавляем индекс и ограничение уникальности
        migrations.AlterUniqueTogether(
            name='balance',
            unique_together={('user', 'instrument')},
        ),
        migrations.AddIndex(
            model_name='balance',
            index=models.Index(
                fields=['user', 'instrument'],
                name='exchange_ba_user_id_e4c0ac_idx'
            ),
        ),
    ] 