"""
Unit Tests for Donation Service
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
from unittest.mock import MagicMock
from datetime import datetime

# Import models and functions to test
from app.models.donation import Donation, DonationStatus
from app.schemas.donation import (
    CreateDonationRequest,
    UpdateDonationRequest,
    DonationResponse
)
from app.services.donation import DonationService


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_donation_id():
    """Generate a sample donation ID"""
    return 1


@pytest.fixture
def sample_donation():
    """Create a sample donation object"""
    return Donation(
        id=1,
        user_id="user-123",
        campaign_id=5,
        amount=100.0,
        status=DonationStatus.INITIATED,
        payment_method="card",
        payment_id=None,
        donor_name="John Doe",
        donor_email="john@example.com",
        message="Great cause!",
        is_anonymous=False,
        created_at=datetime(2025, 11, 21, 10, 0, 0),
        updated_at=datetime(2025, 11, 21, 10, 0, 0)
    )


@pytest.fixture
def sample_create_donation_request():
    """Sample donation creation data"""
    return CreateDonationRequest(
        user_id="user-123",
        campaign_id=5,
        amount=100.0,
        payment_method="card",
        donor_name="John Doe",
        donor_email="john@example.com",
        message="Great cause!",
        is_anonymous=False
    )


@pytest.fixture
def sample_update_donation_request():
    """Sample donation update data"""
    return UpdateDonationRequest(
        status="captured",
        payment_id="pi_12345"
    )


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.rollback = MagicMock()
    session.query = MagicMock()
    return session


# ============================================================================
# SERVICE TESTS - CREATE DONATION
# ============================================================================

class TestDonationServiceCreate:
    """Test donation creation service - success and failure scenarios"""
    
    def test_create_donation_success(
        self,
        mock_db_session,
        sample_create_donation_request,
        sample_donation
    ):
        """Test successful donation creation"""
        # Mock database operations
        def mock_refresh(obj):
            obj.id = 1
            obj.created_at = datetime(2025, 11, 21, 10, 0, 0)
            obj.updated_at = datetime(2025, 11, 21, 10, 0, 0)
        mock_db_session.refresh = MagicMock(side_effect=mock_refresh)
        
        donation_response, donation_obj = DonationService.create_donation(
            db=mock_db_session,
            donation_data=sample_create_donation_request
        )
        
        # Verify database operations called
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        assert mock_db_session.refresh.called
        
        # Verify response
        assert isinstance(donation_response, DonationResponse)
        assert donation_response.user_id == sample_create_donation_request.user_id
        assert donation_response.campaign_id == sample_create_donation_request.campaign_id
        assert donation_response.amount == sample_create_donation_request.amount
    
    def test_create_donation_database_error(
        self,
        mock_db_session,
        sample_create_donation_request
    ):
        """Test donation creation handles database errors"""
        mock_db_session.commit.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception) as exc_info:
            DonationService.create_donation(
                db=mock_db_session,
                donation_data=sample_create_donation_request
            )
        
        assert "Failed to create donation" in str(exc_info.value)
        assert mock_db_session.rollback.called


# ============================================================================
# SERVICE TESTS - GET DONATION
# ============================================================================

class TestDonationServiceGet:
    """Test donation retrieval service - success and failure scenarios"""
    
    def test_get_donation_success(
        self,
        mock_db_session,
        sample_donation,
        sample_donation_id
    ):
        """Test successfully getting donation by ID"""
        # Mock query result
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = sample_donation
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        donation = DonationService.get_donation(
            db=mock_db_session,
            donation_id=sample_donation_id
        )
        
        assert donation is not None
        assert isinstance(donation, DonationResponse)
        assert donation.id == sample_donation_id
        assert donation.user_id == sample_donation.user_id
    
    def test_get_donation_not_found(
        self,
        mock_db_session,
        sample_donation_id
    ):
        """Test getting donation by ID when donation doesn't exist"""
        # Mock query result - donation not found
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        donation = DonationService.get_donation(
            db=mock_db_session,
            donation_id=sample_donation_id
        )
        
        assert donation is None


# ============================================================================
# SERVICE TESTS - GET DONATIONS BY USER
# ============================================================================

class TestDonationServiceGetByUser:
    """Test getting donations by user - success scenarios"""
    
    def test_get_donations_by_user_success(
        self,
        mock_db_session,
        sample_donation
    ):
        """Test successfully getting donations by user ID"""
        # Mock query result
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()
        mock_limit.all.return_value = [sample_donation]
        mock_offset.limit.return_value = mock_limit
        mock_filter.offset.return_value = mock_offset
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        donations = DonationService.get_donations_by_user(
            db=mock_db_session,
            user_id="user-123",
            skip=0,
            limit=100
        )
        
        assert len(donations) == 1
        assert isinstance(donations[0], DonationResponse)
        assert donations[0].user_id == "user-123"
    
    def test_get_donations_by_user_empty(
        self,
        mock_db_session
    ):
        """Test getting donations by user when no donations exist"""
        # Mock query result - empty list
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()
        mock_limit.all.return_value = []
        mock_offset.limit.return_value = mock_limit
        mock_filter.offset.return_value = mock_offset
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        donations = DonationService.get_donations_by_user(
            db=mock_db_session,
            user_id="user-999",
            skip=0,
            limit=100
        )
        
        assert len(donations) == 0


# ============================================================================
# SERVICE TESTS - UPDATE DONATION
# ============================================================================

class TestDonationServiceUpdate:
    """Test donation update service - success and failure scenarios"""
    
    def test_update_donation_status_success(
        self,
        mock_db_session,
        sample_donation,
        sample_donation_id,
        sample_update_donation_request
    ):
        """Test successfully updating donation status"""
        # Mock query result
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = sample_donation
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        donation = DonationService.update_donation_status(
            db=mock_db_session,
            donation_id=sample_donation_id,
            update_data=sample_update_donation_request
        )
        
        # Verify database operations called
        assert mock_db_session.commit.called
        assert mock_db_session.refresh.called
        
        # Verify response
        assert donation is not None
        assert isinstance(donation, DonationResponse)
    
    def test_update_donation_not_found(
        self,
        mock_db_session,
        sample_donation_id,
        sample_update_donation_request
    ):
        """Test updating donation when donation doesn't exist"""
        # Mock query result - donation not found
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        donation = DonationService.update_donation_status(
            db=mock_db_session,
            donation_id=sample_donation_id,
            update_data=sample_update_donation_request
        )
        
        assert donation is None
    
    def test_update_donation_database_error(
        self,
        mock_db_session,
        sample_donation,
        sample_donation_id,
        sample_update_donation_request
    ):
        """Test donation update handles database errors"""
        # Mock query result
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = sample_donation
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        # Simulate database error on commit
        mock_db_session.commit.side_effect = Exception("Database error")
        
        with pytest.raises(Exception) as exc_info:
            DonationService.update_donation_status(
                db=mock_db_session,
                donation_id=sample_donation_id,
                update_data=sample_update_donation_request
            )
        
        assert "Failed to update donation" in str(exc_info.value)
        assert mock_db_session.rollback.called
