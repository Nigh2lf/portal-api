"""Bases reutilizáveis e models de infraestrutura do app ``core``.

Este módulo concentra coisas que **raramente** mudam — bases abstratas e
tabelas internas de auditoria —, deixando [core/models.py](models.py) focado
nos models de domínio.

Conteúdo:

- **Bases abstratas (sem tabela própria):**
  - ``AbstractModel`` — UUID PK + timestamps + ``created_by``/``updated_by``.
  - ``SoftDeleteMixin`` (+ manager/queryset) — soft delete opt-in.
- **Models de infraestrutura (não mexa sem motivo):**
  - ``LogRequest`` — log de cada request HTTP (preenchido pelo middleware).
  - ``LogModelChange`` — auditoria de CREATE/UPDATE/DELETE em models.

FKs para ``User`` usam string (``"core.User"``) para evitar import circular:
este módulo é carregado por ``core/models.py`` antes do ``User`` ser definido.
``Meta.app_label = "core"`` é explícito porque os models concretos estão fora
de ``models.py``.
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone

# =============================================================================
# Bases abstratas
# =============================================================================


class AbstractModel(models.Model):
    """Timestamps + auditoria de autoria.

    ``created_by`` / ``updated_by`` são populados automaticamente pelo
    ``BaseModelViewSet`` (``perform_create`` / ``perform_update``) quando o usuário
    da request está autenticado. Em fluxos sem request (shell, management
    commands, jobs, seeds, migrations) os campos ficam ``NULL``.

    Use ``SoftDeleteMixin`` para habilitar soft delete.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "core.User",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        "core.User",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True
        ordering = ("-created_at",)


class UnindexedAuditMixin(models.Model):
    """``created_by`` / ``updated_by`` sem índice nem constraint, para tabelas de alto volume.

    Liste antes de ``AbstractModel``. Nessas tabelas (fotos, taxas, estatísticas) a autoria
    quase nunca é preenchida e ninguém filtra por ela, mas cada linha gravada mantinha dois
    índices que disputavam a memória do MySQL com as leituras do site.
    """

    created_by = models.ForeignKey(
        "core.User",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_created",
        db_index=False,
        db_constraint=False,
    )
    updated_by = models.ForeignKey(
        "core.User",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_updated",
        db_index=False,
        db_constraint=False,
    )

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Manager padrão que continua retornando todos os registros.

    Use ``Model.objects.alive()`` para filtrar não excluídos.
    """


class SoftDeleteMixin(models.Model):
    """Mixin opt-in: aplique apenas em models que precisam de soft delete."""

    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey("core.User", null=True, blank=True, on_delete=models.SET_NULL)

    objects = SoftDeleteManager()

    class Meta:
        abstract = True

    def delete(self, deleted_by=None, hard=False, *args, **kwargs):
        if hard:
            return super().delete(*args, **kwargs)
        self.deleted_at = timezone.now()
        if deleted_by is not None:
            self.deleted_by = deleted_by
        update_fields = ["deleted_at", "deleted_by"]
        # Se o model também possui ``is_active`` (ex.: User), desativa em conjunto.
        if hasattr(self, "is_active"):
            self.is_active = False
            update_fields.append("is_active")
        self.save(update_fields=update_fields)

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        update_fields = ["deleted_at", "deleted_by"]
        if hasattr(self, "is_active"):
            self.is_active = True
            update_fields.append("is_active")
        self.save(update_fields=update_fields)


# =============================================================================
# Models de infraestrutura — auditoria
# =============================================================================


class LogRequest(models.Model):
    """Log de cada request HTTP processada (preenchido pelo
    ``RequestLoggerMiddleware``).

    `path` guarda apenas a URL (sem querystring), o que facilita agregação
    e busca. `params` guarda a querystring serializada como JSON. `data`
    guarda o body JSON (com chaves sensíveis redatadas).

    A tabela cresce rápido: ``manage.py purge_logs`` apaga registros com mais de
    ``LOG_REQUESTS_RETENTION_DAYS`` (30) dias.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(blank=True, null=True)
    method = models.CharField(max_length=10)
    path = models.TextField(blank=True, null=True)  # noqa: DJ001 - request pode não ter path resolvido
    execution_time = models.FloatField(blank=True, null=True)
    status_code = models.IntegerField(blank=True, null=True)
    data = models.TextField(blank=True, null=True)  # noqa: DJ001 - JSON serializado opcional
    ip = models.CharField(max_length=45, blank=True, default="")
    params = models.TextField(blank=True, null=True)  # noqa: DJ001 - querystring serializada opcional
    user_agent = models.TextField(blank=True, null=True)  # noqa: DJ001 - opcional
    curl = models.TextField(blank=True, null=True)  # noqa: DJ001 - opcional
    user = models.ForeignKey(
        "core.User",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="request_logs",
    )
    user_email = models.CharField(max_length=255, blank=True, default="")
    cache_status = models.CharField(
        max_length=4,
        blank=True,
        default="",
        help_text="HIT quando todo o cache público consultado na request acertou, MISS se algum foi ao banco, vazio se não usou cache.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status_code"]),
            models.Index(fields=["method"]),
            models.Index(fields=["cache_status"]),
        ]

    def __str__(self):
        return f"{self.method} {self.path} -> {self.status_code}"


class LogModelChange(models.Model):
    """Auditoria de mudanças em models (CREATE/UPDATE/DELETE).

    Preenchida pelos signals em ``core.signals_audit``. Cobre alterações via
    Admin, ORM, management commands e ViewSets — qualquer caminho que chame
    ``Model.save()`` ou ``Model.delete()``.

    Para limitar a tabelas específicas, use a env ``MODEL_AUDIT_MODELS``
    (csv ``app_label.ModelName``). Default: ``core.User``.

    Tabela é purgada por ``manage.py purge_logs`` após
    ``MODEL_AUDIT_RETENTION_DAYS`` (default 30) dias.
    """

    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app_label = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    action = models.CharField(max_length=10, choices=Action.choices)
    changes = models.JSONField(blank=True, null=True)
    actor = models.ForeignKey(
        "core.User",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="audit_actions",
    )
    actor_email = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "core"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["app_label", "model_name", "object_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} {self.app_label}.{self.model_name}({self.object_id})"
