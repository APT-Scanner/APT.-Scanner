import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.user_service import create_user, generate_unique_username, get_user_by_username
from src.models.models import User as UserModel
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_generate_unique_username():
    """Test that generate_unique_username creates unique usernames when conflicts exist."""
    # Mock database session
    db = AsyncMock(spec=AsyncSession)
    
    # Mock existing users
    existing_usernames = ["testuser", "testuser_1", "testuser_2"]
    
    async def mock_get_user_by_username(db, username):
        return UserModel(username=username) if username in existing_usernames else None
    
    # Replace the function temporarily for testing
    import src.services.user_service
    original_func = src.services.user_service.get_user_by_username
    src.services.user_service.get_user_by_username = mock_get_user_by_username
    
    try:
        # Test generating unique username
        unique_username = await generate_unique_username(db, "testuser")
        assert unique_username == "testuser_3"
        
        # Test with non-conflicting username
        unique_username = await generate_unique_username(db, "newuser")
        assert unique_username == "newuser"
        
    finally:
        # Restore original function
        src.services.user_service.get_user_by_username = original_func


@pytest.mark.asyncio
async def test_create_user_with_duplicate_email_prefix():
    """Test that creating users with duplicate email prefixes generates unique usernames."""
    db = AsyncMock(spec=AsyncSession)
    
    # Mock the database operations
    created_users = []
    
    async def mock_get_user_by_username(db, username):
        return next((user for user in created_users if user.username == username), None)
    
    async def mock_get_user_by_firebase_uid(db, firebase_uid):
        return next((user for user in created_users if user.firebase_uid == firebase_uid), None)
    
    def mock_add(user):
        created_users.append(user)
    
    async def mock_commit():
        pass
    
    async def mock_refresh(user):
        user.id = len(created_users)
    
    # Setup mocks
    db.add = mock_add
    db.commit = mock_commit
    db.refresh = mock_refresh
    
    # Replace functions temporarily
    import src.services.user_service
    original_get_by_username = src.services.user_service.get_user_by_username
    original_get_by_firebase = src.services.user_service.get_user_by_firebase_uid
    
    src.services.user_service.get_user_by_username = mock_get_user_by_username
    src.services.user_service.get_user_by_firebase_uid = mock_get_user_by_firebase_uid
    
    try:
        # Create first user with email bbbbbbbb@1.com
        user1 = await create_user(
            db=db,
            firebase_uid="uid1",
            email="bbbbbbbb@1.com"
        )
        assert user1.username == "bbbbbbbb"
        
        # Create second user with email bbbbbbbb@2.com
        user2 = await create_user(
            db=db,
            firebase_uid="uid2", 
            email="bbbbbbbb@2.com"
        )
        assert user2.username == "bbbbbbbb_1"
        
        # Verify usernames are different
        assert user1.username != user2.username
        
    finally:
        # Restore original functions
        src.services.user_service.get_user_by_username = original_get_by_username
        src.services.user_service.get_user_by_firebase_uid = original_get_by_firebase


if __name__ == "__main__":
    pytest.main([__file__]) 