from app import create_app

app = create_app('development')

print("\n📋 RUTAS REGISTRADAS:")
print("=====================")
for rule in app.url_map.iter_rules():
    print(f"{rule.endpoint:30} {rule}")
print("=====================")
