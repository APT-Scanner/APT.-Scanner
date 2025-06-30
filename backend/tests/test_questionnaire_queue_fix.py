"""Test questionnaire queue management fix."""
import pytest
from collections import deque
from unittest.mock import AsyncMock, MagicMock
from backend.src.services.questionnaire_service import QuestionnaireService


@pytest.fixture
def mock_questionnaire_service():
    """Create a mock questionnaire service for testing."""
    service = QuestionnaireService()
    
    # Mock the database connections
    service.mongo_db = AsyncMock()
    
    # Set up basic test questions
    service.basic_information_questions = {
        "q1": {"id": "q1", "text": "Question 1", "type": "text"},
        "q2": {"id": "q2", "text": "Question 2", "type": "text"},
        "q3": {"id": "q3", "text": "Question 3", "type": "text"}
    }
    service.dynamic_questionnaire = {}
    service.question_graph = {}
    service.total_questions = 3
    
    # Mock the database operations
    service._get_user_state_from_db = AsyncMock(return_value=None)
    service._update_user_state_in_db = AsyncMock(return_value=True)
    service._delete_user_state_from_db = AsyncMock(return_value=True)
    
    return service


@pytest.mark.asyncio
async def test_question_not_removed_from_queue_until_answered():
    """Test that questions are not removed from queue when fetched, only when answered."""
    service = QuestionnaireService()
    service.mongo_db = AsyncMock()
    service.basic_information_questions = {
        "q1": {"id": "q1", "text": "Question 1", "type": "text"},
        "q2": {"id": "q2", "text": "Question 2", "type": "text"}
    }
    service.dynamic_questionnaire = {}
    service.question_graph = {}
    service.total_questions = 2
    
    # Mock database operations
    service._get_user_state_from_db = AsyncMock(return_value=None)
    service._update_user_state_in_db = AsyncMock(return_value=True)
    
    user_id = "test_user"
    
    # Step 1: Get initial state
    state = await service.get_user_state(user_id)
    assert len(state['queue']) == 2
    assert list(state['queue']) == ["q1", "q2"]
    assert state['current_question_id'] is None
    
    # Step 2: Get next question (should not remove from queue)
    next_question, is_complete, _ = await service.get_next_question(user_id)
    assert next_question['id'] == "q1"
    assert not is_complete
    
    # Verify queue still contains both questions
    updated_state = await service.get_user_state(user_id)
    assert len(updated_state['queue']) == 2
    assert list(updated_state['queue']) == ["q1", "q2"]
    assert updated_state['current_question_id'] == "q1"
    
    # Step 3: Get next question again (should return same question)
    next_question_again, is_complete, _ = await service.get_next_question(user_id)
    assert next_question_again['id'] == "q1"  # Same question
    assert not is_complete
    
    # Verify queue still unchanged
    state_after_second_fetch = await service.get_user_state(user_id)
    assert len(state_after_second_fetch['queue']) == 2
    assert list(state_after_second_fetch['queue']) == ["q1", "q2"]
    assert state_after_second_fetch['current_question_id'] == "q1"
    
    # Step 4: Submit answer for q1
    next_question_after_answer, is_complete, _ = await service.get_next_question(
        user_id, {"q1": "answer1"}
    )
    assert next_question_after_answer['id'] == "q2"
    assert not is_complete
    
    # Verify q1 was removed from queue and q2 is now current
    final_state = await service.get_user_state(user_id)
    assert len(final_state['queue']) == 1
    assert list(final_state['queue']) == ["q2"]
    assert final_state['current_question_id'] == "q2"
    assert "q1" in final_state['answered_questions']
    assert final_state['answers']['q1'] == "answer1"


@pytest.mark.asyncio
async def test_skip_question_removes_from_queue():
    """Test that skipping a question removes it from the queue."""
    service = QuestionnaireService()
    service.mongo_db = AsyncMock()
    service.basic_information_questions = {
        "q1": {"id": "q1", "text": "Question 1", "type": "text"},
        "q2": {"id": "q2", "text": "Question 2", "type": "text"}
    }
    service.dynamic_questionnaire = {}
    service.question_graph = {}
    service.total_questions = 2
    
    # Mock database operations
    service._get_user_state_from_db = AsyncMock(return_value=None)
    service._update_user_state_in_db = AsyncMock(return_value=True)
    
    user_id = "test_user"
    
    # Get first question
    next_question, _, _ = await service.get_next_question(user_id)
    assert next_question['id'] == "q1"
    
    # Skip the current question
    skipped = await service.skip_current_question(user_id)
    assert skipped is True
    
    # Verify q1 was removed from queue
    state_after_skip = await service.get_user_state(user_id)
    assert len(state_after_skip['queue']) == 1
    assert list(state_after_skip['queue']) == ["q2"]
    assert state_after_skip['current_question_id'] is None
    assert "q1" not in state_after_skip['answered_questions']  # Not answered, just skipped
    
    # Get next question should return q2
    next_question_after_skip, _, _ = await service.get_next_question(user_id)
    assert next_question_after_skip['id'] == "q2"


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        # Simple test runner
        print("Running questionnaire queue fix tests...")
        
        try:
            await test_question_not_removed_from_queue_until_answered()
            print("✓ test_question_not_removed_from_queue_until_answered passed")
        except Exception as e:
            print(f"✗ test_question_not_removed_from_queue_until_answered failed: {e}")
        
        try:
            await test_skip_question_removes_from_queue()
            print("✓ test_skip_question_removes_from_queue passed")
        except Exception as e:
            print(f"✗ test_skip_question_removes_from_queue failed: {e}")
    
    asyncio.run(run_tests()) 