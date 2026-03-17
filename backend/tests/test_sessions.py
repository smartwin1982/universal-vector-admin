"""
Session service tests
"""
import pytest
from app.services.session_service import SessionService


def test_create_session():
    service = SessionService()
    session = service.create_session()
    assert session.session_id
    assert session.messages == []


def test_add_message():
    service = SessionService()
    session = service.create_session()
    service.add_message(session.session_id, "user", "Hello")
    service.add_message(session.session_id, "assistant", "Hi there")

    retrieved = service.get_session(session.session_id)
    assert retrieved is not None
    assert len(retrieved.messages) == 2
    assert retrieved.messages[0].role == "user"
    assert retrieved.messages[1].role == "assistant"


def test_delete_session():
    service = SessionService()
    session = service.create_session()
    assert service.delete_session(session.session_id) is True
    assert service.get_session(session.session_id) is None
    assert service.delete_session(session.session_id) is False
