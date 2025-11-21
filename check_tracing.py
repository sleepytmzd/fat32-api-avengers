"""
Quick diagnostic script to check Jaeger tracing configuration
Run this to verify your services are properly configured for tracing
"""
import os
import sys

def check_service_config(service_name, service_path):
    """Check if a service has tracing properly configured"""
    print(f"\n{'='*60}")
    print(f"Checking {service_name}")
    print(f"{'='*60}")
    
    issues = []
    
    # Check if middleware/tracing.py exists
    tracing_file = os.path.join(service_path, "middleware", "tracing.py")
    if not os.path.exists(tracing_file):
        issues.append(f"❌ Missing: middleware/tracing.py")
    else:
        print(f"✅ Found: middleware/tracing.py")
    
    # Check if main.py initializes tracing
    main_file = os.path.join(service_path, "main.py")
    if os.path.exists(main_file):
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "init_tracing" in content:
                print(f"✅ main.py calls init_tracing()")
            else:
                issues.append(f"❌ main.py doesn't call init_tracing()")
    
    # Check requirements.txt
    req_file = os.path.join(service_path, "requirements.txt")
    if os.path.exists(req_file):
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
            has_otel = "opentelemetry" in content
            has_jaeger = "jaeger" in content
            if has_otel and has_jaeger:
                print(f"✅ requirements.txt has OpenTelemetry dependencies")
            else:
                issues.append(f"❌ requirements.txt missing OpenTelemetry or Jaeger")
    
    if issues:
        print(f"\n⚠️  Issues found:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print(f"\n✅ {service_name} is properly configured!")
    
    return len(issues) == 0

def check_docker_compose():
    """Check docker-compose.yml configuration"""
    print(f"\n{'='*60}")
    print(f"Checking docker-compose.yml")
    print(f"{'='*60}")
    
    compose_file = "docker-compose.yml"
    if not os.path.exists(compose_file):
        print("❌ docker-compose.yml not found")
        return False
    
    with open(compose_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    services = ['user-service', 'api-gateway', 'payment-service', 'notification-service']
    
    for service in services:
        if service in content:
            # Check for Jaeger env vars
            service_section = content[content.find(service):content.find(service) + 1000]
            has_jaeger_endpoint = "JAEGER_ENDPOINT" in service_section
            has_tracing_enabled = "TRACING_ENABLED" in service_section
            has_jaeger_depends = "jaeger:" in service_section or "jaeger-demo:" in service_section
            
            print(f"\n{service}:")
            print(f"  {'✅' if has_jaeger_endpoint else '❌'} JAEGER_ENDPOINT env var")
            print(f"  {'✅' if has_tracing_enabled else '❌'} TRACING_ENABLED env var")
            print(f"  {'✅' if has_jaeger_depends else '❌'} depends_on jaeger")
            
            if not (has_jaeger_endpoint and has_tracing_enabled):
                print(f"  ⚠️  Add these env vars to {service}:")
                print(f"      JAEGER_ENDPOINT: http://jaeger-demo:14268/api/traces")
                print(f"      TRACING_ENABLED: \"true\"")
                print(f"      SERVICE_NAME: \"{service}\"")

def main():
    print("\n" + "="*60)
    print("JAEGER TRACING DIAGNOSTIC TOOL")
    print("="*60)
    
    # Check services
    services = {
        "User Service": "user-service",
        "API Gateway": "api-gateway",
        "Payment Service": "payment-service",
        "Notification Service": "notification-service",
    }
    
    all_good = True
    for name, path in services.items():
        if os.path.exists(path):
            result = check_service_config(name, path)
            all_good = all_good and result
        else:
            print(f"\n⚠️  {name} directory not found at {path}")
            all_good = False
    
    # Check docker-compose
    check_docker_compose()
    
    print(f"\n{'='*60}")
    print("COMMON ISSUES & SOLUTIONS")
    print(f"{'='*60}")
    print("""
1. Services not showing in Jaeger UI:
   - Rebuild containers: docker-compose up --build
   - Check logs: docker-compose logs user-service | grep -i trac
   - Verify Jaeger is running: docker ps | grep jaeger

2. Make requests to generate traces:
   - curl http://localhost:8000/api/v1/user/users/me
   - Then check Jaeger UI at http://localhost:16686

3. Ensure environment variables are set:
   - TRACING_ENABLED=true
   - JAEGER_ENDPOINT=http://jaeger-demo:14268/api/traces

4. Check container logs for errors:
   docker-compose logs user-service
   docker-compose logs api-gateway

5. Restart services after changes:
   docker-compose restart user-service api-gateway
    """)

if __name__ == "__main__":
    main()
