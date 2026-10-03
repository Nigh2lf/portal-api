"""Pacote de cron jobs (APScheduler).

Não importa nada aqui no topo — o scheduler é iniciado por
``core.apps.CoreConfig.ready`` somente quando ``RUN_CRON=true``.
"""
