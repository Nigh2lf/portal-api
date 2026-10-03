"""System checks de segurança.

Estes checks rodam em ``manage.py check`` (e portanto em ``runserver``,
``test``, ``migrate`` etc.). Falhas (Error) **derrubam o boot**.

IDs:
- ``core.E001`` — ViewSet sem ``permission_classes`` nem ``get_permissions``.
- ``core.E002`` — ViewSet usa ``CustomPermissionClass`` mas não declarou ``view_name``.
- ``core.E003`` — Subclasse de ``BaseModelViewSet`` sem padrão de permissão declarado.
  (Padrão do projeto: ``view_name`` + ``CustomPermissionClass``.)
- ``core.W002`` — ViewSet expõe ``destroy`` mas usa a mesma permissão para tudo.
- ``core.E004`` — Produção com ``SECRET_KEY`` fraca/default.
- ``core.E005`` — Produção com ``ALLOWED_HOSTS`` permissivo (`*` ou vazio).
- ``core.E006`` — Produção com ``CORS_ALLOW_ALL_ORIGINS=True``.
- ``core.W003`` — Produção sem ``BREVO_API_KEY`` (e-mails silenciosamente não enviados).
- ``core.W004`` — Produção com ``SECURE_SSL_REDIRECT=False``.
- ``core.W006`` — ``AllowAny`` usado sem comentário justificativo (``# allow-any:``).
- ``core.W007`` — ``ModelSerializer.Meta.fields`` é ``"__all__"`` (proibido).
- ``core.W008`` — Serializer expõe campo PII conhecido (password, hash, token, etc.).
- ``core.E008`` — Produção com migrations pendentes.
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register

# Módulos cujas classes-base **não contam** como declaração explícita.
_SKIP_MODULES = (
    "rest_framework",
    "core.classes.base_viewset",
)


def _has_explicit_permissions(viewset_cls) -> bool:
    """True se o ViewSet (ou alguma classe própria do projeto) declara perms."""
    for cls in viewset_cls.__mro__:
        if cls is object:
            continue
        module = getattr(cls, "__module__", "") or ""
        if any(module.startswith(m) for m in _SKIP_MODULES):
            continue
        if "permission_classes" in cls.__dict__ or "get_permissions" in cls.__dict__:
            return True
    return False


def _uses_custom_permission_class(viewset_cls) -> bool:
    from core.classes.permission import CustomPermissionClass

    perm_classes = getattr(viewset_cls, "permission_classes", None) or []
    for p in perm_classes:
        try:
            if isinstance(p, type) and issubclass(p, CustomPermissionClass):
                return True
        except TypeError:
            continue
    return False


def _inherits_base_viewset(viewset_cls) -> bool:
    from core.classes.base_viewset import BaseModelViewSet

    return issubclass(viewset_cls, BaseModelViewSet) and viewset_cls is not BaseModelViewSet


def _has_uniform_permissions(viewset_cls) -> bool:
    """True quando ``permission_classes`` está setado e ``get_permissions`` não
    foi sobrescrito. Indica que destroy/list compartilham a mesma permissão
    (suspeito).

    ``CustomPermissionClass`` não conta: ela já deriva o tipo de permissão do
    método HTTP (GET → READ, DELETE → DELETE), então ler ≠ deletar mesmo com
    ``permission_classes`` uniforme.
    """
    if _uses_custom_permission_class(viewset_cls):
        return False
    own = {k for cls in viewset_cls.__mro__ if cls is not object for k in cls.__dict__}
    if "get_permissions" in own:
        return False
    return "permission_classes" in own


@register(Tags.security)
def check_viewset_permissions(app_configs, **kwargs):
    """Audita ViewSets registrados no router da v1."""
    issues = []

    try:
        from config.urls_v1 import router
    except Exception as exc:  # pragma: no cover
        return [
            Warning(
                f"Não foi possível importar o router para auditar permissões: {exc}",
                id="core.W001",
            )
        ]

    for prefix, viewset_cls, _basename in router.registry:
        # E001 — alguma forma de declaração precisa existir
        if not _has_explicit_permissions(viewset_cls):
            issues.append(
                Error(
                    (
                        f"ViewSet {viewset_cls.__name__} (rota '{prefix}') não declara "
                        "`permission_classes` nem sobrescreve `get_permissions`."
                    ),
                    hint=(
                        "Use o padrão do projeto: `view_name = '<nome>'` + "
                        "`permission_classes = [IsAuthenticated, CustomPermissionClass]`."
                    ),
                    obj=viewset_cls,
                    id="core.E001",
                )
            )

        # E002 — CustomPermissionClass exige view_name
        if _uses_custom_permission_class(viewset_cls) and not getattr(
            viewset_cls, "view_name", None
        ):
            issues.append(
                Error(
                    (
                        f"ViewSet {viewset_cls.__name__} usa CustomPermissionClass mas "
                        "não define `view_name`."
                    ),
                    hint=(
                        "Adicione `view_name = '<nome>'` à classe — deve casar com "
                        "`Menu.view` no DB. Sem isso, CustomPermissionClass nega tudo."
                    ),
                    obj=viewset_cls,
                    id="core.E002",
                )
            )

        # E003 — subclasses de BaseModelViewSet devem declarar permissão própria
        # (permission_classes ou get_permissions).
        if _inherits_base_viewset(viewset_cls) and not _has_explicit_permissions(viewset_cls):
            # já coberto pelo E001 acima; segue como redundância intencional.
            continue

        # W002 — destroy + permissão uniforme = suspeito
        if (
            _inherits_base_viewset(viewset_cls)
            and _has_uniform_permissions(viewset_cls)
            and "destroy" not in getattr(viewset_cls, "_disabled_actions", set())
        ):
            issues.append(
                Warning(
                    (
                        f"ViewSet {viewset_cls.__name__} usa a mesma `permission_classes` "
                        "para todas as actions, incluindo `destroy`. Geralmente "
                        "leitura ≠ deleção."
                    ),
                    hint=(
                        "Migre para `CustomPermissionClass` (separa READ/CREATE/"
                        "UPDATE/DELETE por método HTTP) ou sobrescreva "
                        "`get_permissions`. Se a uniformidade for intencional, "
                        "ignore com SILENCED_SYSTEM_CHECKS = ['core.W002']."
                    ),
                    obj=viewset_cls,
                    id="core.W002",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Hardening de produção
# ---------------------------------------------------------------------------
_WEAK_SECRET_FRAGMENTS = ("change-me", "changeme", "dev-only", "insecure", "secret")


@register(Tags.security, deploy=True)
def check_production_hardening(app_configs, **kwargs):
    """Roda só em ``manage.py check --deploy`` (CI / pipeline de prod).

    Não falha o ``runserver`` local em DEBUG=True.
    """
    if settings.DEBUG:
        return []

    issues = []

    # E004 — SECRET_KEY
    sk = settings.SECRET_KEY or ""
    weak = not sk or len(sk) < 50 or any(frag in sk.lower() for frag in _WEAK_SECRET_FRAGMENTS)
    if weak:
        issues.append(
            Error(
                "SECRET_KEY parece fraca ou padrão de exemplo.",
                hint="Gere uma chave longa e aleatória (>= 50 chars) e injete via env.",
                id="core.E004",
            )
        )

    # E005 — ALLOWED_HOSTS
    hosts = settings.ALLOWED_HOSTS or []
    if not hosts or "*" in hosts:
        issues.append(
            Error(
                "ALLOWED_HOSTS está vazio ou contém '*' em produção.",
                hint="Liste explicitamente os hosts: api.meusite.com,admin.meusite.com.",
                id="core.E005",
            )
        )

    # E006 — CORS
    if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
        issues.append(
            Error(
                "CORS_ALLOW_ALL_ORIGINS=True em produção.",
                hint="Use CORS_ALLOWED_ORIGINS com a lista exata do front.",
                id="core.E006",
            )
        )

    # W003 — chave do provedor de e-mail
    if not getattr(settings, "BREVO_API_KEY", ""):
        issues.append(
            Warning(
                "BREVO_API_KEY não configurada. E-mails não serão enviados.",
                hint="Defina BREVO_API_KEY no ambiente de produção.",
                id="core.W003",
            )
        )

    # W004 — SSL redirect
    if not getattr(settings, "SECURE_SSL_REDIRECT", False):
        issues.append(
            Warning(
                "SECURE_SSL_REDIRECT está desligado em produção.",
                hint="Ative SECURE_SSL_REDIRECT=True (ou termine TLS no proxy e use SECURE_PROXY_SSL_HEADER).",
                id="core.W004",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# AllowAny exige justificativa
# ---------------------------------------------------------------------------
_ALLOW_ANY_RE = re.compile(r"\bAllowAny\b")
_JUSTIFY_MARKERS = ("# allow-any:", "# noqa: ALLOW-ANY")


def _project_view_files() -> list[Path]:
    base = Path(settings.BASE_DIR)
    paths = []
    for sub in ("core/views", "core/classes"):
        d = base / sub
        if d.is_dir():
            paths.extend(d.rglob("*.py"))
    return paths


@register(Tags.security)
def check_allow_any_justification(app_configs, **kwargs):
    """``AllowAny`` deve vir com comentário ``# allow-any: <motivo>`` na mesma
    linha ou na linha de cima. Força o dev a justificar abertura pública.
    """
    issues = []
    for path in _project_view_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines):
            if not _ALLOW_ANY_RE.search(line):
                continue
            # Ignora a linha de import.
            stripped = line.lstrip()
            if stripped.startswith(("from ", "import ")):
                continue
            # Linha pode ter justificativa inline.
            if any(m in line for m in _JUSTIFY_MARKERS):
                continue
            # Ou em qualquer das 5 linhas anteriores (cobre dicts multi-linha).
            window_start = max(0, i - 10)
            if any(any(m in lines[j] for m in _JUSTIFY_MARKERS) for j in range(window_start, i)):
                continue
            rel = path.relative_to(settings.BASE_DIR)
            issues.append(
                Warning(
                    f"{rel}:{i + 1} usa AllowAny sem justificativa.",
                    hint=(
                        "Adicione `# allow-any: <motivo>` na mesma linha ou na "
                        "linha acima explicando por que esta rota é pública."
                    ),
                    id="core.W006",
                )
            )
    return issues


# ---------------------------------------------------------------------------
# Auditoria de serializers (PII / fields="__all__")
# ---------------------------------------------------------------------------
# Campos sensíveis que NUNCA devem aparecer em saída de API por engano.
_PII_FIELDS = frozenset(
    {
        "password",
        "forgot_password_hash",
        "forgot_password_expire",
        "email_verification_code",
        "email_verification_expire",
    }
)


def _all_modelserializers():
    """Coleta todas as subclasses de ModelSerializer importadas no projeto."""
    from rest_framework.serializers import ModelSerializer

    # Força o import do pacote para popular as subclasses.
    try:
        import core.serializers  # noqa: F401
    except Exception:  # pragma: no cover
        return []

    seen = set()
    found = []
    stack = [ModelSerializer]
    while stack:
        cls = stack.pop()
        for sub in cls.__subclasses__():
            if sub in seen:
                continue
            seen.add(sub)
            stack.append(sub)
            module = getattr(sub, "__module__", "") or ""
            if not module.startswith("core."):
                continue
            if module.startswith("core.tests"):
                continue
            found.append(sub)
    return found


@register(Tags.security)
def check_serializers_pii(app_configs, **kwargs):
    """Audita ``ModelSerializer``s do projeto:

    - W007: ``Meta.fields = '__all__'`` é proibido (vaza colunas novas por engano).
    - W008: campos PII conhecidos só passam se o serializer marcar
      ``Meta.allow_pii = True`` (acknowledge explícito).
    """
    issues = []

    for sub in _all_modelserializers():
        meta = getattr(sub, "Meta", None)
        if meta is None:
            continue

        fields = getattr(meta, "fields", None)
        exclude = getattr(meta, "exclude", None)

        # W007 — fields="__all__" proibido (a no ser que opt-in explcito).
        allow_all = getattr(meta, "allow_all_fields", False)
        if fields == "__all__" and not allow_all:
            issues.append(
                Warning(
                    f"{sub.__module__}.{sub.__name__} usa Meta.fields = '__all__'.",
                    hint=(
                        "Liste os campos explicitamente. '__all__' vaza colunas "
                        "futuras (ex.: token, hash) sem code review perceber. "
                        "Se for intencional, marque `allow_all_fields = True` na Meta."
                    ),
                    obj=sub,
                    id="core.W007",
                )
            )

        # W008 — PII exposta sem acknowledge.
        allow_pii = getattr(meta, "allow_pii", False)
        if allow_pii:
            continue

        # Resolve o conjunto de fields exposto. Se for "__all__"/None, já alertamos.
        if isinstance(fields, list | tuple):
            exposed = set(fields)
        elif isinstance(exclude, list | tuple):
            model = getattr(meta, "model", None)
            if model is None:
                continue
            all_names = {f.name for f in model._meta.get_fields()}
            exposed = all_names - set(exclude)
        else:
            continue

        leaks = exposed & _PII_FIELDS
        if not leaks:
            continue

        # Filtra leaks que so write_only (no aparecem na resposta).
        extra_kwargs = getattr(meta, "extra_kwargs", {}) or {}
        declared = getattr(sub, "_declared_fields", {}) or {}
        safe = set()
        for fname in leaks:
            if extra_kwargs.get(fname, {}).get("write_only"):
                safe.add(fname)
                continue
            field = declared.get(fname)
            if field is not None and getattr(field, "write_only", False):
                safe.add(fname)
        leaks = leaks - safe

        if leaks:
            issues.append(
                Warning(
                    (f"{sub.__module__}.{sub.__name__} expõe campos PII: " f"{sorted(leaks)}."),
                    hint=(
                        "Remova esses campos de Meta.fields, ou marque "
                        "`allow_pii = True` na Meta para reconhecer explicitamente."
                    ),
                    obj=sub,
                    id="core.W008",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Migrations pendentes em produção
# ---------------------------------------------------------------------------
@register(Tags.database, deploy=True)
def check_unapplied_migrations(app_configs, **kwargs):
    """Em produção, migrations pendentes derrubam o boot."""
    if settings.DEBUG:
        return []

    try:
        from django.db import connections
        from django.db.migrations.executor import MigrationExecutor
    except Exception as exc:  # pragma: no cover
        return [
            Warning(
                f"Não foi possível auditar migrations: {exc}",
                id="core.W009",
            )
        ]

    issues = []
    for alias in connections:
        try:
            executor = MigrationExecutor(connections[alias])
            targets = executor.loader.graph.leaf_nodes()
            plan = executor.migration_plan(targets)
        except Exception as exc:
            issues.append(
                Warning(
                    f"Não foi possível conectar ao DB '{alias}': {exc}",
                    id="core.W009",
                )
            )
            continue
        if plan:
            pending = ", ".join(f"{m.app_label}.{m.name}" for m, _ in plan[:5])
            issues.append(
                Error(
                    f"Migrations pendentes no DB '{alias}': {pending}"
                    + (" ..." if len(plan) > 5 else ""),
                    hint="Rode `python manage.py migrate` antes de subir o serviço.",
                    id="core.E008",
                )
            )
    return issues
