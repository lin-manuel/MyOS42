from contextvars import ContextVar


current_tenant_user = ContextVar("myos_current_tenant_user", default=None)
