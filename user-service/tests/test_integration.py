"""
Integration Tests for User Service
Tests with real PostgreSQL database (CI-compatible)
"""

import sys
from pathlib import Path
# Add parent folder (project root) to sys.path so local modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
proj_root_str = str(PROJECT_ROOT)
if proj_root_str not in sys.path:
    sys.path.insert(0, proj_root_str)

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
import uuid
import os
from datetime import datetime

from main import app
from database import Base, get_db
from models import User, UserCreate, UserUpdate
from crud import create_user, get_user_by_email

# Test database URL - Use env var for CI, fallback for local
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://testuser:testpass@localhost:15433/testdb"
)

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create test database and tables"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Teardown - drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(test_db):
    """Get database session for tests"""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Create test client with database override"""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user in database"""
    user_data = UserCreate(
        email="testuser@example.com",
        password="testpassword123",
        full_name="Test User",
        role="user"
    )
    user = await create_user(db_session, user_data)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session):
    """Create a test admin user in database"""
    admin_data = UserCreate(
        email="admin@example.com",
        password="adminpassword123",
        full_name="Admin User",
        role="admin"
    )
    admin = await create_user(db_session, admin_data)
    return admin


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

class TestHealthCheck:
    """Test health check endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check returns healthy status"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "user-service"


# ============================================================================
# AUTHENTICATION ENDPOINTS TESTS
# ============================================================================

class TestAuthentication:
    """Test authentication endpoints"""
    
    @pytest.mark.asyncio
    async def test_register_new_user(self, client):
        """Test registering a new user"""
        user_data = {
            "email": "newuser@example.com",
            "password": "securepass123",
            "full_name": "New User",
            "role": "user"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "user"
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, test_user):
        """Test registering with existing email fails"""
        user_data = {
            "email": "testuser@example.com",  # Same as test_user
            "password": "anotherpass123",
            "full_name": "Another User"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        """Test registering with invalid email format"""
        user_data = {
            "email": "not-an-email",
            "password": "password123",
            "full_name": "Test User"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_validate_credentials_success(self, client, test_user):
        """Test credential validation with correct credentials"""
        credentials = {
            "email": "testuser@example.com",
            "password": "testpassword123"
        }
        
        response = await client.post("/api/v1/auth/validate-credentials", json=credentials)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["full_name"] == "Test User"
        assert data["role"] == "user"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_validate_credentials_wrong_password(self, client, test_user):
        """Test credential validation with wrong password"""
        credentials = {
            "email": "testuser@example.com",
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/v1/auth/validate-credentials", json=credentials)
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_validate_credentials_nonexistent_user(self, client):
        """Test credential validation with non-existent user"""
        credentials = {
            "email": "nonexistent@example.com",
            "password": "anypassword"
        }
        
        response = await client.post("/api/v1/auth/validate-credentials", json=credentials)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_validate_credentials_missing_fields(self, client):
        """Test credential validation with missing fields"""
        credentials = {"email": "test@example.com"}  # Missing password
        
        response = await client.post("/api/v1/auth/validate-credentials", json=credentials)
        
        assert response.status_code == 400
        assert "Email and password required" in response.json()["detail"]


# ============================================================================
# USER PROFILE TESTS
# ============================================================================

class TestUserProfile:
    """Test user profile endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_my_profile(self, client, test_user):
        """Test getting current user profile"""
        response = await client.get(
            "/users/me",
            headers={"x-user-id": str(test_user.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["full_name"] == "Test User"
        assert data["role"] == "user"
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_get_my_profile_unauthorized(self, client):
        """Test getting profile without authentication"""
        response = await client.get("/users/me")
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_my_profile_invalid_user_id(self, client):
        """Test getting profile with non-existent user ID"""
        fake_id = str(uuid.uuid4())
        
        response = await client.get(
            "/users/me",
            headers={"x-user-id": fake_id}
        )
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_my_profile(self, client, test_user):
        """Test updating current user profile"""
        update_data = {
            "full_name": "Updated Name"
        }
        
        response = await client.put(
            "/users/me",
            json=update_data,
            headers={"x-user-id": str(test_user.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["email"] == "testuser@example.com"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_my_profile_with_password(self, client, test_user, db_session):
        """Test updating profile with password change"""
        update_data = {
            "password": "newpassword123"
        }
        
        response = await client.put(
            "/users/me",
            json=update_data,
            headers={"x-user-id": str(test_user.id)}
        )
        
        assert response.status_code == 200
        
        # Verify new password works
        credentials = {
            "email": "testuser@example.com",
            "password": "newpassword123"
        }
        
        auth_response = await client.post("/api/v1/auth/validate-credentials", json=credentials)
        assert auth_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_update_my_profile_unauthorized(self, client):
        """Test updating profile without authentication"""
        update_data = {"full_name": "New Name"}
        
        response = await client.put("/users/me", json=update_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_delete_my_account(self, client, test_user):
        """Test deleting current user account"""
        response = await client.delete(
            "/users/me",
            headers={"x-user-id": str(test_user.id)}
        )
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify user is deleted
        get_response = await client.get(
            "/users/me",
            headers={"x-user-id": str(test_user.id)}
        )
        assert get_response.status_code == 404


# ============================================================================
# ADMIN ENDPOINTS TESTS
# ============================================================================

class TestAdminEndpoints:
    """Test admin-only endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_users_as_admin(self, client, test_user, test_admin):
        """Test listing all users as admin"""
        response = await client.get(
            "/users",
            headers={"x-user-role": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # At least test_user and test_admin
    
    @pytest.mark.asyncio
    async def test_list_users_as_non_admin(self, client, test_user):
        """Test listing users without admin role fails"""
        response = await client.get(
            "/users",
            headers={"x-user-role": "user"}
        )
        
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_list_users_with_pagination(self, client, test_admin):
        """Test user listing with pagination"""
        response = await client.get(
            "/users?skip=0&limit=1",
            headers={"x-user-role": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_as_admin(self, client, test_user, test_admin):
        """Test getting specific user by ID as admin"""
        response = await client.get(
            f"/users/{test_user.id}",
            headers={"x-user-role": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_as_non_admin(self, client, test_user):
        """Test getting user by ID without admin role fails"""
        response = await client.get(
            f"/users/{test_user.id}",
            headers={"x-user-role": "user"}
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_admin_create_user(self, client, test_admin):
        """Test admin creating a user"""
        user_data = {
            "email": "admin-created@example.com",
            "password": "password123",
            "full_name": "Admin Created User",
            "role": "user"
        }
        
        response = await client.post(
            "/users",
            json=user_data,
            headers={"x-user-role": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin-created@example.com"
    
    @pytest.mark.asyncio
    async def test_admin_update_user(self, client, test_user, test_admin):
        """Test admin updating another user"""
        update_data = {
            "full_name": "Admin Updated Name",
            "role": "moderator"
        }
        
        response = await client.put(
            f"/users/{test_user.id}",
            json=update_data,
            headers={"x-user-role": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Admin Updated Name"
        assert data["role"] == "moderator"
    
    @pytest.mark.asyncio
    async def test_admin_delete_user(self, client, test_user, test_admin):
        """Test admin deleting a user"""
        response = await client.delete(
            f"/users/{test_user.id}",
            headers={"x-user-role": "admin"}
        )
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify user is deleted
        get_response = await client.get(
            f"/users/{test_user.id}",
            headers={"x-user-role": "admin"}
        )
        assert get_response.status_code == 404


# ============================================================================
# DATABASE INTEGRATION TESTS
# ============================================================================

class TestDatabaseIntegration:
    """Test database operations directly"""
    
    @pytest.mark.asyncio
    async def test_user_persistence(self, db_session):
        """Test that user data persists correctly"""
        from crud import create_user, get_user_by_email
        
        # Create user
        user_data = UserCreate(
            email="persist@example.com",
            password="password123",
            full_name="Persist Test"
        )
        created_user = await create_user(db_session, user_data)
        
        # Retrieve user
        retrieved_user = await get_user_by_email(db_session, "persist@example.com")
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email
        assert retrieved_user.full_name == created_user.full_name
    
    @pytest.mark.asyncio
    async def test_password_hashing(self, db_session):
        """Test that passwords are properly hashed"""
        from crud import create_user
        
        user_data = UserCreate(
            email="hash@example.com",
            password="plaintext123",
            full_name="Hash Test"
        )
        user = await create_user(db_session, user_data)
        
        # Password should be hashed, not stored in plain text
        assert user.hashed_password != "plaintext123"
        assert len(user.hashed_password) > len("plaintext123")
    
    @pytest.mark.asyncio
    async def test_unique_email_constraint(self, db_session):
        """Test that duplicate emails are prevented"""
        from crud import create_user
        from sqlalchemy.exc import IntegrityError
        
        user_data_1 = UserCreate(
            email="unique@example.com",
            password="password123",
            full_name="First User"
        )
        await create_user(db_session, user_data_1)
        
        # Try to create another user with same email
        user_data_2 = UserCreate(
            email="unique@example.com",
            password="password456",
            full_name="Second User"
        )
        
        with pytest.raises(IntegrityError):
            await create_user(db_session, user_data_2)
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_timestamp_fields(self, db_session):
        """Test that timestamp fields are set correctly"""
        from crud import create_user
        
        user_data = UserCreate(
            email="timestamp@example.com",
            password="password123",
            full_name="Timestamp Test"
        )
        user = await create_user(db_session, user_data)
        
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)
        assert user.last_login is None  # Should be None initially


# ============================================================================
# END-TO-END FLOW TESTS
# ============================================================================

class TestEndToEndFlows:
    """Test complete user journeys"""
    
    @pytest.mark.asyncio
    async def test_complete_user_lifecycle(self, client):
        """Test: register -> login -> update -> delete"""
        # 1. Register
        register_data = {
            "email": "lifecycle@example.com",
            "password": "password123",
            "full_name": "Lifecycle Test"
        }
        register_response = await client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 201
        user_id = register_response.json()["id"]
        
        # 2. Login (validate credentials)
        login_data = {
            "email": "lifecycle@example.com",
            "password": "password123"
        }
        login_response = await client.post("/api/v1/auth/validate-credentials", json=login_data)
        assert login_response.status_code == 200
        
        # 3. Get profile
        profile_response = await client.get(
            "/users/me",
            headers={"x-user-id": user_id}
        )
        assert profile_response.status_code == 200
        
        # 4. Update profile
        update_data = {"full_name": "Updated Lifecycle"}
        update_response = await client.put(
            "/users/me",
            json=update_data,
            headers={"x-user-id": user_id}
        )
        assert update_response.status_code == 200
        assert update_response.json()["full_name"] == "Updated Lifecycle"
        
        # 5. Delete account
        delete_response = await client.delete(
            "/users/me",
            headers={"x-user-id": user_id}
        )
        assert delete_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_admin_user_management_flow(self, client, test_admin):
        """Test: admin creates user -> views users -> updates user -> deletes user"""
        # 1. Admin creates user
        create_data = {
            "email": "managed@example.com",
            "password": "password123",
            "full_name": "Managed User"
        }
        create_response = await client.post(
            "/users",
            json=create_data,
            headers={"x-user-role": "admin"}
        )
        assert create_response.status_code == 200
        user_id = create_response.json()["id"]
        
        # 2. Admin views all users
        list_response = await client.get(
            "/users",
            headers={"x-user-role": "admin"}
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) >= 2
        
        # 3. Admin updates user
        update_data = {"role": "moderator"}
        update_response = await client.put(
            f"/users/{user_id}",
            json=update_data,
            headers={"x-user-role": "admin"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["role"] == "moderator"
        
        # 4. Admin deletes user
        delete_response = await client.delete(
            f"/users/{user_id}",
            headers={"x-user-role": "admin"}
        )
        assert delete_response.status_code == 200
