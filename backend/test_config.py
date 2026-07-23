from app.core.config import settings

print(settings)

print("-" * 50)

print(settings.model_dump())

print("-" * 50)

print(settings.supabase_url)
print(settings.supabase_service_role_key[:20])
print(settings.environment)
print(settings.llm_provider)