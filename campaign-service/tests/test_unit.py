"""
Unit Tests for Campaign Service
Tests CRUD operations with mocking
"""
import sys
from pathlib import Path
# Add parent folder (project root) to sys.path so local modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
proj_root_str = str(PROJECT_ROOT)
if proj_root_str not in sys.path:
    sys.path.insert(0, proj_root_str)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta

# Import models and functions to test
from app.models.campaign import Campaign
from app.schemas.campaign import (
    CreateCampaignRequest,
    UpdateCampaignRequest,
    CampaignResponse
)
from app.services.campaign import CampaignService


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_campaign_id():
    """Generate a sample campaign ID"""
    return 1


@pytest.fixture
def sample_start_date():
    """Sample start date"""
    return datetime(2025, 6, 1, 0, 0, 0)


@pytest.fixture
def sample_end_date():
    """Sample end date"""
    return datetime(2025, 8, 31, 23, 59, 59)


@pytest.fixture
def sample_campaign(sample_campaign_id, sample_start_date, sample_end_date):
    """Create a sample campaign object"""
    return Campaign(
        id=sample_campaign_id,
        title="Summer Sale 2025",
        name="summer-sale-2025",
        description="Get amazing deals this summer",
        start_date=sample_start_date,
        end_date=sample_end_date,
        is_active=True,
        created_at=datetime(2025, 5, 1, 10, 0, 0),
        updated_at=datetime(2025, 5, 1, 10, 0, 0)
    )


@pytest.fixture
def sample_create_campaign_request(sample_start_date, sample_end_date):
    """Sample campaign creation data"""
    return CreateCampaignRequest(
        title="Summer Sale 2025",
        name="summer-sale-2025",
        description="Get amazing deals this summer",
        start_date=sample_start_date,
        end_date=sample_end_date,
        is_active=True
    )


@pytest.fixture
def sample_update_campaign_request():
    """Sample campaign update data"""
    return UpdateCampaignRequest(
        title="Summer Sale 2025 Extended",
        end_date=datetime(2025, 9, 15, 23, 59, 59),
        is_active=True
    )


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.delete = MagicMock()
    session.rollback = MagicMock()
    session.query = MagicMock()
    return session


@pytest.fixture
def mock_circuit_breaker():
    """Mock circuit breaker that passes through function calls"""
    async def mock_call(func):
        return func()
    
    breaker = MagicMock()
    breaker.call = mock_call
    breaker.get_state = MagicMock(return_value="closed")
    return breaker


# ============================================================================
# SERVICE TESTS - CREATE CAMPAIGN
# ============================================================================

class TestCampaignServiceCreate:
    """Test campaign creation service - success and failure scenarios"""
    
    @pytest.mark.asyncio
    async def test_create_campaign_success(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_create_campaign_request,
        sample_campaign
    ):
        """Test successful campaign creation"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock database operations
            def mock_refresh(obj):
                obj.id = 1
                obj.created_at = datetime(2025, 5, 1, 10, 0, 0)
                obj.updated_at = datetime(2025, 5, 1, 10, 0, 0)
            mock_db_session.refresh = MagicMock(side_effect=mock_refresh)
            
            campaign = await CampaignService.create_campaign(
                db=mock_db_session,
                campaign_data=sample_create_campaign_request
            )
            
            # Verify database operations called
            assert mock_db_session.add.called
            assert mock_db_session.commit.called
            assert mock_db_session.refresh.called
            
            # Verify response
            assert isinstance(campaign, CampaignResponse)
            assert campaign.title == sample_create_campaign_request.title
            assert campaign.name == sample_create_campaign_request.name
    
    @pytest.mark.asyncio
    async def test_create_campaign_database_error(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_create_campaign_request
    ):
        """Test campaign creation handles database errors"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            mock_db_session.commit.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception) as exc_info:
                await CampaignService.create_campaign(
                    db=mock_db_session,
                    campaign_data=sample_create_campaign_request
                )
            
            assert "Failed to create campaign" in str(exc_info.value)
            assert mock_db_session.rollback.called
    
    @pytest.mark.asyncio
    async def test_create_campaign_circuit_breaker_open(
        self,
        mock_db_session,
        sample_create_campaign_request
    ):
        """Test campaign creation when circuit breaker is open"""
        from app.core.circuit_breaker import CircuitBreakerError
        
        async def mock_call_open(func):
            raise CircuitBreakerError("Circuit breaker is open")
        
        breaker = MagicMock()
        breaker.call = mock_call_open
        
        with patch('app.services.campaign.db_circuit_breaker', breaker):
            with pytest.raises(Exception) as exc_info:
                await CampaignService.create_campaign(
                    db=mock_db_session,
                    campaign_data=sample_create_campaign_request
                )
            
            assert "Service temporarily unavailable" in str(exc_info.value)


# ============================================================================
# SERVICE TESTS - GET CAMPAIGN
# ============================================================================

class TestCampaignServiceGet:
    """Test campaign retrieval service - success and failure scenarios"""
    
    @pytest.mark.asyncio
    async def test_get_campaign_success(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_campaign,
        sample_campaign_id
    ):
        """Test successfully getting campaign by ID"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = sample_campaign
            mock_query.filter.return_value = mock_filter
            mock_db_session.query.return_value = mock_query
            
            campaign = await CampaignService.get_campaign(
                db=mock_db_session,
                campaign_id=sample_campaign_id
            )
            
            assert campaign is not None
            assert isinstance(campaign, CampaignResponse)
            assert campaign.id == sample_campaign_id
            assert campaign.title == sample_campaign.title
    
    @pytest.mark.asyncio
    async def test_get_campaign_not_found(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_campaign_id
    ):
        """Test getting campaign by ID when campaign doesn't exist"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result - campaign not found
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.filter.return_value = mock_filter
            mock_db_session.query.return_value = mock_query
            
            campaign = await CampaignService.get_campaign(
                db=mock_db_session,
                campaign_id=sample_campaign_id
            )
            
            assert campaign is None
    
    @pytest.mark.asyncio
    async def test_get_campaign_circuit_breaker_open(
        self,
        mock_db_session,
        sample_campaign_id
    ):
        """Test getting campaign when circuit breaker is open"""
        from app.core.circuit_breaker import CircuitBreakerError
        
        async def mock_call_open(func):
            raise CircuitBreakerError("Circuit breaker is open")
        
        breaker = MagicMock()
        breaker.call = mock_call_open
        
        with patch('app.services.campaign.db_circuit_breaker', breaker):
            with pytest.raises(Exception) as exc_info:
                await CampaignService.get_campaign(
                    db=mock_db_session,
                    campaign_id=sample_campaign_id
                )
            
            assert "Service temporarily unavailable" in str(exc_info.value)


# ============================================================================
# SERVICE TESTS - GET ALL CAMPAIGNS
# ============================================================================

class TestCampaignServiceGetAll:
    """Test getting all campaigns - success and failure scenarios"""
    
    @pytest.mark.asyncio
    async def test_get_all_campaigns_success(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_campaign
    ):
        """Test successfully getting all campaigns"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result
            mock_query = MagicMock()
            mock_offset = MagicMock()
            mock_limit = MagicMock()
            mock_limit.all.return_value = [sample_campaign]
            mock_offset.limit.return_value = mock_limit
            mock_query.offset.return_value = mock_offset
            mock_db_session.query.return_value = mock_query
            
            campaigns = await CampaignService.get_all_campaigns(
                db=mock_db_session,
                skip=0,
                limit=100
            )
            
            assert len(campaigns) == 1
            assert isinstance(campaigns[0], CampaignResponse)
            assert campaigns[0].title == sample_campaign.title
    
    @pytest.mark.asyncio
    async def test_get_all_campaigns_empty(
        self,
        mock_db_session,
        mock_circuit_breaker
    ):
        """Test getting all campaigns when no campaigns exist"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result - empty list
            mock_query = MagicMock()
            mock_offset = MagicMock()
            mock_limit = MagicMock()
            mock_limit.all.return_value = []
            mock_offset.limit.return_value = mock_limit
            mock_query.offset.return_value = mock_offset
            mock_db_session.query.return_value = mock_query
            
            campaigns = await CampaignService.get_all_campaigns(
                db=mock_db_session,
                skip=0,
                limit=100
            )
            
            assert len(campaigns) == 0
    
    @pytest.mark.asyncio
    async def test_get_all_campaigns_with_pagination(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_campaign
    ):
        """Test getting campaigns with pagination parameters"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result
            mock_query = MagicMock()
            mock_offset = MagicMock()
            mock_limit = MagicMock()
            mock_limit.all.return_value = [sample_campaign]
            mock_offset.limit.return_value = mock_limit
            mock_query.offset.return_value = mock_offset
            mock_db_session.query.return_value = mock_query
            
            campaigns = await CampaignService.get_all_campaigns(
                db=mock_db_session,
                skip=10,
                limit=50
            )
            
            # Verify offset and limit were called with correct values
            mock_query.offset.assert_called_once_with(10)
            mock_offset.limit.assert_called_once_with(50)


# ============================================================================
# SERVICE TESTS - UPDATE CAMPAIGN
# ============================================================================

class TestCampaignServiceUpdate:
    """Test campaign update service - success and failure scenarios"""
    
    @pytest.mark.asyncio
    async def test_update_campaign_success(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_campaign,
        sample_campaign_id,
        sample_update_campaign_request
    ):
        """Test successfully updating campaign"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = sample_campaign
            mock_query.filter.return_value = mock_filter
            mock_db_session.query.return_value = mock_query
            
            campaign = await CampaignService.update_campaign(
                db=mock_db_session,
                campaign_id=sample_campaign_id,
                campaign_data=sample_update_campaign_request
            )
            
            # Verify database operations called
            assert mock_db_session.commit.called
            assert mock_db_session.refresh.called
            
            # Verify response
            assert campaign is not None
            assert isinstance(campaign, CampaignResponse)
            assert campaign.title == sample_update_campaign_request.title
    
    @pytest.mark.asyncio
    async def test_update_campaign_not_found(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_campaign_id,
        sample_update_campaign_request
    ):
        """Test updating campaign when campaign doesn't exist"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result - campaign not found
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.filter.return_value = mock_filter
            mock_db_session.query.return_value = mock_query
            
            campaign = await CampaignService.update_campaign(
                db=mock_db_session,
                campaign_id=sample_campaign_id,
                campaign_data=sample_update_campaign_request
            )
            
            assert campaign is None
    
    @pytest.mark.asyncio
    async def test_update_campaign_partial_update(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_campaign,
        sample_campaign_id
    ):
        """Test updating campaign with partial data"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = sample_campaign
            mock_query.filter.return_value = mock_filter
            mock_db_session.query.return_value = mock_query
            
            # Only update is_active field
            partial_update = UpdateCampaignRequest(is_active=False)
            
            campaign = await CampaignService.update_campaign(
                db=mock_db_session,
                campaign_id=sample_campaign_id,
                campaign_data=partial_update
            )
            
            assert campaign is not None
            assert campaign.is_active == False
    
    @pytest.mark.asyncio
    async def test_update_campaign_database_error(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_campaign,
        sample_campaign_id,
        sample_update_campaign_request
    ):
        """Test campaign update handles database errors"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = sample_campaign
            mock_query.filter.return_value = mock_filter
            mock_db_session.query.return_value = mock_query
            
            # Simulate database error on commit
            mock_db_session.commit.side_effect = Exception("Database error")
            
            with pytest.raises(Exception) as exc_info:
                await CampaignService.update_campaign(
                    db=mock_db_session,
                    campaign_id=sample_campaign_id,
                    campaign_data=sample_update_campaign_request
                )
            
            assert "Failed to update campaign" in str(exc_info.value)
            assert mock_db_session.rollback.called


# ============================================================================
# SERVICE TESTS - DELETE CAMPAIGN
# ============================================================================

class TestCampaignServiceDelete:
    """Test campaign deletion service - success and failure scenarios"""
    
    @pytest.mark.asyncio
    async def test_delete_campaign_success(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_campaign,
        sample_campaign_id
    ):
        """Test successfully deleting campaign"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = sample_campaign
            mock_query.filter.return_value = mock_filter
            mock_db_session.query.return_value = mock_query
            
            result = await CampaignService.delete_campaign(
                db=mock_db_session,
                campaign_id=sample_campaign_id
            )
            
            assert result is True
            assert mock_db_session.delete.called
            assert mock_db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_delete_campaign_not_found(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_campaign_id
    ):
        """Test deleting campaign when campaign doesn't exist"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result - campaign not found
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.filter.return_value = mock_filter
            mock_db_session.query.return_value = mock_query
            
            result = await CampaignService.delete_campaign(
                db=mock_db_session,
                campaign_id=sample_campaign_id
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_campaign_database_error(
        self,
        mock_db_session,
        mock_circuit_breaker,
        sample_campaign,
        sample_campaign_id
    ):
        """Test campaign deletion handles database errors"""
        with patch('app.services.campaign.db_circuit_breaker', mock_circuit_breaker):
            # Mock query result
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = sample_campaign
            mock_query.filter.return_value = mock_filter
            mock_db_session.query.return_value = mock_query
            
            # Simulate database error on commit
            mock_db_session.commit.side_effect = Exception("Database error")
            
            with pytest.raises(Exception) as exc_info:
                await CampaignService.delete_campaign(
                    db=mock_db_session,
                    campaign_id=sample_campaign_id
                )
            
            assert "Failed to delete campaign" in str(exc_info.value)
            assert mock_db_session.rollback.called
